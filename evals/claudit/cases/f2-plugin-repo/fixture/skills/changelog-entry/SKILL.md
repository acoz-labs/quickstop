---
name: changelog-entry
description: Draft a Keep a Changelog entry from the commits since the last tag. Use when the user asks for release notes, a changelog entry, or "what changed since the last release".
---

# Draft a changelog entry

1. Find the last tag with `git describe --tags --abbrev=0`. If there is none,
   use the first commit.
2. List the commits since then with `git log --format='%s' <tag>..HEAD`.
3. Pipe that list into `python3 "${CLAUDE_SKILL_DIR}/scripts/format_entry.py"`,
   which groups conventional-commit subjects under Added, Fixed and Changed.
4. Show the user the entry and ask before writing it to `CHANGELOG.md`.
