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
need a compatibility reader. Keeping the shape means the existing Claudit
4.2.0 record and the Writing for Humans 1.0.0 record stay byte-identical and
keep validating as they are (both pin the catalog at their own commit, so
the 1.0.0 record still names the old path and still digests correctly).
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
  from `f03bee3a` only by that path; the quality-baselines document gets a
  line recording the new blob and that the diff is the path alone, so the
  1.0 gate record stays readable.
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
2. Archive tag first. Create the annotated tag
   `archive/shipshape-codex-2026-11-05` on `f4900063106e04f36e0360eb152c61941ef32f9b`
   (the main commit that still has `plugins/codex/shipshape`) and push that
   tag alone, before any commit removes the package. Confirm with
   `git ls-remote` and `git ls-tree -r <tag> plugins/codex/shipshape`. If the
   pre-push hook refuses a tag push, stop and tell the lead.
3. Validator narrowing with its tests (still passes on the current tree,
   since Shipshape's Codex entry goes in the same commit as its package).
4. Shipshape Codex package removal: package, catalog entry, acceptance doc,
   test, archive note, workflow sentences, retired generated outputs,
   regenerated catalog table.
5. Writing for Humans move and 1.0.1 bump, runner paths, test paths.
6. Docs sweep and the grep review.
7. `bin/ci`, `bin/check-marketplace --base origin/main`, `claude plugin
   validate` on both packages, candidate install (Proof, part 1). Simplify,
   mark the PR ready, request review from Batcomputer67, tell the lead.
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
- The quality runner's blob hash changes. Contained by the recorded new blob
  and the one-line diff note; 1.0.1's style and skill bytes are identical to
  1.0.0's, so the 1.0 quality gate still describes them (proved by comparing
  the package trees with the manifest excluded).
- A tag on the wrong commit would leave no named copy of the Shipshape Codex
  package. Contained by pushing the tag before any removal and checking its
  tree lists the full package.

## Proof

Before review, on the candidate head:

- `bin/ci` exits 0 on Python 3.11.15; `bin/check-marketplace --base
  origin/main` passes and confirms 1.0.1 is a higher version for changed
  bytes; `bin/sdlc check` conforms.
- New tests: a catalog with a `codex` target and one with a `pi` target are
  rejected with the clear message and no output written; retired files and
  directories are absent; the real `releases.json` (Claudit 4.2.0 and Writing
  for Humans 1.0.0) still validates through `bin/ci`'s marketplace check.
- `git diff --stat -M` shows the package as a rename with only
  `.claude-plugin/plugin.json` modified; the generated Claudit marketplace
  entry is unchanged; `git ls-tree -r archive/shipshape-codex-2026-11-05
  plugins/codex/shipshape` lists the full package (criterion 3).
- `claude plugin validate .` and `claude plugin validate
  ./plugins/writing-for-humans` pass.
- The issue's grep (`codex|pi package|\.agents/plugins|plugins/claude-code`,
  excluding `docs/archive/`) returns only the policy line, the archive note
  and justified hits, listed in the PR (criterion 2).
- Criterion 5 against the candidate: a script sets `HOME` and
  `CLAUDE_CONFIG_DIR` to a fresh `mktemp -d`, sets `DISABLE_AUTOUPDATER=1`,
  copies aside `~/.claude/plugins/*.json` and `~/.claude/settings.json` and
  hashes them before and after, restoring the copies. It adds a scratch
  local marketplace whose entries are Claudit's published entry and a
  git-subdir entry for writing-for-humans at the candidate commit, path
  `plugins/writing-for-humans`; installs both; checks 4.2.0 and 1.0.1 in
  `installed_plugins.json`, the installed digests, the style listed by
  `/output-style` and both skills plus Claudit's skill present in the
  installed packages.

After the tag and the pointer exist (criteria 4 to 7, same isolation script):

- Criterion 4: the published `.claude-plugin/marketplace.json` lists exactly
  claudit 4.2.0 (path `plugins/claudit`, sha `e3b1cd29…`) and
  writing-for-humans 1.0.1 (path `plugins/writing-for-humans`, the released
  sha); the tag `writing-for-humans-v1.0.1` resolves to that sha.
- Criterion 5 again from `acoz-labs/quickstop` itself.
- Criterion 6: add the marketplace as it stood at `f490006` (a git ref to
  that commit), install both, then point the marketplace at released `main`,
  update it and run `claude plugin update` for both. Writing for Humans ends
  at 1.0.1 with an install path from the new source, Claudit stays at 4.2.0,
  `claude plugin list` shows no error and no leftover 1.0.0 entry.
- Criterion 7: a scratch marketplace with a git-subdir source at
  `5581a159e10d523c68a514fec0237c46a44ac988`, path
  `plugins/claude-code/writing-for-humans`, installs 1.0.0 with its digest
  matching the 1.0.0 record.
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
