# Plan: Claudit 5.0.0, a thin checker

## Issue

Refs https://github.com/acoz-labs/quickstop/issues/207

Claudit 5.0.0 reports only what its scan script can prove (stale references and
history lines, unenforced gates and must-rules, the check command, scope, a
report-only always-loaded table, missing skill names, verbatim duplicates) as a
list of findings with real lines and exact fixes. Grades, the rubric, skill and
feature advice, the Coverage plan, `--deep`, the Intent paragraph and the
auditor subagent go. This PR is the plugin PR; the pointer PR follows after
acceptance and the `claudit-v5.0.0` tag.

The branch starts from PR #197's head `1ece301e` (closed unmerged), as triage
says, so #197's seven reviewed 4.3.1 commits sit under this plan commit. The
first code step rebases the branch onto current `main`; a trial rebase is clean.
After that the plan's commit ID changes but its blob doesn't, so plan review is
named by blob.

## Files that change

Plugin package (`plugins/claudit/`, version 4.3.1 to 5.0.0):

- Manifest (`.claude-plugin/plugin.json`): version `5.0.0`; the description says
  it lists findings in instruction files and settings that `/doctor` doesn't
  cover; the `grading` keyword goes.
- Skill (`skills/claudit/SKILL.md`): rewritten and much shorter. One scan call,
  then the report. Allowed tools shrink to `Read Grep Glob` and the `scan` and
  `dismiss` script calls: no WebFetch, no `new-pages`, no `deep`, no
  `claude --version` (the scan reads the version itself). Arguments keep
  `--read-only`; `--user` and `--deep` go. The model words each scan finding
  and may drop one only with a stated reason that quotes the repository's own
  text at a `path:line`. It never adds a finding the scan didn't raise.
  Report shape:

  ```markdown
  # Claudit: <project>

  <"Nothing found." or "<n> findings.">

  1. `<path>:<line>` <what's wrong, one or two sentences>.
     Fix: <exact fix; settings and hooks in a fenced block>
     Source: <doc URL> (when the finding has one)

  ## Not reported
  - `<path>:<line>`: <reason, quoting the repository at `<path>:<line>`>
  - Respected: `<path>:<line>` has no hook; `<decision path>:<line>` decided against hooks ("<reason>" or no reason given).

  ## Always loaded
  <the scan's table, verbatim>

  ---
  <the scan's scope lines, when any: files above the repository, a CLAUDE.md above that stops AGENTS.md being read, symlinks>
  Not checked: user and managed settings, settings validity (`/doctor`), server-side branch protection.
  Run `/doctor prompt-audit` for contradictions and wording.
  Claudit 5.0.0; audited commit <sha>; <n> dismissed (<where stored>)
  ```

  "Not reported" is omitted when empty. Apply (step 6) and dismissal stay as
  they are, offered per finding instead of per plan item.
- Apply reference (`skills/claudit/references/apply.md`): "changes" become
  "findings"; behaviour unchanged.
