# Evidence-based scoring

Scores are Claudit heuristics, not an Anthropic security certification or measured
performance. Preserve the six categories and weights, but score only assessed
applicable categories. A category with no applicable components is N/A; an
unreadable scope is unknown; partially inspected applicable scope is partial.
Neither receives a number or contributes to the numeric denominator. Do not give
unknowns a 100, invent deductions, or round a heuristic into certainty.

## Mandatory score gate

For any numeric score or letter grade, run the read-only helper `score` command.
If no helper call is made, report findings and coverage without scores/grades.
The helper consumes repeated CLI arguments directly; no input/output file or
scratch aggregate is needed. Use these forms:

- `--category <slug>:assessed:<0-100>` only when the applicable category has been
  assessed with sufficient actual file/native evidence; apply the deductions below.
- `--category <slug>:partial` when some applicable evidence was assessed but
  material evidence remains redacted, unread or unavailable.
- `--category <slug>:unknown` when applicable coverage has not been established.
- `--category <slug>:na` only when the category is genuinely outside scope or no
  applicable components exist, not as a substitute for missing evidence.

Missing categories default to unknown. Partial/unknown/N/A with a numeric value
is rejected. “No confirmed defects” is not evidence of complete coverage.

For example, a global audit with redacted MCP details, unassessed security policy,
unread installed plugin components and no project instruction scope might use:

```sh
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/runtime.py" score \
  --category over-engineering:assessed:100 \
  --category claudemd-quality:na \
  --category security:unknown \
  --category mcp-config:partial \
  --category plugin-health:unknown \
  --category context-efficiency:unknown
```

Use actual observations, not these example values. This returns a subset score
only for the assessed 20 weight units, with no overall score or grade. Display
coverage and the unassessed categories. Do not attach an A+ or category score to
partial/unknown rows. Global-only project instruction quality is N/A, not 100.
An installed registry entry does not establish component health; redacted MCP
metadata does not fully assess its transport/auth/runtime configuration; unread
sandbox/managed/session policy prevents a comprehensive security score. Unknown
actual loading similarly limits context-efficiency coverage.

The helper fixes the six weights and exposes `assessed_weight`, `applicable_weight`
and `coverage_percent`. Any partial/unknown category permits at most an
`assessed_subset_score`, with no letter grade. Only complete coverage of applicable
categories can return `overall_score` and `grade`. All-N/A yields neither score nor
grade. These are arithmetic/coverage checks, not a claim that the model's supplied
coverage classification or source-backed deductions are independently verified.

| Category / slug | Weight |
|---|---:|
| Over-engineering / `over-engineering` | 20 |
| Instruction quality / `claudemd-quality` | 20 |
| Security posture / `security` | 15 |
| MCP configuration / `mcp-config` | 15 |
| Plugin health / `plugin-health` | 15 |
| Context efficiency / `context-efficiency` | 15 |

Start assessed categories at 100. Apply these deductions only to observed,
source-backed defects. Clamp at zero. Deduplicate the same underlying defect
across agents and categories; choose the primary consequence. No bonuses cancel
out real defects. Report count, target, evidence and rationale for each deduction.

| Category | Issue type | Deduction | Required evidence |
|---|---|---:|---|
| Over-engineering | `redundant-instructions` | 5 each, max20 | Same meaning repeated in simultaneously applicable inputs, with no intentional scope distinction |
| Over-engineering | `duplicated-hook` | 10 each, max20 | Equivalent actions observed running redundantly, not merely similar names |
| Instruction quality | `instruction-conflict` | 15 each, max30 | Mutually incompatible applicable instructions |
| Instruction quality | `broken-import` | 10 each, max20 | Required import resolves missing/unreadable, accounting for trust and exclusions |
| Instruction quality | `stale-reference` | 5 each, max15 | A claimed existing project resource demonstrably absent, not an example/planned path |
| Instruction quality | `circular-import` | 10 | Verified source-relative import cycle |
| Security | `published-secret` | 30 | Secret material in a shared/published surface; redact actual value |
| Security | `broad-bash-allow` | 15 | Effective broad shell permission contradicts user's stated review requirement |
| Security | `unexpected-bypass` | 20 | Effective bypass conflicts with intended protections; account for sandbox/managed policy |
| MCP | `invalid-transport` | 15 each, max30 | Current transport-specific required fields invalid |
| MCP | `missing-binary` | 10 each, max20 | Required local stdio executable unavailable in actual launch environment, not unknown wrapper/PATH |
| Plugin | `missing-install-path` | 20 each, max40 | Applicable registered install path missing |
| Plugin | `invalid-component` | 10 each, max30 | Native validation or current schema confirms an invalid declared component/path |
| Plugin | `invalid-manifest` | 15 | Present manifest invalid; absence alone is valid |
| Context | `redundant-loaded-content` | 10 each, max20 | Proven duplicate text actually loaded in same context |
| Context | `excess-hook-output` | 10 | Observed repeated unnecessary hook output enters model context |

Do **not** deduct for missing optional settings, instructions, MCP, plugins,
skills, memory, env blocks, hook timeouts, absent telemetry, old publication date,
supported `commands/`, missing optional manifest fields, disabled installs,
perceived formatting style, explicit narrow permissions, or unobserved usage.
A glob with no current matches may intentionally target future files; an absolute
deny path outside the current home may intentionally protect another location.
Neither establishes a wrong setting or dead rule. Without explicit target intent
or demonstrated failure of a required operation, report an optional/unknown-intent
observation with **no deduction**. Do not infer intent from the test/current home,
repository contents or naming alone. No official-marketplace exemption exists. A source-verified outdated version can
be an optional update; age alone is not a defect. Word/line count thresholds
(including 200-line advice) guide discussion, not proof that content is harmful.

Token accounting distinguishes always-loaded instructions, conditional rules,
on-demand skills, discovered/deferred/always-loaded MCP tools and observed hook
output. Static JSON file size is not startup prompt size. Use measured native
observations where available; label chars/4 estimates with their assumptions.
Never claim performance improvements from score changes alone.

The helper computes sum(score * weight) / sum(assessed weights). Only for complete
applicable coverage, grades are >=95 A+,
>=90 A, >=75 B, >=60 C, >=40 D, otherwise F. Severity is consequence-based:
active exposure/broken function first, then material maintainability, then optional
adoption. Separate security severity from arbitrary score impact.

Use issue types above in scoped decision fingerprints. Optional features use
`feature-adoption`; new verified defects can use a precise stable issue slug with
a clearly explained heuristic impact. Match scoped history as defined in the
decision protocol, never basename-only. Stale decisions annotate, not suppress.
