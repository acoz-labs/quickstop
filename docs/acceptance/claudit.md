# Claudit acceptance

Claudit was retired on 2026-11-11. Its last release, 4.4.0, runs no audit: the
`claudit` skill replies with a retirement notice that says to run `/doctor`, then
`/doctor prompt-audit`, and links https://acoz.dev/blog/retiring-claudit/. This
procedure accepts that release. The procedure for the last auditing version,
4.2.0, is at the
[`claudit-v4.2.0` tag](https://github.com/acoz-labs/quickstop/blob/claudit-v4.2.0/docs/acceptance/claudit.md).

Supported target: **Claude Code**. Use the retained package as described in
[delivery](../delivery.md). Record the Claude Code version, the package version
and digest, and every command, input and output. Passing manifest validation alone
is not acceptance. Results go on the issue, not in the repository, and carry no
machine paths.

## Isolation

- Install and inventory checks run from a script that sets `HOME` and
  `CLAUDE_CONFIG_DIR` to a fresh `mktemp -d` directory. They need no login.
- A temporary config directory isn't logged in, so model turns run on the normal
  login from a throwaway `git worktree` of a trusted clone, with `--plugin-dir` set
  to the package under test, `--setting-sources project,local`,
  `--strict-mcp-config` and `--output-format stream-json --verbose`.
- Every headless `claude` call sets `DISABLE_AUTOUPDATER=1`.
- Claude Code refuses `file://` marketplaces; a candidate is installed from a local
  directory marketplace instead.
- Graders read the whole output. Never grade a truncated excerpt.

## Candidate scenarios

Run these on the extracted retained package before the release tag.

1. **Install.** Install 4.4.0 from a local directory marketplace holding the
   candidate. The inventory shows one skill, `claudit`, and no agents. Record
   `claude plugin validate --strict` on the package.
2. **The notice, and no audit.** In a synthetic Git repository, run three prompts:
   `/claudit:claudit`, `/claudit:claudit --read-only hooks`, and the plain request
   "audit my Claude Code setup with Claudit". A run passes only when all of these
   hold:
   - the final reply contains "retired", `/doctor`, `/doctor prompt-audit` and
     https://acoz.dev/blog/retiring-claudit/;
   - the init event lists the `claudit` skill and no `auditor` agent;
   - the two slash-command runs make no tool calls, and the plain request makes
     exactly one, a Skill call for `claudit`. Any other tool call (Read, Grep, Glob,
     Bash, WebFetch, Agent, Task or anything else) fails the run.

   Negative control: the plain request without the plugin must not produce the
   post URL, so the grader can tell the skill's reply from a guess.
3. **Consumer state.** The synthetic repository's files, Git index and working tree
   are unchanged. No `~/.cache/claudit` or `CLAUDIT_CACHE_DIR` directory is
   created. `~/.claude/settings.json` and `~/.claude/plugins/*.json` in the
   temporary home are hashed before and after. Don't byte-hash `~/.claude.json`,
   which live sessions rewrite.
4. **Update from 4.2.0.** Install 4.2.0 from a local directory marketplace at the
   4.2.0 commit, point that marketplace at the candidate, update, and see 4.4.0
   and the notice. The 4.2.0 cache staying on disk with `.orphaned_at` is expected;
   record it.

## Gate before publishing

https://acoz.dev/blog/retiring-claudit/ returns HTTP 200, recorded with the time.
Don't create the GitHub Release or merge the pointer PR until it does, unless the
factory says otherwise.

## Published-artifact scenarios

Run these after the GitHub Release and the pointer PR.

- **Bytes.** The downloaded release asset's SHA-256 matches the accepted digest,
  and the extracted package digest matches the 4.4.0 record in `releases.json`.
- **Clean install.** In a fresh temporary `HOME` and `CLAUDE_CONFIG_DIR`, install
  from the published `acoz-labs/quickstop` marketplace. It shows 4.4.0 at the
  pointer's commit, one skill (`claudit`) and no agents.
- **Model turns.** Repeat scenario 2, with its negative control and grading rules,
  with `--plugin-dir` set to the package the published install wrote, or to the
  extracted downloaded asset.
- **Update, the way users update.** Before the pointer PR merges, while the
  published marketplace still serves 4.2.0, install 4.2.0 from it into a kept
  temporary `HOME` and `CLAUDE_CONFIG_DIR`. After the merge, in that same home,
  record that 4.2.0 is still installed, then run the marketplace update and the
  plugin update. Record 4.4.0, the notice and the orphaned 4.2.0 cache. Never
  remove and re-add the marketplace: that uninstalls its plugins and turns the
  test into a fresh install.
- **Pointers work.** The post URL returns HTTP 200, and `/doctor prompt-audit` is
  recognised by the Claude Code that runs these checks. Record both with its
  version.

## Recovery

A fault in 4.4.0 itself is fixed forward with 4.4.1. Restoring the 4.2.0 record is
only for a failure of the pointer PR, because it would re-advertise the auditing
version that was retired.
