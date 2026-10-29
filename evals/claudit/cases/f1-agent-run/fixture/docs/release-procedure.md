# Release procedure

Agents cut every tallyho release. Follow these steps in order and stop at the
first failure; report the failing step instead of working around it.

1. Confirm the working tree is clean: `git status --porcelain` prints nothing.
2. Run `bin/ci`. It must exit 0.
3. Choose the next version. Bug fixes bump the patch number; new public
   functions bump the minor number. Never bump the major number without an
   issue that says so.
4. Update the version in both `pyproject.toml` and `src/tallyho/__init__.py`.
   They must match.
5. Add a section to the top of `CHANGELOG.md` headed `## <version>` listing
   each user-visible change in one line.
6. Run `bin/ci` again.
7. Commit with the message `release: <version>`.
8. Tag the commit `v<version>` (annotated tag, message `tallyho <version>`).
9. Push the commit and the tag: `git push && git push --tags`.
10. Post the changelog section as the release note in the tracking issue.
