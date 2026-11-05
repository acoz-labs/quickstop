# Plan: Claude Code-only Quickstop with a flat plugins/<name> layout

## Issue

Refs https://github.com/acoz-labs/quickstop/issues/202

Quickstop becomes a Claude Code-only marketplace with every plugin at
`plugins/<name>/`: Codex and Pi support go, Shipshape's never-released Codex
package is archived under a tag and removed, and Writing for Humans moves to
`plugins/writing-for-humans` as release 1.0.1. Claudit stays byte-for-byte
at 4.2.0.

## Schema decision

`catalog.json` and `releases.json` keep their current shape: plugins keep a
`targets` map and release records keep `harness`. The only allowed harness is
`claude-code` and the only format is `claude-plugin`.

Flattening would be a bigger change, not a smaller one. The release-history
check keys every published commit, version and digest by `(name, harness)`,
and it reads the catalog at each released commit, so historical locks would
need a compatibility reader. Keeping the shape means both existing records
keep validating as they are: each pins the catalog and package at its own
commit, so the 1.0.0 record still names the old path and still digests
correctly. No lock in history holds a `codex` or `pi` record, so the history
check is unaffected by the narrowing.

Which PR touches which record:

- Plugin PR: `releases.json` does not change; the Claudit 4.2.0 and Writing
  for Humans 1.0.0 records stay byte-identical.
- Pointer PR: the Claudit record stays byte-identical. The Writing for Humans
  1.0.0 record is replaced by the 1.0.1 record, because the lock holds one
  record per name and harness and `promote` swaps it
  (`bin/marketplace-release`). The 1.0.0 record remains in history, which is
  what rollback restores.

`bin/marketplace-release promote` keeps its `--harness` flag.

## Files that change

This PR (the plugin PR, `Refs #202`):

- Marketplace validator (`bin/check-marketplace`): the format table holds
  only `claude-code`/`claude-plugin`. A `codex`, `pi` or any other target
  fails with `<plugin>: unsupported target '<harness>'; Quickstop supports
  only claude-code`, and a wrong format under `claude-code` keeps its own
  message. Remove the Codex projection, the Pi projection and Pi resource
  checks, the `.codex-plugin` overlay, the OpenAI extension and Codex
  `interface`/`apps` resource checks, and the root-`plugin.json`/`package.json`
  manifest detection. Generated outputs shrink to `.claude-plugin/marketplace.json`
  and `docs/catalog.md`; the catalog table drops the Codex and Pi columns.
  The undeclared-manifest check stays for `.claude-plugin/plugin.json`. The
  base comparison and the legacy Claude-only migration path are unchanged.
- Release helper (`bin/marketplace-release`): no logic change expected; it
  already derives formats and outputs from the validator. Docstring or help
  text only if they name other tools.
- Removed: `.agents/plugins/marketplace.json`, `docs/pi-packages.md`,
  `plugins/codex/shipshape/` (whole package), Shipshape's `catalog.json`
  entry, `docs/acceptance/shipshape.md`, `tests/test_shipshape.py`.
- Moved with `git mv`: `plugins/claude-code/writing-for-humans` to
  `plugins/writing-for-humans`. In its manifest, `version` becomes `1.0.1`
  and `homepage` points at the new path; nothing else in the package
  changes. The catalog target path follows.
- Regenerated: `docs/catalog.md` (Shipshape row and Codex/Pi columns gone;
  Writing for Humans still shows 1.0.0 because the lock still advertises
  it). `.claude-plugin/marketplace.json` does not change in this PR.
- Eval runners: the default plugin path and `--plugin` help text in
  `bin/writing-for-humans-eval` and `bin/writing-for-humans-quality-eval`.
  The frozen suite directory is untouched. The quality runner's blob changes
  from `f03bee3a` only by that path. The quality-baselines document gets a
  note saying so, with the new blob, and what follows from it: the runner
  at the new blob refuses the retained 1.0 results and the 1.0 calibration,
  which are tied to `f03bee3a`. The 1.0 record stays readable as written;
  re-summarizing it needs a checkout at the old blob, and the next counted
  quality run needs a fresh calibration.
- Tests:
  - `tests/test_marketplace.py`: delete the Codex-only, Pi-only, shared
    two-tool package, portable-schema, overlay and Codex resource-type
    cases; rewrite the cases that used Codex only as a second package
    (independent versions, unregistered or undeclared manifest) with two
    Claude plugins; add rejection tests for `codex` and `pi` targets that
    check the message and that nothing is written; add a test that the
    retired outputs and `plugins/codex`, `plugins/claude-code` are absent
    from the repository.
  - `tests/test_marketplace_release.py`: delete the Codex-pin and Pi-command
    case; the rest stay.
  - `tests/test_writing_kit.py` and `tests/test_writing_for_humans_eval.py`:
    new package path; the existing "no Codex copy" assertion widens to the
    two retired directories.
