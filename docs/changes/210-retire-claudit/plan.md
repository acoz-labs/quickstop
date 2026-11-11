# Plan: retire Claudit with a last release, 4.4.0

## Issue

Refs https://github.com/acoz-labs/quickstop/issues/210

Claudit's last release, 4.4.0, runs no audit: its skill and README tell the
user Claudit is retired, to run `/doctor`, then `/doctor prompt-audit`, and
link https://acoz.dev/blog/retiring-claudit/. The marketplace keeps listing
Claudit, marked retired the way Shipshape was, so existing installs update to
the notice instead of silently keeping 4.2.0.

## Version

4.4.0. The repository's rule is that changed package bytes need a strictly
higher stable `X.Y.Z` than the advertised 4.2.0 (`bin/check-marketplace
--base`), and the brief rules out 5.0.0, which belongs to the abandoned thin
checker in #207 and PR #208.

- Not 4.2.1: removing the audit is a behaviour change, not a fix, so a patch
  number would misdescribe it.
- Not 4.3.0 or 4.3.1: no tag or release has those numbers (the published tags
  stop at `claudit-v4.2.0`), but both were public candidate versions in closed
  PR #197 and in the eval results posted on its issues. Reusing either for
  different bytes would make those records ambiguous. 4.4.0 is the next minor
  number nobody has used.

## How Shipshape's retirement maps onto a plugin

