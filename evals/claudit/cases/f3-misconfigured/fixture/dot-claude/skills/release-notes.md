---
name: release-notes
description: Draft release notes for invoicer from the commits since the last tag. Use when asked for release notes or a changelog entry.
---

1. Run `git describe --tags --abbrev=0` to find the last tag.
2. Run `git log --oneline <tag>..HEAD`.
3. Group the changes under Added, Fixed and Changed.
4. Bump `version` in `package.json` to match and show the user the draft.