- Scan script (`skills/claudit/scripts/claudit.py`, `VERSION = '5.0.0'`):
  - Kept, ids unchanged so existing dismissals still apply: `stale-ref`,
    `stale-command`, `stale-dep`, `broken-import`, `missing-name`, history
    narrative (today's `stale_candidates`, now findings with id
    `history:<path>:<line>`, keeping the docs-only migration-guide skip and
    `not_a_decline`), `gate-ask`, `stop-hook`, `allowlist`,
    `agents-md-not-loaded`, `oversized` (200 lines), `long-description`,
    `agent-descriptions`, `visible-skill`, and `duplicate` restricted to
    verbatim runs with real line numbers.
  - Each finding carries `path`, `line` (the real line of the cited text, or
    the file's first line for a whole-file fact such as `oversized`),
    `problem`, `fix` and an optional `source` (URL and heading).
  - Declines stay only to suppress `stop-hook` and `allowlist`: a documented
    decision against hooks or pre-approved commands moves that finding to a
    `respected` list with the decision's `path:line` and reason. When a fact
    contradicts the decision's stated reason (today's `reconsider`: f10's
    "hooks can't block Claude from finishing", "there is no check command"
    while `CLAUDE.md` names one; and new, f12's allowlist replaced by project
    `bypassPermissions`, which Claude Code ignores in project settings), the
    finding stays, citing both the decision and the contradicting evidence.
  - Settings that don't parse skip the settings-based checks (allowlist, ask
    rules, hooks) and add a "not checked" footer line naming the file, so a
    broken `settings.json` never yields false "not allowed" findings.
  - Removed: `grades_of`, `plan_of`, `CHANGE_TITLES`, baseline status,
    profiles, signals used only for Intent, `procedure_docs` and
    `procedure-skill`, `optional`, handoffs, `new_pages`, `deep` and
    `claude_doctor`, and the checks outside the issue's list (`invalid-json`,
    `wrong-type`, `matcher-type`, `matcher-ignored`, `hook-script`,
    `hooks-file`, `default-mode`, `auto-mode`, `mcp-location`, `flat-skill`,
    `skill-missing`, `write-rule`, `secret-deny`, `claudeignore`, `lsp`,
    `plugin-validate`, `plugin-eval`, `no-instructions`,
    `undocumented-checks`, `git-hooks`, `too-large`). Paraphrase matching
    goes.
  - Output: `findings`, `respected`, `context` (table), `scope`, `footer`,
    `dismissed`, `inventory` (trimmed to what the report and graders read).
  - Doc sources move into the script as a small URL-and-heading map for the
    kept checks; each URL and heading is checked against the live docs once
    at build time and recorded on the PR.
- Feature catalog (`skills/claudit/catalog.json`): deleted.
- Auditor subagent (`agents/auditor.md`): deleted; its job was model-judged
  findings.
- README: rewritten to the new output, with "run `/doctor prompt-audit` first"
  up front, what Claudit checks and doesn't, and an "Upgrading from 4.x" note.
- Changelog (`CHANGELOG.md`, new): a 5.0.0 entry naming the breaking output
  change, what was removed and why (4.3.0 and 4.3.1 gate results).

Eval suite and runner (repository only, not plugin bytes):

- Graders (`evals/claudit/cases/*/graders/`): regenerated. Every grader is a
  script (regex) grader anchored on structure, not phrasing: a `finding-*`
  grader needs a numbered item that cites the expected `path:line` and whose
  fix holds the exact token (for example `Bash(bin/check-notes)`); every case
  gets `no-unraised-findings` (numbered items cite only the case's expected
  locations) and `structure-footer` (version, commit, the `/doctor
  prompt-audit` line); clean cases get `structure-nothing-found`. The grade,
  intent, plan, declined and reconsider graders and all 15 llm graders go.
- Expected findings per case (the successors the issue allows), pinned by the
  scan's unit tests and checked against each fixture by the reviewer:
  - f1: `allowlist` (`bin/ci`), `stop-hook`. f2: `allowlist`, `stale-ref`
    `docs/architecture.md`. f3: `oversized` `CLAUDE.md`. f5, f6: `allowlist`
    (and `stop-hook` on f6). f14: the three `gate-ask` rules, branch
    protection named, `stop-hook` for `bin/check`. f15: `allowlist`,
    `stop-hook`, `visible-skill`, the verbatim `duplicate` group; the two
    paraphrases and the lint list are false if reported. f16: two
    `stale-ref`, `stale-dep`, `allowlist`. f18: `allowlist`
    (`Bash(bun run check)`).
  - f10: `stop-hook` and `allowlist`, each citing `docs/decisions.md` and
    the contradicting evidence. f12: `allowlist` for `bin/test`, citing
    `docs/decisions.md:3` and the ignored project `bypassPermissions`.
  - f13: the fixture gains one must-rule ("Always run `npm test` before you
    report a change as done"), so its no-reason hooks decision suppresses a
    real finding: expected is the "Respected" line with "no reason given" and
    no hook recommended.
  - f17: no numbered finding; the footer's scope lines (the scan already
    writes them) name the parent `CLAUDE.md` and `AGENTS.md`, say the parent
    `CLAUDE.md` keeps the repository's `AGENTS.md` from being read on its
    own, and name the symlink's real file.
  - Clean (0 findings, "Nothing found."): f4, f7, f8, f9, f11 (no must-rule,
    so its hooks decision suppresses nothing), f19, and f17's findings list.
  - Case descriptions (`case.yaml`) follow; prompts, budgets and fixtures are
    otherwise unchanged.
