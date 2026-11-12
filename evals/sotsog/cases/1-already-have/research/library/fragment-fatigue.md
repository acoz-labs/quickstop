# Fragment fatigue: when per-change release notes go wrong

Source: https://blog.example.com/tobias-lindqvist/fragment-fatigue
Author: Tobias Lindqvist, independent consultant
Published: 2026-07-07

Per-change fragments have a failure mode nobody mentions in the launch posts.
On two teams I've worked with, the CI check became a box to tick: people wrote
"misc fixes" or "see PR" to get past it, and the compiled notes were worse than
the hand-written ones they replaced. Both teams ended up adding a "skip notes"
label for trivial changes, and a reviewer step to read fragments like any
other text. Without those, the check measures that a file exists, not that a
note is useful.
