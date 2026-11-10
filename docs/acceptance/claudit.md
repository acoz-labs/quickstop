# Claudit acceptance

Supported target: **Claude Code**. A compatible package parser does not establish
support in another harness. Use the retained package and isolated native
configuration described in [delivery](../delivery.md). Record the exact host,
resolved models, package version/digest, commands, inputs, outputs and observed
file effects. Passing manifest validation alone is not acceptance.

## Isolation and evidence

Use synthetic repositories, a separate home and Claude configuration, and a
working directory outside the operator's instruction-file ancestry. Confirm the
native initialization inventory contains only the intended plugin and built-ins.
Disable unrelated MCP connections, plugin synchronization and hooks where needed
for isolation without replacing the product's own workflow. Keep credentials out
of fixture files, prompts, logs and published evidence. Compare consumer files,
Git index, working tree and cache state before and after each scenario.

Native `claude plugin eval` is useful when available, with local reports and
bounded runs, but its scaffolds do not load project configuration. Supplement it
with direct isolated Claude Code sessions for actual settings and installation
behavior. Graders must inspect actual outputs and file/tool effects; a requested
action, an agent's success claim or matching headings is not evidence it happened.

## Eval suite and baselines

[`evals/claudit/`](../../evals/claudit/README.md) is Claudit's `claude plugin eval`
release gate: nineteen synthetic fixtures, run by `bin/claudit-eval` with a pinned
model and `--max-cost-usd`. It isn't a per-PR check. Since 5.0.0 every grader is a
script grader built from the scan of each fixture, so a fixture's expected findings
are what the scan raises there, and no judge grades anything. The same checks run on
real-repository reports (`headless`). Claudit no longer fetches docs, so the gate
runs once, without `--web-fetch`. The 4.x tables in the
[baselines](claudit-eval-baselines.md) stay as history; they measured graded reports
and don't compare with 5.0.0's findings lists. The suite ships in the repository
rather than in the plugin, so measuring Claudit doesn't change plugin bytes.

A paid gate screens a candidate tree at one run per case (fixtures and the real
repositories) before the full three-run gate. The graders, controls and fixtures are
frozen at the screened tree; recorded reports may be regraded at $0, and any later
change to the tree means a new screen before the gate.

Before a paid run, every fixture hook must run on the host toolchain: scaffold each
case and run its Stop hook with the run's environment. f19's Stop hook runs
`go test ./...`, so a mise-managed host needs a Go version selected for folders
outside any project (for example `MISE_GO_VERSION`); otherwise the hook fails and
`doctor-combined` answers that failure instead of auditing (#192).

## Required scenarios

- Install the retained package from a local directory marketplace (never a
  `file://` URL) with `HOME` and `CLAUDE_CONFIG_DIR` set to a fresh `mktemp -d`, and
  verify the native inventory shows one skill (`claudit`) and no agent, the installed
  version, and the cached bytes against the plugin tree. Updating from the previous
  release leaves the old cache with an `.orphaned_at` marker; that is expected. Read
  the full command output; never truncate it. Record native validation
  (`claude plugin validate`) and inventory results.
- Run a headless read-only audit on a real repository at the candidate and on other
  repositories (`bin/claudit-eval headless`, which keeps each command line and
  script-checks the report against the scan of the same clone). Each report is a
  findings list with real `path:line` citations and exact fixes, or "Nothing found",
  with the footer recommending `/doctor prompt-audit`. The reviewer reads every
  finding against the repository. Record wall time and cost at list prices.
- Compare the consumer's files, Git index and working tree before and after a
  read-only audit: nothing changes, no cache directory is created and nothing is
  written outside the project.
- Audit a valid current configuration and fixtures with real problems. Compare
  findings to the fixture's ground truth. Supported defaults, `Bash(x:*)` rules,
  matcher-less Stop hooks, gitignored `CLAUDE.local.md` files and deny rules for
  secrets must not be findings, and nothing the scan didn't raise may appear.
- Run the helper's unit tests on Python 3.9 and the pinned 3.11.
- Apply one selected fix in place and verify only its intended content changes. An
  unselected fix must not be applied. Dismissing a finding writes only the user's
  own file under `${CLAUDE_PLUGIN_DATA}/dismissed/`, and the next audit by that user
  omits it; with `--shared` it writes only `.claude/claudit-dismissed.json`, and
  every audit omits it.
- Exercise branch delivery with staged unrelated changes, unstaged edits and an
  existing branch name against a local test remote: the user's index and working
  tree are preserved, the PR branch holds only the selected paths and an existing
  branch is never reused. Label simulated remote checks honestly; don't send an
  external test PR unless one is explicitly in scope.

## Acceptance and publication

Run repository checks on the exact candidate and compare the retained extracted
package digest. Record every issue criterion and configured delivery criterion
with openable sanitized evidence. A failed behavior returns to implementation;
do not weaken a grader or replace a native scenario with a static assertion.
After publication, install from the advertised GitHub marketplace in the same fresh
`HOME` and `CLAUDE_CONFIG_DIR`, verify the version, the accepted package digest and
the cached bytes against the tagged plugin tree, and smoke its skill. Retain predecessor version/source and tested
consumer update/recovery instructions. Model-driven audit judgments remain
advisory; document any observed limitations and do not claim universal perfection.
