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
says, so #197's nine reviewed 4.3.0 and 4.3.1 commits sit under this plan commit. The
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
  Not checked: user and managed settings, settings validity, server-side branch protection.
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
  - A history finding's fix keeps the line's current fact and moves only the
    dated narrative out: "Keep `<current fact>`; move the dated detail
    (`<date or run>`) to a changelog or decision record." It never says to
    delete the sentence. Quickstop's `docs/repository.md:4` ("Shipshape ...
    was retired on 2026-11-05 and is kept for reference only") gets "keep
    that Shipshape is retired and kept for reference only; move the date".
    Unit tests pin this on a status-line fixture (the fix keeps "retired"
    and "kept for reference only" and names the date) and pin that a
    lessons-list line such as "A glob delete once killed a running eval" is
    not raised.
  - Declines stay only to suppress `stop-hook` and `allowlist`: a documented
    decision against hooks or pre-approved commands moves that finding to a
    `respected` list with the decision's `path:line` and reason. When a fact
    contradicts the decision's stated reason (today's `reconsider`: f10's
    "hooks can't block Claude from finishing", "there is no check command"
    while `CLAUDE.md` names one; and new, f12's allowlist replaced by project
    `bypassPermissions`, which Claude Code ignores in project settings), the
    finding stays, citing both the decision and the contradicting evidence.
    The `bypassPermissions` fact is the one settings-validity fact Claudit
    keeps, only as evidence against a decision; it cites its live docs page
    in the URL map, and the README's "not checked" list names this
    exception.
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
  script (regex) grader anchored on structure, not phrasing, and grades the
  fixtures the way `headless` grades real repositories:
  - `finding-*`: a numbered item that cites the expected `path:line` and
    whose fix holds the exact token (for example `Bash(bin/check-notes)`).
  - `finding-respected-<kind>`: the respected decision's line under "Not
    reported" (f8, f11, f13); `finding-scope-<n>`: each scope line after the
    footer rule (f17).
  - `no-invented-findings`, on every case: every numbered item starts with one
    of the scan's citations, each citation has as many items as the scan has
    findings there, and each item holds a token of its findings; so an
    invented item (a second one at an expected location included), an item
    with no `path:line` and a dropped item all fail. A total-count part was
    dropped in the code: the mutation check showed the per-citation counts
    and the allowed-citation part already imply it.
  - `no-invented-prose`, on every case: the report holds only the template's
    parts (title, count line, numbered items, "Not reported" bullets, the
    always-loaded table, the footer lines). Any other prose (advice under the
    table or in the footer, an extra section) fails.
  - `structure-summary` (the count line, "Nothing found." on clean cases) and
    `structure-footer` (version, commit, not-checked and `/doctor
    prompt-audit` lines) on every case.

  The names follow the runner's counting: `finding-*` graders are the hit
  rate and a failed `no-invented-*` grader is a false finding. The patterns
  live in `bin/claudit-eval`, so `headless` checks real repositories with the
  same definitions.
  The grade, intent, plan, declined and reconsider graders and all 15 llm
  graders go.
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
  - Respected decisions (no numbered finding, a "Respected" line, no hook
    recommended anywhere): f8 as it is (its `CLAUDE.md` must-rule for
    `bin/check`, its decision retiring hooks for the review checklist); f11,
    whose `CLAUDE.md` gains "Always run `bin/check` before you report a
    change as done", expecting its checklist reason quoted; f13, whose
    `CLAUDE.md` gains "Always run `npm test` before you report a change as
    done", expecting "no reason given".
  - f17: no numbered finding; the footer's scope lines (the scan already
    writes them) name the parent `CLAUDE.md` and `AGENTS.md`, say the parent
    `CLAUDE.md` keeps the repository's `AGENTS.md` from being read on its
    own, and name the symlink's real file.
  - Clean (0 findings, "Nothing found."): f4, f7, f9, f19, and the
    findings lists of f8, f11, f13 and f17.
  - Case descriptions (`case.yaml`) follow; prompts, budgets and fixtures are
    otherwise unchanged apart from the f11 and f13 lines.
