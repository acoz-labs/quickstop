---
name: writing-style
description: "Fuller writing references for workflow artifacts (design notes, investigation write-ups, decision records), questions that ask a person to decide or answer something, and the optional cold-reader check. Load the matching reference before writing one of these, or when asked how such writing should be done."
argument-hint: "[artifacts | questions | cold-reader]"
---

# Writing Style

The `writing-for-humans` output style holds the standard for everything a person reads. These references add what it doesn't say for three cases. If you need the standard while another style is selected, read `${CLAUDE_PLUGIN_ROOT}/output-styles/writing-for-humans.md`; don't change the selected style.

Requested output: $ARGUMENTS

If an argument is named above, read the reference in its row. If none is named, pick the reference that matches what you're about to write, or list the table when asked what exists.

| Argument | Output | Reference |
|---|---|---|
| `artifacts` | Workflow artifacts | `${CLAUDE_SKILL_DIR}/references/artifacts.md` |
| `questions` | Questions asked of a person | `${CLAUDE_SKILL_DIR}/references/questions.md` |
| `cold-reader` | The cold-reader check (a mechanism, not a surface) | `${CLAUDE_SKILL_DIR}/references/cold-reader.md` |

A skill that produces one of these outputs points at the reference instead of copying its rules, so it can't drift to an older version. A team's documented standards outrank these references. Package maintainers adding a reference follow `MAINTAINING.md` in the source repository; personal changes belong in your own configuration, never the installed plugin cache.
