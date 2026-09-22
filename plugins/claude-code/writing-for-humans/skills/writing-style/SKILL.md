---
name: writing-style
description: "The canonical home for how each kind of writing we produce gets written: code comments, review comments, PR descriptions, commit messages, chat messages, workflow artifacts, and tickets. Load the matching reference before producing one of these, when asked how something should be written, or when defining or polishing a style. Skills that produce output point here instead of restating rules."
argument-hint: "[output type, such as questions; omit to list the references]"
---

# Writing Style

One home for per-output writing guidance. The always-on core (one standard for all prose, context-independence, spoken voice, personal voice patterns, and the register split) lives in the `writing-for-humans` output style and applies when that style is selected. If you need its rules while another style is selected, read `../../output-styles/writing-for-humans.md` relative to this skill directory; do not change the selected style. These references carry the full per-surface treatment: formats, boundaries, and examples.

Resolve the paths below relative to this installed skill directory, never the working directory.

## References

| Output | Reference |
|---|---|
| Workflow artifacts | `references/artifacts.md` |
| Questions we ask the human | `references/questions.md` |
| The cold-reader check (mechanism, not a surface) | `references/cold-reader.md` |

<!-- Add rows as you write references: code-comments, pr-descriptions,
     commit-messages, review-comments, chat, tickets. The three shipped here
     are the ones carrying mechanisms rather than taste. -->

## Contract for skills

A skill that produces one of these outputs points at the reference ("style: `references/questions.md`, read before writing") instead of carrying rules inline. A skill that copies the rules will drift from them and quietly enforce an older version.

Where a team has its own documented coding or writing standards, those are the authority and outrank anything here. These references carry what is personal or more specific.

## Adding or polishing a style

For package maintenance, a new output type means a new reference and a row in the table. Keep the floor and references consistent. For personal customization, follow the plugin README and work in user-owned configuration, never the installed plugin cache. A surface without a reference uses the output-style floor.
