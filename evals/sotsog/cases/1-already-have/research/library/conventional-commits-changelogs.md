# Generate the changelog from your commits instead

Source: https://devnotes.example.org/generate-changelog-from-commits
Author: Mei Tanaka, maintainer of several open-source libraries
Published: 2026-04-22

Instead of separate note files, write commit titles in a fixed shape
(`feat: ...`, `fix: ...`) and let a tool build the changelog from them at
release time. Nothing extra to write, and nothing to forget. The catch: commit
titles are written for developers, so the changelog reads like a commit log.
Works best for libraries whose users are developers.