- Grader builder and controls: `tests/claudit_graders.py` builds every
  grader from the scan of its scaffolded fixture (`--write`), and
  `tests/test_claudit_graders.py` holds the controls. Each case's correct
  report is rendered six ways (phrasings adapted from the 4.3.1 recorded
  reports under `~/factory/retained/quickstop-193/`: labelled lines, bold
  leads, an inline fix, an unindented fence body, wrapped lines, no Source)
  and must pass every grader. Failing controls change one thing each: a
  dropped item, a wrong line, a missing fix token, the item under "Not
  reported", the token only in a negated note, the same item twice, an
  invented second item at an expected location, an item with no citation,
  advice under "Always loaded" and in the footer, a wrong count, a missing
  footer, respected or scope line. All run in Python and node, plus a
  mutation check of each `no-invented-findings` part and each token. As the
  graders are structural, a hypothetical sentence inside a correctly cited
  item still passes; that wording is the reviewer's to judge. Graders and
  controls are frozen before the screen (see Proof).
- Runner (`bin/claudit-eval`): the `claudit-deep` arm and `--deep` plumbing
  go, and the two-docs-path (`--web-fetch`) requirement for Claudit goes,
  since Claudit no longer fetches docs. With no llm graders left, the
  runner's own judge (the `judge` subcommand and the llm branch for the
  doctor-combined arm) goes too, and so do the #193 `gate` graders.
  `headless` script-checks a real-repo report against the scan of the same
  clone: every line the scan cites exists in the clone, every numbered item
  starts with a citation that is one of the scan's findings, every scan
  finding is reported or dropped under "Not reported" with a reason citing
  the repository, and the respected, count and footer lines and the template
  hold. Whether the cited line says what the item claims is the reviewer's
  read. `summarize --expect-runs` (and every full-suite `run`) refuses a
  result that isn't the whole suite (cases, grader names, run counts), so a
  partial run can't read as PASS; the summary gives median cost and time.
- Old suite tests: `tests/test_claudit_plan.py` becomes
  `tests/test_claudit_decisions.py`; it, `tests/test_claudit_43.py`,
  `tests/test_claudit.py` and `tests/test_claudit_eval.py` are rewritten to
  the new output; `tests/test_claudit_fixture_graders.py`,
  `tests/test_claudit_case_graders.py`, `tests/test_claudit_eval_graders.py`,
  `tests/test_claudit_gate_graders.py`, `tests/claudit_render.py` and the
  4.0.1 reports in `tests/claudit_gate_reports/` are removed. No test of a
  kept check is weakened.
- Package structure test (`tests/test_claudit.py`, new): the package holds
  one skill and no agent or catalog, the manifest and changelog carry the
  scan's version, and the skill allows only the scan and dismiss calls.
- Scan fixes found by the $0 real-repository scan (step 3), each with a unit
  test: a test runner keeps its wrapper (`uv run --frozen pytest`, not
  `pytest`), the allow-rule finding cites the line that names the command
  (code blocks included), and text shared only by subagent, skill or command
  prompts, which each load in their own context, is not a duplicate.

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
5. Eval: graders and controls, the f11 and f13 fixture lines, runner
   changes, eval and acceptance docs. `bin/ci` and `bin/check-marketplace --base origin/main`.
6. Simplify pass over the whole diff; open the PR for review.
7. After review clears the tree for the screen and the lead gives a go:
   screen at n=1 (19 fixtures and the three named repositories; the reviewer
   runs the held-out one). Then the spend projection (Proof); stop and
   report if it doesn't fit. Fix, re-review and re-screen if the screen
   fails, within the four code rounds.
8. On the screened tree, cleared by the reviewer, and the lead's go: the
   full n=3 gate. Results posted on #207, not committed.
9. Clean-install check from a local directory marketplace; then the reviewer
   merges, tags and the pointer PR follows.
