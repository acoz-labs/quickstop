# Signing theatre: when release signatures protect nobody

Source: https://blog.example.com/hannah-osei/signing-theatre
Author: Hannah Osei, security researcher
Published: 2026-09-10

A signature only protects users who check it. For a small project with a
handful of downstream users and nobody verifying, signing adds setup, upkeep
and one more thing to break in the release, while the actual risk (a stolen
maintainer account pushing a bad tag) is untouched. Start with what your
consumers will verify; if nobody will, publish checksums over a trusted channel
and spend the time elsewhere.
