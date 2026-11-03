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
release gate: nineteen synthetic fixtures with planted findings, run by
`bin/claudit-eval` with a pinned model and `--max-cost-usd`. It isn't a per-PR
check. A release compares its numbers with the recorded
[baselines](claudit-eval-baselines.md) using the same model, judge and run count,
and records each arm's conditions (tools granted, runs per case, model, judge,
Claude Code version). Claudit reads docs live, so the gate runs it twice: with
`--web-fetch` (the live path) and without (the shipped-catalog path). Both must meet
the release bars; the live path must also beat a plain prompt given the same
WebFetch grant. The suite ships in the repository rather than in the plugin, so
measuring Claudit doesn't change plugin bytes.

### `--deep` and the #193 gate graders

The suite itself is frozen at the #192 baseline (its scan-derived `structure-*`
graders follow the scan, rebuilt with `python3 tests/test_claudit_case_graders.py
--write`). Two additions live outside it, in `bin/claudit-eval`:

- `run --arm claudit-deep` runs `/claudit:claudit --read-only --deep` headless on the
  candidate (`--plugin`, default `plugins/claudit`), the way `headless` runs Claudit,
  in the same fresh `<tmp>/claudit-combined-*/home/cwd` scaffolds as
  `doctor-combined`, and grades the report with each case's graders. `--deep`'s
  nested `claude -p` can't run inside `claude plugin eval`, whose sandbox has no
  network, so this arm stands in for it. The nested `/doctor prompt-audit .` runs with
  `doctor-combined`'s flags (project settings only, Edit, Write and NotebookEdit
  denied, in a folder that is never trusted, so Bash is denied too) plus
  `Skill(claudit:claudit)` denied; the comparison with `doctor-combined` is
  symmetric. The nested call also denies Bash by flag, so the read-only claim holds in a
  trusted project too; in these untrusted scaffolds that changes nothing. Step 1 of the
  skill passes `--model sonnet --max-budget-usd 0.5`; the runner sets
  `CLAUDIT_DEEP_MODEL` to the arm's `--model`, which pins the nested model to it. The
  helper appends the nested call's status, model, budget, cost, time and denials to
  `CLAUDIT_DEEP_RECORD`, and the run's cost adds them to the outer call's. `command.txt`
  states the nested model and budget. `headless` records the same for a real
  repository.
- `gate --rule principles-skill|doc-skills|history-lines <reports or folders>`
  grades saved reports at $0. `principles-skill` (rule 6) fails a report that
  proposes a skill or slash command for the principles anywhere, Optional notes and
  Also worth knowing included; a question, a reversal ("isn't necessary today, but
  worth adding later") or "add one" after a negated form still counts, and a decline
  line ("Declined: …") or another named skill doesn't. `doc-skills` (rule 4) lists each documentation page a
  numbered Top changes item proposes a skill for ("Add a skill for X", "Turn X into a
  skill", "Add skills for A and B", "Make X a skill") and fails more than one, any
  translation or reference page, or one with no stated reason. `history-lines` (rule 4) passes when a finding block names
  `docs/repository.md`, each of quickstop's two stale history lines (by line number or
  its words) and calls it history or stale; a decline doesn't count. Their positive, negative and attacker
  controls are in `tests/test_claudit_gate_graders.py`.

Before a paid run, every fixture hook must run on the host toolchain: scaffold each
case and run its Stop hook with the run's environment. f19's Stop hook runs
`go test ./...`, so a mise-managed host needs a Go version selected for folders
outside any project (for example `MISE_GO_VERSION`); otherwise the hook fails and
`doctor-combined` answers that failure instead of auditing (#192).

## Required scenarios

- Install the retained marketplace package and verify the native inventory shows
  one skill (`claudit`) and one agent (`auditor`, Sonnet, read-only tools), and no
  `knowledge`, `refresh` or `status` skill. Record native validation
  (`claude plugin validate --strict`) and inventory results.
- Run a headless read-only audit on a real repository at the candidate and on one
  other repository (`bin/claudit-eval headless`, which keeps each command line and
  script-checks the report against the scan of the same clone). Each report states the intent, gives Correctness, Alignment
  and Coverage grades with confidences, and ranks its top changes with exact diffs
  and doc citations, following the plan-length rule in the skill's report step. Record wall time and cost at list prices.
- Compare the consumer's files, Git index and working tree before and after a
  read-only audit: nothing changes, no cache directory is created (check
  `~/.cache/claudit` and `CLAUDIT_CACHE_DIR`) and nothing is written outside the
  project.
- Audit with the docs unreachable (WebFetch denied). The report stays graded and
  says in one footer line that the shipped catalog was used.
- Audit a valid current configuration and a separate fixture with real defects.
  Compare findings to official docs and fixture ground truth. Supported defaults,
  `Bash(x:*)` rules, matcher-less Stop hooks, gitignored `CLAUDE.local.md` files and
  deny rules for secrets must not be reported as defects.
- Run the helper's unit tests on Python 3.9 and the pinned 3.11.
- Apply one selected change in place and verify only its intended content changes.
  A declined or unselected change must not be applied. Dismissing a suggestion
  writes only the user's own file under `${CLAUDE_PLUGIN_DATA}/dismissed/`, and the
  next audit by that user omits it; with `--shared` it writes only
  `.claude/claudit-dismissed.json`, and every audit omits it.
- Run a `--deep` audit headless (`bin/claudit-eval run --arm claudit-deep`, or
  `headless --invoke "/claudit:claudit --read-only --deep"`): the nested
  `/doctor prompt-audit .` runs read-only with project settings only and Bash
  denied, its cost and time are recorded with the run, and each of its findings is
  kept or dropped with a reason. Without a login for the nested call the footer says
  the prompt audit couldn't run and the report stays graded.
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
After publication, install from the advertised marketplace, verify the accepted
package digest and smoke its skills. Retain predecessor version/source and tested
consumer update/recovery instructions. Model-driven audit judgments remain
advisory; document any observed limitations and do not claim universal perfection.