10. Release check from the published GitHub marketplace after the pointer PR
    merges (Proof).
11. Cleanup, triggered by a passing step 10 and done on the lead's go:
    delete `~/factory/retained/quickstop-192/`,
    `~/factory/retained/quickstop-193/` and the #193 clones
    `~/factory/quickstop-193/implementer/` and
    `~/factory/quickstop-193/reviewer/` by those exact paths, after checking
    no process uses them. A failed gate keeps them.

## Risks

- **Breaking output for current users.** Anyone reading grades or the plan
  loses them. Contained by the major version, the changelog entry and the
  README's upgrading note; 4.2.0 stays installable from its tag.
- **Dropping config checks hides real defects** (invalid JSON, array
  matchers, ignored `bypassPermissions`). The footer says settings validity
  isn't checked; it names `/doctor` for it only if the build-time docs check
  finds a page saying `/doctor` reports settings errors, and then cites that
  page. The unparseable-settings guard stops false findings; f3's dropped defects are graded as unraised, so the model
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

- Caps: `claude plugin eval`'s `--max-cost-usd` is a ceiling for the whole
  invocation, checked before each run starts, not a per-case cap. Fixture
  invocations get 19 cases times $0.40 per case per run ($7.60 at n=1,
  $22.80 at n=3), or, if lower, what is left of the $15 cap after the
  projected real-repository runs; the spend rule below keeps the total
  under $15. Real-repository runs through `bin/claudit-eval headless` get
  `--max-budget-usd 0.40` per run.
- Screen, n=1 per case: the 19 fixtures, and quickstop `main` (commit
  pinned), python-sdk `af4c6f4` and claude-code-action `c0949c50` through
  `bin/claudit-eval headless`. The reviewer runs the sealed held-out
  repository (issue comment 6759553072); I never see or run it. 23 runs; at
  the $0.15 bar about $3.50.
- Spend rule, from the screen's measured costs: the gate projects to 57
  times the median fixture run plus 12 times the median real-repository
  run (all four repositories, the held-out one included); a re-screen
  projects to the screen's own total. Before the gate, and before any
  re-screen, if spend so far plus that step plus (for a re-screen) the
  projected gate would pass $15, stop and report to the lead with the
  numbers. At the $0.15 bar the screen is about $3.45 and the gate about
  $10.35, $13.80 together, so a re-screen fits only if the measured runs
  are cheaper than the bar (about $0.12 or less).
- Freeze: graders, controls and fixtures are frozen at the screened tree.
  Recorded reports may be regraded at $0. Any later change to the tree,
  under `evals/` or anywhere else, triggers a re-screen of the new tree
  before the gate, budgeted by the spend rule; a screen never stands for a
  tree it didn't run on.
- Full gate, n=3 per case on the screened, reviewer-cleared tree: 57 fixture
  and 12 real-repository runs.
- Bars: every expected finding above hit in 3 of 3 runs, with f17's
  scope-line graders and the f8, f11 and f13 Respected-line graders counting
  as those cases' planted items; 0 false findings
  (`no-invented-findings` and `no-invented-prose`) on f4, f15, f19 and
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
- Release verification, after the pointer PR merges: install from the
  published GitHub marketplace (`acoz-labs/quickstop`) in the same fresh
  `HOME` and `CLAUDE_CONFIG_DIR` script; check version 5.0.0, the inventory,
  the cached bytes against the tagged plugin tree, and real config hashes
  unchanged before and after.

## Rollback

Before release: close the PR; nothing is advertised. After release: revert
the pointer PR so the marketplace advertises 4.2.0 again, and users reinstall
or `claude plugin update` (their 5.0.0 cache is left orphaned, not deleted).
The `claudit-v5.0.0` tag stays as history. Dismissal files keep working both
ways because the kept ids don't change. The retained #192 and #193 evidence is
deleted only after 5.0.0 is released and verified, so it's available until
then.
