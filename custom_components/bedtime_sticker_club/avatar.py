"""Authenticated upload and local storage for child avatars."""

from io import BytesIO
import os
from pathlib import Path
import re
import tempfile
from uuid import uuid4

from aiohttp import web
from PIL import Image, ImageOps, UnidentifiedImageError

from homeassistant.components.http import HomeAssistantView
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP"}


def remove_avatar_file(path: str | Path) -> None:
    """Remove an obsolete avatar file when it exists."""
    try:
        Path(path).unlink()
    except FileNotFoundError:
        pass


def normalize_avatar(upload: bytes, destination: str | Path) -> None:
    """Decode a supported image, strip metadata, center-crop, and save a WebP."""
    if not upload or len(upload) > MAX_UPLOAD_BYTES:
        raise ValueError("Avatar files must be between 1 byte and 5 MiB.")
    try:
        source = Image.open(BytesIO(upload))
        if source.format not in SUPPORTED_FORMATS:
            raise ValueError("Choose a JPEG, PNG, or WebP image.")
        if source.width * source.height > MAX_IMAGE_PIXELS:
            raise ValueError("Avatar images must be smaller than 16 megapixels.")
        source.load()
        oriented = ImageOps.exif_transpose(source)
        mode = "RGBA" if "A" in oriented.getbands() else "RGB"
        normalized = ImageOps.fit(
            oriented.convert(mode),
            (512, 512),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
    except ValueError:
        raise
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as err:
        raise ValueError("The uploaded file is not a supported image.") from err

    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".webp", delete=False) as temp:
            temp_path = Path(temp.name)
            normalized.save(temp, format="WEBP", quality=86, method=5)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


class ChildAvatarView(HomeAssistantView):
    """Serve and replace a child's local avatar for authenticated users."""

    url = f"/api/{DOMAIN}/avatars/{{child_id}}"
    name = f"api:{DOMAIN}:child_avatar"
    requires_auth = True

    @staticmethod
    def _path(hass, child_id):
        return Path(hass.config.path(DOMAIN, "avatars", child_id))

    async def get(self, request, child_id):
        hass = request.app["hass"]
        coordinator = next(iter(hass.data[DOMAIN].values()), None)
        if coordinator is None or child_id not in coordinator.data["profiles"]:
            raise web.HTTPNotFound()
        filename = coordinator.data["profiles"][child_id].get("avatar_image")
        if not isinstance(filename, str) or not re.fullmatch(rf"{re.escape(child_id)}-[0-9a-f]{{32}}\.webp", filename):
            raise web.HTTPNotFound()
        image_path = self._path(hass, filename)
        if not image_path.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(
            image_path,
            headers={"Cache-Control": "private, max-age=300"},
        )

    async def post(self, request, child_id):
        hass = request.app["hass"]
        coordinator = next(iter(hass.data[DOMAIN].values()), None)
        if coordinator is None or child_id not in coordinator.data["profiles"]:
            raise web.HTTPNotFound()
        if not coordinator.data["profiles"][child_id]["active"]:
            raise web.HTTPBadRequest(text="Restore this child profile before changing its avatar.")
        if request.content_type not in ("image/jpeg", "image/png", "image/webp"):
            raise web.HTTPUnsupportedMediaType(text="Choose a JPEG, PNG, or WebP image.")
        if request.content_length and request.content_length > MAX_UPLOAD_BYTES:
            raise web.HTTPRequestEntityTooLarge(
                max_size=MAX_UPLOAD_BYTES,
                actual_size=request.content_length,
            )
        upload = await request.content.read(MAX_UPLOAD_BYTES + 1)
        if len(upload) > MAX_UPLOAD_BYTES:
            raise web.HTTPRequestEntityTooLarge(max_size=MAX_UPLOAD_BYTES, actual_size=len(upload))
        filename = f"{child_id}-{uuid4().hex}.webp"
        image_path = self._path(hass, filename)
        previous = coordinator.data["profiles"][child_id].get("avatar_image")
        try:
            await hass.async_add_executor_job(normalize_avatar, upload, image_path)
            await coordinator.async_set_avatar_image(child_id, filename)
        except ValueError as err:
            await hass.async_add_executor_job(remove_avatar_file, image_path)
            raise web.HTTPBadRequest(text=str(err)) from err
        except Exception:
            await hass.async_add_executor_job(remove_avatar_file, image_path)
            raise
        if isinstance(previous, str) and re.fullmatch(rf"{re.escape(child_id)}-[0-9a-f]{{32}}\.webp", previous):
            await hass.async_add_executor_job(remove_avatar_file, self._path(hass, previous))
        return self.json({"avatar_image": filename})
