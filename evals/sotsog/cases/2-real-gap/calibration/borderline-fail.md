# Lock-safe migrations: adopt for Lanternhall

We'll adopt safer migrations. Work will follow. This should help.

Date 2026-11-12. Sources: the post and the library.

## The idea in brief

Make migrations safer.

## What the evidence shows

Promising.

- **Who gains:** not obvious.
- **Measured against:** some before-and-after.
- **What's missing:** a few details.
- **Whose conditions:** similar enough.
- **Independent support:** other sources exist, including rehearsals-are-a-privacy-risk.md and online-schema-change-tools.md.

## How it compares with what we do

| Principle | How they do it | How we do it | Fit |
|---|---|---|---|
| Safer migrations | various | not much | gap |

## Why this decision

There have been some issues with migrations, and this seems like good practice.

## Revisit when

- If needed.

## Implementation brief

Set up a migration linter and add timeouts as needed.

## Sources

- link.md, read 2026-11-12.
- rehearsals-are-a-privacy-risk.md, read 2026-11-12.
- online-schema-change-tools.md, read 2026-11-12.
