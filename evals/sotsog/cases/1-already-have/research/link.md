# Stop writing changelogs at release time: how Pikeworth moved release notes into every pull request

Source: https://engineering.pikeworth.example.com/blog/release-notes-in-every-pr
Author: Dana Okafor, staff engineer, Pikeworth (a bookkeeping app for small shops)
Published: 2026-08-19

For years our release notes were written the night before a release by
whoever drew the short straw, reading through two weeks of merged pull
requests. They were late, they missed things, and they were written for
developers ("refactor ledger sync") instead of for the shop owners who read
them.

So we moved the note into the pull request itself. Four things make it work:

1. **One note file per change.** Each pull request adds a small file to a
   `changelog.d/` folder, named after the pull request. Separate files mean no
   merge conflicts on a shared changelog.
2. **A type per note.** The file name carries a type (feature, fix, removal,
   security), so the release can group notes without anyone sorting them.
3. **CI refuses a change without a note.** A check fails any pull request that
   touches application code and adds no note. Docs-only changes are exempt.
4. **The release compiles the notes.** Our release script gathers the files
   into the changelog, grouped by type, and deletes them.

Since we switched in January, every release has gone out with its notes on
time: 14 releases in a row, against 5 of the 14 before. The support team says
customers ask fewer "what changed?" questions, though we haven't counted them.

The one cost: contributors grumble about writing a note for a one-line fix.
We think the habit is worth it.