Shipshape was a guide, not a plugin, and had no catalog entry by the time it
was retired (PR #206), so there is no `retired` catalog field to copy, and
the catalog schema refuses unknown fields. Its retirement was text: each
place that presented it says "Retired on 2026-11-05 and kept for reference
only" and links the retirement note. Claudit gets the same treatment in every
place that presents it, with the catalog description as the marketplace
metadata:

- Catalog description (`catalog.json`), which `bin/check-marketplace --write`
  copies into the native index (`.claude-plugin/marketplace.json`) and the
  version table (`docs/catalog.md`). Proposed text: "Retired on 2026-11-11.
  Run /doctor, then /doctor prompt-audit, instead. This last version runs no
  audit; it only says so and links the retirement post." The repository rule
  puts catalog description changes in the pointer PR, because promote
  regenerates the indexes from the head's catalog.
- Package manifest description (`plugins/claudit/.claude-plugin/plugin.json`):
  the same sentence, in the plugin PR because it is package bytes.
- The repository README's Plugins section and the repository guide's opening
  paragraph (`docs/repository.md`): "Claudit was retired on 2026-11-11", with
  the `/doctor` pointers and the post link, as #206 did for Shipshape.
- The package README opens with the same `> **Retired.**` note Shipshape's
  pages open with.

The listing keeps Claudit's name and category. Its keywords drop "audit",
"optimization" and "grading", which describe what it no longer does, and add
"retired"; "configuration" and "best-practices" stay. Keywords are manifest
bytes, so this is in the plugin PR.

## Files that change

### Plugin PR (this PR)

Package (`plugins/claudit/`), all bytes, so all covered by the version bump:

- Skill instructions (`skills/claudit/SKILL.md`): replaced. The frontmatter
  keeps `name: claudit`; the description says Claudit is retired and to use
  it when the user runs or asks for Claudit; `allowed-tools`, `model` and
  `argument-hint` are removed. The body tells Claude to reply with the fixed
  retirement message and nothing else, to ignore any arguments, and not to
  read files, run commands or audit anything. The message: Claudit is
  retired; run `/doctor`, then `/doctor prompt-audit`; why, at
  https://acoz.dev/blog/retiring-claudit/; how to uninstall
  (`/plugin uninstall claudit@quickstop`).
- Package README (`README.md`): replaced by a short page that opens with a
  `> **Retired.** Claudit was retired on 2026-11-11 …` note, as Shipshape's
  pages do (PR #206), then gives the same message, the uninstall command, and where the last auditing version lives
  (tag `claudit-v4.2.0`).
- Manifest (`.claude-plugin/plugin.json`): version 4.4.0, the retired
  description and the trimmed keywords above.
- Removed, because they only exist to audit: the auditor agent
  (`agents/auditor.md`), the scan helper (`skills/claudit/scripts/claudit.py`),
  the shipped docs catalog (`skills/claudit/catalog.json`) and the apply
  reference (`skills/claudit/references/apply.md`). Keeping the agent would
  leave a model-invocable auditor in the package, which breaks "performs no
  audit". `LICENSE` stays.

Repository tooling that exercises the removed helper:

- Removed: the Claudit eval runner (`bin/claudit-eval`), its suite
  (`evals/claudit/`), the Claudit tests (`tests/test_claudit*.py`, about 5,300
  lines) and their recorded gate reports (`tests/claudit_gate_reports/`), and
  the `.gitignore` lines for its results. All of them load
  `plugins/claudit/skills/claudit/scripts/claudit.py` or grade its audit
  reports, so they can't run once the helper is gone. They test removed
  code; no test of remaining code is weakened. They stay readable in
  history at this PR's base commit, which is newer than tag
  `claudit-v4.2.0` (it has the later `doctor-combined` arm).
- Kept as historical records, unchanged: the eval baselines
  (`docs/acceptance/claudit-eval-baselines.md` and its folder), the
  investigation notes and earlier change folders. The baselines page gets a
  one-line note at the top saying Claudit was retired in 4.4.0 and its eval
  tooling removed, with the tag where it lives. Its two relative links into
  the removed suite README become GitHub links to that README pinned at
  this PR's base commit, so no link in the repository breaks; command
  names in the recorded text stay as they were run.
- Claudit's acceptance procedure (`docs/acceptance/claudit.md`): replaced by
  the 4.4.0 scenarios in Proof below, with a line saying the 4.2.0 procedure
  is at tag `claudit-v4.2.0`.
- The repository guide (`docs/repository.md`): the layout lines that name
  `bin/claudit-eval` and the plugin-eval git note that cites it are updated to
  match. Lessons that stay true for other plugin evals stay. The Claudit
  retirement note itself goes in the pointer PR.

No file of Writing for Humans, no other plugin's version, and no
`releases.json` record changes in this PR.

### Pointer PR (after acceptance and the `claudit-v4.4.0` tag)

- Release lock (`releases.json`): the Claudit record is replaced by the 4.4.0
  record (commit, package digest, manifest snapshot, provenance with the
  acceptance comment), written with promote's logic. The Writing for Humans
  record stays byte-identical.
- Catalog (`catalog.json`): Claudit's retired description.
- Regenerated indexes (`bin/check-marketplace --write`): the native index and
  version table show 4.4.0, the retired description and the new commit pin.
- The repository README and repository guide notes described above. In the
  README's Plugins section, the sentence "For Claudit, use `/plugin install
  claudit@quickstop`" is dropped and the local-development example switches
  from `plugins/claudit` to `plugins/writing-for-humans`, so the README no
  longer offers to install a retired plugin.

The reviewer confirms the lock by running promote on the pointer head as the
maintainer account and seeing "Already points at this accepted artifact" with
no diff.

## Order of work

1. This plan alone, draft PR, plan review.
2. Package: new skill, README and manifest; remove the agent, helper,
   catalog and apply reference. `bin/check-marketplace --base origin/main`
   passes with 4.4.0.
3. Remove the Claudit eval tooling and tests in the same commit as the helper
   (step 2 and 3 land together so `bin/ci` passes at every commit), then
   update the acceptance procedure, baselines note and repository guide
   lines.
4. Run `bin/ci`, `bin/check-marketplace --base origin/main`, `bin/sdlc check`,
   `claude plugin validate .` and `claude plugin validate ./plugins/claudit`;
   run the candidate checks in Proof; mark the PR ready and request review.
5. After merge: the reviewer retains the archive, runs acceptance, gates and
   tags `claudit-v4.4.0`; I check the peeled commit and tree.
6. Gate before publishing: the post URL returns HTTP 200, recorded with the
   time. The GitHub Release is not created and the pointer PR is not merged
   until it does (or the factory says so).
7. Pointer PR from the latest `main`: lock record via promote's logic,
   catalog description, regenerated indexes, README and repository guide
   notes; `bin/ci` and `bin/check-marketplace --base origin/main`.
8. The reviewer verifies the published release with the published-artifact
   checks in Proof and closes #210.

The lead closes #207 and #208 after the release verifies; this work doesn't
touch them.

## Risks

- **The model audits anyway.** A skill is instructions, not code; with the
  auditor agent and helper gone and no pre-approved tools, Claude has nothing
  to audit with, and the body forbids tools and file reads. Proof checks the
  real run's tool calls, not just its text.
- **Model invocation.** Claude may invoke the skill when a user asks for an
  audit without naming Claudit. That only shows the notice pointing to
  `/doctor`, which is the outcome we want; the description says to use it for
  Claudit requests so unrelated requests don't trigger it.
- **`/doctor prompt-audit` must exist** in the Claude Code version users run.
  The owner's post names it; acceptance records the Claude Code version and
  runs `/doctor prompt-audit` once to confirm it's recognised.
- **The post link 404s.** It returns 200 today; step 6 makes a 200 a gate
  before the GitHub Release and the pointer merge.
- **Removing 5,300 lines of tests** could read as weakening the suite. They
  only test the removed helper and graders for its reports; the PR lists them
  and shows the unittest count drops by exactly their test count, with
  everything else still passing.
- **Old cache on disk.** After `/plugin update`, the 4.2.0 cache stays with
  `.orphaned_at`; that is expected and acceptance records it rather than
  treating it as a failure.
- **Other plugins.** A diff check shows nothing under
  `plugins/writing-for-humans/` changes and its lock record is byte-identical
  in both PRs.

## Proof

Repository checks at the candidate head: `bin/ci` (pinned Python 3.11.15),
`bin/check-marketplace --base origin/main` (4.4.0 is higher than 4.2.0),
`bin/sdlc check`, `claude plugin validate .` and
`claude plugin validate ./plugins/claudit`. A `git diff --name-only` check
that no path outside `plugins/claudit/`, the removed Claudit tooling and the
named docs changes.

Candidate install and run checks, from a script that sets `HOME` and
`CLAUDE_CONFIG_DIR` to fresh temporary directories for the install and
inventory checks, and from a throwaway worktree on the normal login with
`--plugin-dir`, `--setting-sources project,local` and
`--strict-mcp-config` for the model-turn checks, with
`DISABLE_AUTOUPDATER=1`:

1. Install from a local directory marketplace holding the candidate (Claude
   Code refuses `file://` marketplaces): 4.4.0 installs, the inventory shows
   one skill (`claudit`) and no agents.
2. Run three prompts headless with stream-json output, in a synthetic
   repository: `/claudit:claudit`, `/claudit:claudit --read-only hooks` and
   the plain "audit my Claude Code setup with Claudit". Graders read the
   whole output, never a truncated excerpt, and pass a run only when:
   - the final reply contains "retired", `/doctor`, `/doctor prompt-audit`
     and the post URL;
   - the init event lists the `claudit` skill and no `auditor` agent;
   - the two slash-command runs make zero tool calls, and the plain-language
     run makes exactly one, a Skill call for `claudit`; no run calls Read,
     Grep, Glob, Bash, WebFetch, Agent, Task or any other tool.
   Negative control: the plain-language prompt run without the plugin must
   not produce the post URL, so the grader tells the skill's reply from a
   guess.
3. Consumer state: the synthetic repository's files, Git index and working
   tree are unchanged; no `~/.cache/claudit` or `CLAUDIT_CACHE_DIR`
   directory is created; `~/.claude/settings.json` and
   `~/.claude/plugins/*.json` in the temporary home are hashed before and
   after.
4. Update path: install 4.2.0 from a local marketplace at the 4.2.0 commit,
   switch the marketplace to the candidate, update, and see 4.4.0 with the
   notice; the 4.2.0 cache remaining with `.orphaned_at` is recorded as
   expected.

The independent verifier repeats checks 1 to 4 on the retained archive's
extracted package before the tag.

After publication, the verifier checks the published artifact. These checks
are also written into the rewritten acceptance procedure:

- The downloaded release asset's SHA-256 matches the accepted digest, and
  the extracted package digest matches the 4.4.0 record in `releases.json`.
- A clean install from the published GitHub marketplace
  (`acoz-labs/quickstop`), under a temporary `HOME` and
  `CLAUDE_CONFIG_DIR`, shows 4.4.0 at the pointer's commit, one skill
  (`claudit`) and no agents. That install needs no login.
- A temporary config dir isn't logged in, so the model turns run on the
  normal login from a throwaway worktree, with `--plugin-dir` set to the
  package that the published install wrote (or the extracted downloaded
  asset), `--setting-sources project,local`, `--strict-mcp-config` and
  `DISABLE_AUTOUPDATER=1`. The three prompts and grading rules of check 2
  apply unchanged, with the negative control.
- The update path of check 4 runs against the published marketplace: install
  4.2.0 from a local directory marketplace at the 4.2.0 commit, re-point it
  to `acoz-labs/quickstop`, update, and see 4.4.0 with the notice.
- The post URL returns HTTP 200, and `/doctor prompt-audit` is recognised by
  the Claude Code that runs the checks; both are recorded with its version.

Results are posted on the issue, not committed, and carry no machine paths.

## Rollback

Before the pointer PR merges, nothing is advertised: revert the plugin PR.

After it merges, a fault in 4.4.0 itself (a wrong link, the model auditing
anyway, a broken skill) is fixed forward with 4.4.1 through the same two-PR
flow. Restoring 4.2.0 would re-advertise the auditing version the owner
retired and wouldn't downgrade users already on 4.4.0.

Restoring the 4.2.0 lock record and the previous catalog description, with a
reviewed pointer PR and regenerated indexes, is kept for a failure of the
pointer PR itself (a wrong commit pin or a listing that won't load). 4.2.0's
record stays in history for that. The `claudit-v4.4.0` tag and its release
asset stay as published; a later release with different bytes takes a new
number.