- Grader builder and controls (`tests/test_claudit_fixture_graders.py`):
  rewritten around the citation-anchored form. Each grader has passing
  controls (at least six real phrasings of the item, several taken from the
  screen's recorded reports once they exist) and failing ones (wrong line,
  missing fix token, the item under "Not reported", a negated or
  hypothetical sentence, a citation outside the findings list), plus a
  mutation check per named part.
- Runner (`bin/claudit-eval`): the `claudit-deep` arm and `--deep` plumbing
  go, and the two-docs-path (`--web-fetch`) requirement for Claudit goes,
  since Claudit no longer fetches docs. `headless` script-checks a real-repo
  report against the scan of the same clone: every numbered item's
  `path:line` exists, the cited line holds the quoted text, every item maps
  to a scan finding, and every scan finding is reported, dropped under "Not
  reported" with a `path:line` reason, or dismissed. `summarize` validates
  against the expected suite (cases, grader stems, run counts) so a partial
  run can't read as PASS.
- Old suite tests (`tests/test_claudit_plan.py`, `tests/test_claudit_43.py`,
  `tests/test_claudit_gate_graders.py`, parts of `tests/test_claudit.py`,
  `tests/test_claudit_eval*.py`, `tests/test_claudit_case_graders.py`,
  `tests/claudit_render.py`): removed or rewritten to match; no test of a
  kept check is weakened.
- Marketplace and structure tests (`tests/test_marketplace.py` and
  neighbours): the Claudit inventory is one skill, no agent.

Docs: `evals/claudit/README.md` (cases table, graders), the acceptance doc
(`docs/acceptance/claudit.md`: required scenarios for the findings list, no
`--deep`, no docs-unreachable path, install from a local directory
marketplace), and the baselines doc (a 5.0.0 section; the 4.x tables stay as
history). `docs/repository.md` only if a lesson comes up.

Outside the repository: eval scripts, logs, ledger and results under
`~/factory/retained/quickstop-207/`, written fresh with absolute paths and
reusing the #193 scripts' guard, candidate, live-process, usage and money
checks.

## Order of work

1. After plan review: rebase onto `main` (rebase-only repository), run
   `bin/ci`, push. No behaviour change.
2. Scan script: remove the dropped checks and outputs, add the finding shape,
   `respected`, the contradiction rules and the unparseable-settings guard.
   Unit tests for each kept check (hit, no hit, real line), each removal (the
   id never appears), the suppress and contradict paths, and dismissal ids.
3. $0 scan of the three named real repositories (quickstop `main`, python-sdk
   `af4c6f4`, claude-code-action `c0949c50`, fresh clones, commits recorded):
   read every finding against the files and fix the scan where one is wrong,
   with a fixture-style unit test for the rule, never a repository-name
   special case. Repeated at every head.
4. Skill, apply reference, manifest, catalog and auditor deletions, README,
   changelog. Local `claude plugin validate` on the repository and plugin.
5. Eval: graders and controls, f13 fixture line, runner changes, eval and
   acceptance docs. `bin/ci` and `bin/check-marketplace --base origin/main`.
6. Simplify pass over the whole diff; open the PR for review.
7. After review clears the tree for the screen and the lead gives a go:
   screen at n=1 (19 fixtures and the three named repositories; the reviewer
   runs the held-out one). Fix and re-review if the screen fails, within the
   four code rounds.
8. On a reviewer-cleared tree and the lead's go: the full n=3 gate. Results
   posted on #207, not committed.
9. Clean-install check from a local directory marketplace.

## Risks

- **Breaking output for current users.** Anyone reading grades or the plan
  loses them. Contained by the major version, the changelog entry and the
  README's upgrading note; 4.2.0 stays installable from its tag.
- **Dropping config checks hides real defects** (invalid JSON, array
  matchers, ignored `bypassPermissions`). The footer says settings validity
  isn't checked and points at `/doctor`; the unparseable-settings guard stops
  false findings; f3's dropped defects are graded as unraised, so the model
  can't reintroduce them.
