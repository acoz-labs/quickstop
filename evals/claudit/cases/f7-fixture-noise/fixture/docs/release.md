# Release

1. Update `CHANGELOG.md` with the changes since the last tag.
2. Bump `version` in `pyproject.toml`.
3. Run `bin/ci` and make sure it passes.
4. Commit, then tag the commit `vX.Y.Z`.
5. Push the tag; the package is built from it.