- Archive note: `docs/archive/shipshape-codex.md` names the tag
  `archive/shipshape-codex-2026-11-05` and its commit `f490006`, and says why
  (never released; acceptance was blocked because no Codex host was
  available), in the style of the existing cross-platform archive note.
- Shipshape workflow (`workflows/shipshape/README.md`, `adapt.md`,
  `examples.md`, `process.md`): remove only the sentences about the optional
  Codex package. The starter prompt is unchanged, so the storefront receipt
  is unaffected; the PR records that determination.
- Docs that describe more than one tool: `README.md` (drop the Codex and Pi
  install sections and the multi-tool framing; Writing for Humans link),
  `docs/marketplace.md` (one adapter, the Pi section and "Add a harness"
  replaced, "Package layouts" becomes `plugins/<name>/` with the Claudit
  exception gone, and the single policy line: *another agent tool is added
  only once its plugins can be tested in that tool*), `docs/plugin-development.md`,
  `docs/delivery.md` (Claude-only install wording; promote command keeps
  `--harness claude-code`), `docs/repository.md` (layout and tracking list),
  `docs/workflows.md`, `docs/acceptance/writing-for-humans.md` (its last
  sentence about other harnesses), `docs/investigation.md` (its present-tense
  description of multi-tool support). Each remaining grep hit is listed and
  justified in the PR.

Left alone on purpose: everything under `plugins/claudit/`, `evals/`, the
Claudit tests (their Codex mentions are grader fixtures about AGENTS.md),
recorded eval reports, PR #197 and every downstream repository.

The later pointer PR (also mine, `Refs #202`, after acceptance and the
release tag):

- `releases.json`: the writing-for-humans 1.0.1 record built exactly as
  `promote` builds it (merged commit, package digest, catalog target and
  manifest snapshot from that commit, `sdlc-accepted` provenance with the
  reviewer's acceptance receipt). Claudit's record is untouched.
- `catalog.json`: the marketplace description loses "unified marketplace
  for agentic plugins" (catalog description changes belong in the pointer
  PR, not the plugin PR).
- Regenerated `.claude-plugin/marketplace.json` (1.0.1, path
  `plugins/writing-for-humans`, the released sha, new description) and
  `docs/catalog.md`.

## Order of work

1. Plan PR: this file alone, draft PR, plan review. No code until the plan
   review has nothing above low.
2. Archive tag first. The reviewer (Batcomputer67) creates the annotated
   tag `archive/shipshape-codex-2026-11-05` on
   `f4900063106e04f36e0360eb152c61941ef32f9b` (the main commit that still has
   `plugins/codex/shipshape`) and pushes it, before any commit removes the
   package; the implementer's pre-push hook refuses tag pushes. I then
   confirm it by tree hash: `git ls-remote origin
   'refs/tags/archive/shipshape-codex-2026-11-05*'` shows the peeled `^{}`
   line at `f4900063106e04f36e0360eb152c61941ef32f9b`, and `git rev-parse
   <tag>^{}:plugins/codex/shipshape` equals `git rev-parse
   f490006:plugins/codex/shipshape`, whose `ls-tree -r` lists 10 files.
3. Shipshape Codex package removal: package, catalog entry, acceptance doc,
   test, archive note, workflow sentences, regenerated catalog table. The
   current validator still passes once the Codex entry is gone; the Codex
   index was already empty.
4. Validator narrowing with its tests, removal of the retired generated
   outputs, regenerated catalog table. This comes after step 3 because the
   narrowed validator rejects Shipshape's `codex` target.
5. Writing for Humans move and 1.0.1 bump, runner paths, test paths, the
   quality-baselines note.
6. Docs sweep and the grep review.
7. `bin/ci`, `bin/check-marketplace --base origin/main`, `claude plugin
   validate` on both packages, the regression suite and candidate install
   checks (Proof, before review). Simplify, mark the PR ready, request
   review from Batcomputer67, tell the lead.
8. After merge (rebase merge only), the reviewer accepts the merged commit
   and tags `writing-for-humans-v1.0.1`. I then open the pointer PR, with the
   records written by `promote`'s logic; the reviewer confirms by running
   `promote` on its head ("Already points at this accepted artifact", no
   diff).
9. After the pointer merges: criteria 5 to 7 on the published marketplace,
   transcripts posted on the issue.

## Risks

