# Changes

Each non-trivial change gets one folder, `docs/changes/<issue>-<slug>/`, for
example `docs/changes/42-export-csv/`. It holds `plan.md` and, when useful,
`intent.md` (why and for whom) or `spec.md` (precise behaviour). Start the plan
from `_template/plan.md`.

The plan's Issue section links its issue, and the PR description links the
folder. The author commits `plan.md` alone as the first commit on the PR
branch; an independent maintainer reviews it before code is written. When the
work departs from the plan, the same commit updates `plan.md`. Code review
checks the diff against it.

Folders stay after shipping as the record of what was intended and why. The
shipping PR still updates the durable docs (architecture, operations,
decisions) from what shipped; the plan does not replace them.

`docs/operations/sdlc.md` says when a plan is required. `bin/validate-solution-plans`
checks that each folder has a `plan.md` with every section and an issue link.
Plans written under the earlier `docs/plans/` convention stay where they are.
