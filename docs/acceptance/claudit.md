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
release gate: five synthetic fixtures with planted findings, run by
`bin/claudit-eval` with a pinned model and `--max-cost-usd`. It isn't a per-PR
check. A release compares its numbers with the recorded
[baselines](claudit-eval-baselines.md) using the same model, judge and run count,
and records each arm's conditions (tools granted, runs per case, model, judge,
Claude Code version). Claudit reads docs live, so the gate runs it twice: with
`--web-fetch` (the live path) and without (the shipped-catalog path). Both must meet
the release bars; the live path must also beat a plain prompt given the same
WebFetch grant. The suite ships in the repository rather than in the plugin, so
measuring Claudit doesn't change plugin bytes.

## Required scenarios

- Install the retained marketplace package and verify the native inventory shows
  one skill (`claudit`) and one agent (`auditor`, Sonnet, read-only tools), and no
  `knowledge`, `refresh` or `status` skill. Record native validation
  (`claude plugin validate --strict`) and inventory results.
- Run a headless read-only audit on a real repository at the candidate and on one
  other repository. Each report states the intent, gives Correctness, Alignment
  and Coverage grades with confidences, and ranks 3 to 7 changes with exact diffs
  and doc citations. Record wall time and cost at list prices.
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
  writes only `.claude/claudit-dismissed.json`, and the next audit omits it.
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