- Existing installs follow a path change. Writing for Humans 1.0.0 users have
  a git-subdir source at the old path; 1.0.1 moves it. Contained by: the old
  commit and path stay in history, the 1.0.0 lock record stays valid, and
  criteria 6 (upgrade from the `f490006` marketplace) and 7 (old pin still
  installs) are run before the job closes.
- Between the plugin PR merging and the pointer PR merging, the marketplace
  still advertises 1.0.0 at the old path. That is the intended state: the
  release lock is the only thing that advertises.
- Claudit could be disturbed by the validator change. Contained by: its
  catalog entry, release record and package are untouched; the validator
  re-checks the 4.2.0 record's digest, manifest and provenance in `bin/ci`;
  the generated Claudit marketplace entry must stay byte-identical (checked in
  the diff).
- Narrowing removes checks a future tool would need. Accepted: the policy
  line says a new tool needs testable plugins first, and the archive tag plus
  git history keep the old adapters recoverable.
- The quality runner's blob hash changes, so it refuses the retained 1.0
  results and calibration. Contained by the baselines note (new blob, the
  path-only diff, re-summarizing 1.0 needs the old blob, the next counted run
  needs a fresh calibration). 1.0.1's style and skill bytes are identical to
  1.0.0's, so the 1.0 quality gate still describes them (proved by comparing
  the package trees with the manifest excluded).
- A tag on the wrong commit would leave no named copy of the Shipshape Codex
  package. Contained by pushing the tag before any removal and checking its
  tree lists the full package.

## Proof

### Isolation for every install check

Each install check runs from a script that sets `HOME` and
`CLAUDE_CONFIG_DIR` to a fresh `mktemp -d` directory and sets
`DISABLE_AUTOUPDATER=1` on every `claude` call. Before the run it hashes
`~/.claude/settings.json` and `~/.claude/plugins/*.json` and copies them to
the run's evidence directory; it does not hash `~/.claude.json`. After the
run it hashes them again:

- Hashes match: nothing is restored; the run left real config alone.
- Hashes differ: the script stops without restoring. I diff the copies
  against the live files, restore only entries the run itself wrote (if
  any), leave changes made by other live sessions in place, and report the
  diff and what was restored.

The scratch directories are deleted by exact path at the end.

### Before review, on the candidate head

- `bin/ci` exits 0 on Python 3.11.15; `bin/check-marketplace --base
  origin/main` passes and confirms 1.0.1 is a higher version for changed
  bytes; `bin/sdlc check` conforms.
- New tests: a catalog with a `codex` target and one with a `pi` target are
  rejected with the clear message and no output written; retired files and
  directories are absent; the real `releases.json` (Claudit 4.2.0 and Writing
  for Humans 1.0.0) still validates through `bin/ci`'s marketplace check.
- `git diff --stat -M` shows the package as a rename with only
  `.claude-plugin/plugin.json` modified; the package tree with the manifest
  excluded matches 1.0.0's; the generated Claudit marketplace entry is
  unchanged.
- Archive tag (criterion 3): the tree-hash checks in step 2 of the order of
  work, repeated against the remote.
- `claude plugin validate .` and `claude plugin validate
  ./plugins/writing-for-humans` pass.
- The issue's grep (`codex|pi package|\.agents/plugins|plugins/claude-code`,
  excluding `docs/archive/`) returns only the policy line, the archive note
  and justified hits, listed in the PR (criterion 2).
