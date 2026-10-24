"""Verify custom child avatars are decoded and normalized before storage."""

from io import BytesIO
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.bedtime_sticker_club.avatar import MAX_UPLOAD_BYTES, normalize_avatar


class AvatarTests(unittest.TestCase):
    def test_normalizes_image_to_square_webp(self):
        source = Image.new("RGB", (1024, 512), "purple")
        payload = BytesIO()
        source.save(payload, format="PNG")
        with TemporaryDirectory() as folder:
            destination = Path(folder) / "child.webp"
            normalize_avatar(payload.getvalue(), destination)
            with Image.open(destination) as saved:
                self.assertEqual(saved.format, "WEBP")
                self.assertEqual(saved.size, (512, 512))
                self.assertFalse(saved.getexif())

    def test_rejects_oversized_unrecognized_and_vector_files(self):
        inputs = (
            b"x" * (MAX_UPLOAD_BYTES + 1),
            b"not an image",
            b"<svg xmlns='http://www.w3.org/2000/svg'></svg>",
        )
        with TemporaryDirectory() as folder:
            destination = Path(folder) / "child.webp"
            for payload in inputs:
                with self.subTest(size=len(payload)):
                    with self.assertRaises(ValueError):
                        normalize_avatar(payload, destination)
                    self.assertFalse(destination.exists())

    def test_rejects_images_over_pixel_limit(self):
        payload = BytesIO()
        Image.new("RGB", (5000, 4000), "blue").save(payload, format="PNG")
        with TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                normalize_avatar(payload.getvalue(), Path(folder) / "child.webp")


if __name__ == "__main__":
    unittest.main()
