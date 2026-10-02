---
name: writing-style
description: "Per-surface writing references for workflow artifacts (design notes, investigation write-ups, decision records), questions that ask a person to decide or answer something, and the optional cold-reader check. Load the matching reference before writing one of these. Also use when asked how any kind of writing should be written, or when defining or polishing a style; code comments, commit messages, PR descriptions, review comments and chat have no reference and use the writing-for-humans output style."
argument-hint: "[artifacts | questions | cold-reader]"
---

# Writing Style

One home for per-output writing guidance. The always-on core (one standard for all prose, context-independence, spoken voice, personal voice patterns, and the register split) lives in the `writing-for-humans` output style and applies when that style is selected. If you need its rules while another style is selected, read `${CLAUDE_PLUGIN_ROOT}/output-styles/writing-for-humans.md`; do not change the selected style. These references carry the full per-surface treatment: formats, boundaries, and examples.

Requested output: $ARGUMENTS

If an argument is named above, read the reference in its table row. If none is named, pick the reference that matches what you are about to write, or list the table when asked what exists.

## References

| Argument | Output | Reference |
|---|---|---|
| `artifacts` | Workflow artifacts | `${CLAUDE_SKILL_DIR}/references/artifacts.md` |
| `questions` | Questions we ask the human | `${CLAUDE_SKILL_DIR}/references/questions.md` |
| `cold-reader` | The cold-reader check (mechanism, not a surface) | `${CLAUDE_SKILL_DIR}/references/cold-reader.md` |

## Contract for skills

A skill that produces one of these outputs points at the reference ("style: the `writing-for-humans:writing-style` questions reference, read before writing") instead of carrying rules inline. A skill that copies the rules will drift from them and quietly enforce an older version.

Where a team has its own documented coding or writing standards, those are the authority and outrank anything here. These references carry what is personal or more specific.

## Adding or polishing a style

For package maintenance, a new output type means a new reference, a row in the table, its argument in the hint, and the surface added to this skill's description. See the package's `MAINTAINING.md` in the source repository. Keep the floor and references consistent. For personal customization, follow the plugin README and work in user-owned configuration, never the installed plugin cache. A surface without a reference uses the output-style floor.
