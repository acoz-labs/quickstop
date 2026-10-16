---
name: shipshape-review
description: Execute independent exact-head review, require correction and re-review, and hand off fixed-candidate acceptance.
---

Read [runtime obligations](../../references/runtime.md) and
[operator protocol](../../references/operator.md) relative to this installed file.
Use a fresh reasoning context, separate process/session and clean exact-head
workspace. Independently execute required checks and the real artifact scenario;
author reports, approval state, CI and schema success alone are insufficient.
Record actionable findings. Author corrections require new-head re-review;
reviewer-written fixes require another independent reviewer. Missing reviewer,
tools, auth or sandbox blocks progress. Never represent a switched account as
independent execution. The [helper](../../scripts/shipshape.py) authenticates no role.
Only a trusted adapter may bind actual process provenance and call existing
repository gates. Merge-ready is a recommendation, not a merge permission.
After verified merge, hand off the actual merged SHA and retained artifact to
independent acceptance through existing gates. Do not reuse review as acceptance
or declare release from contributor tests. Preserve scope through closeout.
