---
name: schema-rules
description: Naming and structure rules for orchard database migrations.
---
# Schema rules

- One table per migration.
- Name a migration `<number>_<verb>_<table>`, for example `0042_add_reason_code_to_movements`.
- Every migration has a reverse step that restores the previous schema exactly.
- Quantities are `INTEGER`; never use `REAL` or `NUMERIC` for a count.
- Hand edits to anything in `migrations/` are not allowed; always generate a fresh migration through `bin/migrate new`.