- The #172 regression suite (`bin/writing-for-humans-eval`) runs once on the
  candidate package at its new path, with `--model claude-sonnet-5-5` (the
  1.0.0 run's model) and `--max-cost-usd 1` (the 1.0.0 run cost $0.20). It runs because it covers exactly what a path move can break:
  install from a marketplace, style selection and the user-only audit
  contract. The quality gate does not run again: 1.0.1's style and skill
  bytes equal 1.0.0's.

### Acceptance for 1.0.1, scaled to a path-only patch

The catalog's procedure for Writing for Humans
(`docs/acceptance/writing-for-humans.md`, "Bounded follow-up releases" and
the 0.3.0 list) applies. For a release whose only change is the package
path, these are the checks a move could break, and each runs:

- In the temporary config, which isn't logged in, so model-free:
  - Install both plugins and record `installed_plugins.json` (version,
    install path, commit) and the installed package digests.
  - The $0 `/output-style` preflight after selecting
    `writing-for-humans:writing-for-humans` shows it as "(current)" in a
    fresh session, with a negative control (a nonexistent style name is not
    shown as current).
  - The init event of a `claude -p` call lists the skills and slash commands
    of both plugins: `writing-for-humans:writing-style`,
    `writing-for-humans:writing-audit` and Claudit's skill.
  - Every `${CLAUDE_SKILL_DIR}` and `${CLAUDE_PLUGIN_ROOT}` path in both
    Writing for Humans skills, expanded against the install path, names a
    readable file.
  - Select another style, disable and uninstall Writing for Humans, and show
    that a fresh session has no plugin style or skills and that an unrelated
    setting placed beforehand is unchanged.
- On the normal login, from a throwaway worktree of this clone, one model
  turn: `claude -p` with `--plugin-dir` set to the installed 1.0.1 bytes,
  `--setting-sources project,local` and `--strict-mcp-config`, asking for a
  task that makes the `writing-style` skill read a package-local reference.
  The trace must show the Read of that reference resolving under the new
  install path. Capped with `--max-budget-usd 0.5`, with
  `DISABLE_AUTOUPDATER=1` and the same before/after hashes of the real
  config files, and run before the temporary install directory is deleted.
- Recovery to the previous version is criterion 7 below.

Criterion 5 before review uses the same steps against the candidate,
through a local directory marketplace. Claude Code 2.1.318 refuses a
`file://` marketplace source ("Invalid marketplace source format"), so the
planned `file://` mirror was replaced: a scratch clone of the pushed
candidate commit gets one local commit changing only
`.claude-plugin/marketplace.json`, so its Claudit entry stays the published
one and its writing-for-humans entry is 1.0.1 as a git-subdir source at the
candidate commit, path `plugins/writing-for-humans`. That clone is added by
path; its marketplace name is `quickstop`. The plugins' sources fetch from
GitHub, and the scratch commit is never pushed.

### After the tag and the pointer exist

- Criterion 4: the published `.claude-plugin/marketplace.json` lists exactly
  claudit 4.2.0 (path `plugins/claudit`, sha `e3b1cd29…`) and
  writing-for-humans 1.0.1 (path `plugins/writing-for-humans`, the released
  sha); the tag `writing-for-humans-v1.0.1` resolves to that sha.
- Criterion 5 again, from `acoz-labs/quickstop` itself, with the model-free
  checks above.
- Criterion 6, the real user's update path. `claude plugin marketplace add
  acoz-labs/quickstop` makes a shallow git clone of `main` under the config's
  `plugins/marketplaces/quickstop`, and `marketplace update` pulls it. (The
  planned `file://` mirror is refused by Claude Code.) In a fresh temporary
  config: add `acoz-labs/quickstop`; in that clone, `git fetch --depth 1
  origin f4900063106e04f36e0360eb152c61941ef32f9b` and `git reset --hard` to
  it. Before installing, check that the clone's HEAD is `f490006` and that
  the marketplace lists writing-for-humans 1.0.0 at
  `plugins/claude-code/writing-for-humans`. Install both plugins and record
  `installed_plugins.json` and the plugin cache listing. Then, under the same
  marketplace name, run `claude plugin marketplace update quickstop` and
  `claude plugin update` for each plugin. The marketplace is never removed or
  re-added, since removal can uninstall its plugins. If `marketplace update`
  refuses or doesn't move the clone to released `main`, stop and report
  rather than switching mechanism. Pass: the clone is at released `main`,
  Writing for Humans ends at 1.0.1 with an install path and commit from the
  new source, Claudit stays at 4.2.0 with the same commit, `claude plugin
  list` shows no error, and the init event still lists Claudit's skill and
  both Writing for Humans skills. Record `installed_plugins.json` and the
  cache listing again and show the 1.0.0 cache entry is gone, or explain why
  it remains (for example, if Claude Code keeps old versions by design).
- Criterion 7: a scratch marketplace with a git-subdir source at
  `5581a159e10d523c68a514fec0237c46a44ac988`, path
  `plugins/claude-code/writing-for-humans`, installs 1.0.0 with its digest
  matching the 1.0.0 record. This is also the recovery check for 1.0.1.
- Transcripts of commands and outputs go on the issue, compared with the
  1.0.0 baseline in the retained release evidence for #189.

The independent verifier reruns `bin/ci` in a clean full-history checkout at
the merged commit, confirms the archive tag's tree, runs `promote` on the
pointer head, and repeats the install checks from the published marketplace.

## Rollback

- Plugin PR: revert it. The package returns to the old path and Codex/Pi
  support returns; nothing is advertised differently because the lock was not
  touched.
- Pointer PR: revert it to advertise 1.0.0 at `5581a159`, the recovery record.
  Users who already updated keep 1.0.1 until they reinstall; 1.0.1's
  behaviour is identical, so that is harmless.
- Neither tag is removed on rollback. The archive tag is the only copy of
  the Shipshape Codex package outside history and stays permanently; the
  1.0.1 tag and release are immutable, and a fix would be 1.0.2.
