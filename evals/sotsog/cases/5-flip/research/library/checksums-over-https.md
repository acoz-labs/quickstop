# Checksums are enough for most small projects

Source: https://release-craft.example.org/checksums-are-enough
Author: Release Craft (community guide to release engineering)
Published: 2026-03-18

Publish a `SHA256SUMS` file alongside each release, on the same HTTPS page,
and tell downstream users to check it. It catches corrupted and swapped
downloads, needs no tooling and costs nothing to maintain. It doesn't prove
who built the file or from which commit; for that you need signing and
provenance.
