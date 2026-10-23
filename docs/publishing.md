# Publishing to HACS

This repository is packaged as a **HACS Integration**. Its runtime files live in
`custom_components/bedtime_sticker_club/`. HACS downloads that entire directory,
including the dashboard, config flow, translations, and local brand icons. No frontend build or
ZIP download is required for HACS installation.

## First publication

1. Create a **public** GitHub repository. The current manifest assumes
   `nbonfire/bedtimestickerclub`; update `documentation`, `issue_tracker`, and
   `codeowners` in `custom_components/bedtime_sticker_club/manifest.json` if the
   actual owner or repository differs.
2. Set a description, enable Issues, and add topics such as `home-assistant`,
   `hacs`, `integration`, and `dashboard`.
3. Push the complete repository, including `.github/workflows/`, `docker/`, and
   the integration's YAML and PNG files.
4. Run the **Validate** workflow. The HACS action checks GitHub metadata as well
   as the repository layout; those remote checks require a published repository.
5. Add the repository URL through **HACS → Custom repositories → Integration**
   and complete Add integration on a test Home Assistant instance.

HACS can install the default branch before a release exists. A custom repository
does not require inclusion in the default HACS catalog. To request catalog
inclusion later, follow [HACS's submission process](https://www.hacs.xyz/docs/publish/include/).

## Releases

1. Update the integration manifest's `version` (starting with `1.0.0`).
2. Commit the changes and push a matching tag, for example `v1.0.0`.
3. The **Release** workflow validates that the tag matches the manifest, runs
   the tests, and creates a **draft** release with `bedtime_sticker_club.zip`.
4. Review the release notes and publish the draft. HACS only offers published
   releases; a Git tag or draft alone does not create a HACS release version.

The ZIP is for manual installation: extract it into the Home Assistant config
directory. It contains `custom_components/bedtime_sticker_club/` and never
includes account data, preview storage, caches, or test fixtures. HACS uses the
integration files from the release tag, rather than this optional archive.

Local validation and archive creation (run with the dependencies in the pinned
Home Assistant image):

```sh
python scripts/validate_repository.py --tag v1.0.0
python -m unittest discover -s tests -v
python scripts/build_release.py
```
