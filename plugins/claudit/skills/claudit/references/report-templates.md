# Audit report

Prefer a compact report with evidence links over decorative boxes. Preserve these
fields so uncertainty and partial coverage stay visible.

## Configuration map

- Host/plugin version, session cwd, project/main-worktree and config-directory scope.
- Relevant files by scope/category with present/missing/unreadable/corrupt state.
- Effective-state observations versus filesystem candidates.
- Included/omitted counts, excluded directories and unassessed managed/session inputs.
- Requested focus, applicable scoped decision count and unmatched legacy history.

## Findings

Lead with the most consequential observed result. For every defect give:

| Finding | Scope and file/line | Observed evidence | Official source/section | Consequence | Suggested change |
|---|---|---|---|---|---|

Redact secrets and private values. Separate confirmed defects, optional adoption
and unresolved questions. If focused, put relevant findings first and deepen their
evidence without misrepresenting other scopes as fully checked. Deduplicate
cross-agent findings. Note matching decisions with reason, scope and any staleness.

## Score and limits

Show each assessed category, deduction rationale and score; mark N/A and unknown.
Include weights and any renormalization. If materially incomplete, label the
result “assessed-subset score”; otherwise show the overall score/grade. Research
source dates, current/recorded host, stale/degraded domains, unreadable files and
failed agents remain explicit. A fresh cache is not semantic verification.

## Optional improvements

Explain relevance and tradeoff, not just missing features. Context figures specify
measured versus estimated, what loads and when, and what remains unknown.
Label documented defaults/configured expectations separately from observed runtime
behavior. In particular, unspecified alwaysLoad is not verified tool deferral;
actual session evidence must account for tool search and environment overrides.
Read-only audits end here without edit/decision prompts. For authorized selected
fixes, show exact targets, delivery path, actual validation and observed before/
after differences. A PR summary contains only sanitized project information.