- **A wrong finding on an unseen repository.** History lines are the riskiest
  (main's `docs/repository.md` now has "was retired on 2026-11-05" at lines
  4-5 and "A glob delete once killed a running eval" in a lessons list). The
  $0 scan at every head on the named repositories catches what it can; rules
  stay general so nothing is tuned to them; the held-out repository is
  sealed and the reviewer runs it. A wrong finding there fails the gate: no
  release, and the table goes to case-claudit.
- **Gate lines moved.** The two history lines the gate names
  (`docs/repository.md:42` and `:64` at `d825abd`) are at lines 44 and 74
  on `main` (`92989f8`). The gate reads them as those two sentences at
  their current lines on the pinned quickstop commit, and that commit is
  recorded with each run.
- **Medians over $0.15 or 60 s.** 4.3.1's default runs cost $0.13 to $0.18.
  The thin skill removes the docs fetch, the intent step and most reads, and
  the scan pre-words each problem and fix, so a run is the scan call plus
  the answer. The screen measures it before the full gate.
- **Grader errors.** Citation-anchored structure graders avoid phrasing
  matches; controls and mutation checks run in `bin/ci`; at most two
  hand-read corrections under the #168 quote rule, each shown beside its
  recorded value.
- **Spend and host state.** $15 cap at list price and the 70% shared-window
  pause, checked before every run; per-run caps; every paid run needs the
  lead's go. Runs set `DISABLE_AUTOUPDATER=1`, use throwaway clones and hash
  `~/.claude/settings.json` and `~/.claude/plugins/*.json` before and after.
  Local processes are stopped by exact PID.

## Proof

Local, at every head:

- `bin/ci` on Python 3.11.15 (unit tests for every kept and removed check,
  grader controls and mutation checks, plan validation, marketplace checks),
  `bin/check-marketplace --base origin/main` (5.0.0 above the advertised
  4.2.0), `bin/sdlc check`.
- `claude plugin validate .` and `claude plugin validate ./plugins/claudit`.
- The $0 scan of the three named real repositories, each finding read
  against its file.

Paid gate (Claude Sonnet as pinned by the runner; list price; $15 cap; no run
without the lead's go):

- Screen, n=1 per case: the 19 fixtures, and quickstop `main` (commit
  pinned), python-sdk `af4c6f4` and claude-code-action `c0949c50` through
  `bin/claudit-eval headless`. The reviewer runs the sealed held-out
  repository (issue comment 6759553072); I never see or run it. Estimated
  about $2.50.
- Full gate, n=3 per case on the reviewer-cleared tree: estimated about
  $7.50 for 57 fixture and 12 real-repository runs.
- Bars: every expected finding above hit in 3 of 3 runs; 0 false findings
  (`no-unraised-findings` and the clean-case graders) on f4, f15, f19 and
  every clean case; at most two hand-read corrections in total; on all four
  real repositories the headless script checks pass (real lines, no
  unraised finding, every scan finding accounted for), the reviewer judges 0
  findings wrong, and quickstop names the two history sentences above at
  their real lines; medians at or under $0.15 and 60 s per run. Each report
  is posted on #207 with its commit, cost and time; `CANDIDATE.txt` (tree,
  head, extraction write-tree, plugin tree) sits in every result directory.

Release checks:

- Plugin structure tests in `bin/ci`; `bin/sdlc audit` after merge (retried
  after a minute if GitHub hasn't linked the PR yet).
- Install from a local directory marketplace (never `file://`) in a script
  that sets `HOME` and `CLAUDE_CONFIG_DIR` to a fresh `mktemp -d`: add the
  marketplace, install `claudit`, check the inventory (one skill, no agent),
  the installed version 5.0.0 and the cached bytes against the plugin tree;
  then update from 4.2.0 and check the new cache, accepting the old cache's
  `.orphaned_at` marker. Graders read the full command output, never
  truncated. Real config hashes unchanged before and after.
- The reviewer tags `claudit-v5.0.0` (my pre-push hook refuses tags); I check
  the peeled commit and tree.

## Rollback

Before release: close the PR; nothing is advertised. After release: revert
the pointer PR so the marketplace advertises 4.2.0 again, and users reinstall
or `claude plugin update` (their 5.0.0 cache is left orphaned, not deleted).
The `claudit-v5.0.0` tag stays as history. Dismissal files keep working both
ways because the kept ids don't change. The retained #192 and #193 evidence is
deleted only after 5.0.0 is released and verified, so it's available until
then.
