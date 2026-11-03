---
name: release-notes
description: Writes orchard release notes for shop managers. Read the merged pull requests since the last tag with git log, group the changes by how many shops they affect with the widest first, write one short paragraph per change that says what changes for a person at the till or in the warehouse, leave out module and function names, ticket numbers and developer names, put the notes under a heading with the version and date, and save them to docs/releases/<version>.md before the release is tagged.
---
# Release notes

1. List the merged pull requests since the last tag: `git log --merges --oneline <last-tag>..HEAD`.
2. Group the changes by how many shops they affect, widest first.
3. For each change, write one short paragraph on what changes for a person at the till or in the warehouse.
4. Leave out module and function names, ticket numbers and developer names.
5. Put the notes under a heading with the version and the date.
6. Save them to `docs/releases/<version>.md` before the release is tagged.
