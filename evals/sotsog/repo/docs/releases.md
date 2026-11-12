# Releases

We release once a month, on the first Tuesday.

1. A maintainer runs `bin/release <version>`, which compiles `changes/` into
   `CHANGELOG.md`, tags the commit and builds a source tarball and a wheel.
2. The maintainer uploads both files and a `SHA256SUMS` file to the project's
   releases page.
3. The network's IT team deploys from the tag. The Coastline Library
   Consortium downloads the tarball, checks it against `SHA256SUMS` and
   deploys it on its own servers.

Releases are not signed, and we publish no record of how they were built.
Nobody has asked for either so far.
