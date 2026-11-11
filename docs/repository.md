# Quickstop repository

Quickstop is a home for agent plugins and practical, read-and-adapt workflows.
Its first workflow, [Shipshape](../workflows/shipshape/README.md), was retired on
2026-11-05 and is kept for reference only. Claudit and the
Writing for Humans kit are Claude Code plugins at `plugins/<name>/`; Quickstop supports
no other agent tool. Their advertised versions and publication
state are recorded in the [generated catalog](catalog.md). `catalog.json`
declares each plugin's `claude-code` target; native package manifests own versions. Generated
indexes and package layouts follow [the marketplace contract](marketplace.md).
Plugin creation and review use the shared SDLC and development guide.

`AGENTS.md` and `docs/operations/sdlc.md` define delivery authority and roles.
`CLAUDE.md` imports this guidance for Claude Code. Use conventional commit titles;
retain honest author/committer attribution without generated-tool trailers.
Preserve existing MIT notices. Personal identities and machine setup stay outside
this repository.

## Commands

Requires Git, Bash and Python **3.11.15**, pinned in `.python-version` (standard
library only; no downloaded Python dependencies). Install it with mise
(`mise install python@3.11.15`) or put it on PATH under a version name, then run
the bare commands:

```sh
bin/ci
bin/check-marketplace --base origin/main
bin/sdlc check
```

`bin/ci` and `bin/check-marketplace` find the pinned version themselves: they try
`python3.11`, `python3` and `python` in every PATH directory, then `mise where
python@3.11.15`, so another `python3` earlier on PATH does not matter. If none
reports exactly 3.11.15 they name the version and exit 1. `bin/ci` runs its
checks and tests on that interpreter. `bin/sdlc` is SDLC-managed and runs on
whichever `python3` comes first; `bin/sdlc check` passes on Python 3.9.6 as well,
and `bin/ci` runs it on the pinned version.
`.claude/settings.json` pre-approves exactly these three bare commands, so they
run without a prompt; any other arguments, or a PATH change, still prompt.
`AGENTS.md` offers `bin/container bin/ci` where supported; this repository
provides no `bin/container`, so verification runs `bin/ci` directly on the
pinned Python.
The initial compatibility run also passed on Python 3.9.6; release evidence uses
the pinned runtime, not the system default.

Healthy output:

- `bin/ci`: exits 0, prints `Using Python 3.11.15 at <path>`, the
  `bin/sdlc check` line and unittest's `OK`. A missing pinned Python prints
  the version it needs and exits 1.
- `bin/check-marketplace --base origin/main`: exits 0 and prints
  `Marketplace valid: <n> plugin(s); package versions checked`.
- `bin/sdlc check`: exits 0 and prints `{"version": "<version>", "conforms": true}`.

`bin/ci` runs managed conformity, optional-plan validation, catalog/adapter
checks and regression tests. `--base` additionally rejects changed plugin bytes
without a strictly higher stable version. Supply the actual pre-change commit;
an unavailable base is an error, never a reason to skip validation. All distributed
files, including README changes, count as bytes. Python bytecode caches (`__pycache__/`,
`*.pyc`) are local state and never count, in `--base` or in
`bin/marketplace-release verify-package --path`; `bin/ci` does not write them. Generated listings derive
versions from the native manifests; plugins release independently. Regenerate indexes with
`bin/check-marketplace --write` after changing catalog or manifest metadata.

Use the host's `claude plugin validate .` and `claude plugin validate
./plugins/<name>` when available. These supplement local
checks and do not prove runtime behavior. Acceptance scenarios belong
in [delivery](delivery.md). Inspect current host documentation for unfamiliar
components instead of treating the lightweight local validator as a complete
upstream schema implementation.

`scripts/check-plugin-versions.sh BASE` remains a compatibility wrapper. Repository
push hooks and Claude shell-match hooks have been retired; clean-checkout evidence
is the verification gate. Existing clones with the old installed pre-push hook
may remove that specific hook after inspecting it; do not replace personal hooks.

## Conventions

- Only rebase merges are allowed. Before the merge go, check
  `git merge-base --is-ancestor origin/main <head>`. A rebase merge rewrites
  commit IDs and changes `git archive` digests (the commit ID is embedded),
  so name candidates and gate results by tree hash, and record
  `CANDIDATE.txt` (tree, head, extraction write-tree, plugin tree) in every
  eval result directory.
- Commits and PR bodies carry no generated-tool trailers (co-author lines,
  session links). Remove any a harness adds before review.
- `AGENTS.md` is SDLC-managed and hash-pinned; repository notes go here.
- `.claude/settings.json` allows exact commands only. A `--flag *` rule also
  matches arguments appended later (such as `--write`), so add exact rules
  and probe appended forms under `dontAsk`. Leave out of the allowlist:
  `--write` steps, placeholder forms (`PRE_CHANGE_SHA`, `BASE`), paid eval
  runs, release and setup steps, and `claude plugin validate` commands.
- Model-turn acceptance runs use `claude -p` from a throwaway clone on the
  normal login, with `--plugin-dir`, `--setting-sources project,local`,
  `--strict-mcp-config` and an isolated cache directory where one applies.
  No `claude mcp` commands and no change to real Claude config or
  credentials. A temporary `CLAUDE_CONFIG_DIR` isn't logged in, so it can't
  run model turns. Settle this method at triage.
- Clean-install checks run from a script that sets `HOME` and
  `CLAUDE_CONFIG_DIR` to a fresh `mktemp -d` directory and hashes
  `~/.claude/settings.json` and `~/.claude/plugins/*.json` before and after.
  Don't byte-hash `~/.claude.json`: live sessions rewrite it every few
  seconds. Scope run-state checks to known paths, never `find` over `$HOME`.
- Set `DISABLE_AUTOUPDATER=1` on every headless `claude` call: background
  marketplace refresh rewrites `~/.claude/plugins/known_marketplaces.json`
  mid-run.
- A plugin release takes two PRs: the plugin PR (package and version bump),
  then, after acceptance and the release tag, the pointer PR (`releases.json`,
  regenerated indexes). `catalog.json` description changes, including the
  marketplace description, go in the pointer PR, never the plugin PR: promote
  regenerates the indexes from the head's catalog.
- The implementer's pre-push hook refuses tag pushes, archive tags included;
  the reviewer creates and pushes them, and the implementer checks the peeled
  commit and tree.
- `bin/marketplace-release promote` runs only as the maintainer account. The
  contributor writes the pointer files with promote's logic, and the
  reviewer confirms by running promote on the head ("Already points at this
  accepted artifact", no diff).
- Paid eval gates: define grader metrics and the miss-counting rule before
  the first paid run; make structural checks (paths, commands) script
  graders, because model judges misgrade them; run the $0 script-only scan
  of the real gate repositories at every head; screen each candidate by tree
  at n=1 before the full gate; and start the counted gate only on a tree the
  reviewer has cleared. A screen may stand for a later tree only when the
  requester agrees and both tree hashes are recorded. Keep judge replies.
- Cap every paid run with `--max-budget-usd`. `doctor-combined` costs about
  $0.50 a run, about six times plain.
- `claude plugin eval` (2.1.312 and later): `--eval-dir` must be inside the
  plugin root, so run from a scratch copy; every run starts in an empty
  workspace, so fixtures come through `context.scaffold_script`; sandboxed
  Bash reads only the plugin under test plus the run's home and workspace;
  `--case` takes exact names and silently matches nothing for globs.
- `/usr/bin/git` on macOS is an xcrun shim that fails in the plugin-eval
  sandbox: copy a real git into the scratch plugin, as
  `bin/writing-for-humans-eval` does.
- An eval's summarize step validates against the expected suite (cases,
  grader stems, run counts), or a partial run reads as PASS. Post results on
  the issue; don't commit them.

## Known mistakes

- Builder scripts write `rm -rf "${VAR:?}"/*`, never `rm -rf $VAR/*`, and
  delete exact scratch paths they created, never globs, while runs or other
  agents are active. A glob delete once killed a running eval.
- Never edit a bash script while it runs. To change course, stop the parent
  by exact PID and chain from a new script. Single-quote log notes that
  contain `$` under `set -u`. Run multi-argument headless loops from bash:
  zsh doesn't word-split loop variables.
- Don't edit files while a checker runs.
- When a product security check (such as canonical paths) breaks tests on
  one OS, fix the fixtures, not the check.
- `claude -p --setting-sources project` ignores project allow rules in a
  never-trusted folder such as a fresh clone. For headless no-prompt checks,
  use a throwaway `git worktree` of a trusted clone and remove it after.
- When mise is active, `mise exec` can put the pinned Python after
  `/usr/bin`; `bin/ci` finds the pinned version itself.
- An `--allow-tools` allowlist in `claude plugin eval` doesn't refuse
  built-in read-only commands (`ls -R`, `grep`, `head`, `git ls-files`).
  Probe a permission-boundary claim with a non-read-only command, and state
  the exemption in the doc.
- Under `claude -p`, init's `output_style` echoes any value, even a
  nonexistent one. Prove a style with a $0 `/output-style` preflight that
  shows "(current)", a per-run init check, and negative controls.
- Output-style selection can't be tested inside `claude plugin eval`, whose
  child runs with its own config dir; test it outside under a temporary
  `HOME` and `CLAUDE_CONFIG_DIR`.
- Natural-language graders oscillate when they match phrasing. Match
  structure and co-occurrence, with a fail-closed co-occurrence fallback;
  before the counted gate, run a false-negative pass (six or more real
  phrasings per grader from recorded reports), an attacker pass and
  adversarial controls (negation on the same line, rhetorical questions),
  and regrade recorded reports at $0. Exclude Claudit's own citation lines
  from diagnosis cues.
- LLM-comparator calibration needs borderline pass and fail samples from the
  key, not just extremes.
- Opening-sentence splitters treat bold-only heading lines as headings, or
  the excerpt differs by style.
- Allow-only grammars (allowlist suggestions, natural-language rules) are
  designed as allow-only from the start. Before the PR, do an attacker pass:
  add a limiting or reversing qualifier to every allowed form and an
  imperative to every rejected form, and check every other caller of a
  narrowed helper.
- End-to-end probes use a command the scan can learn only from prose:
  `bin/ci` is detected from its file name.
- Check fixture hooks against the host toolchain before a paid gate: a
  fixture's `go test ./...` Stop hook fails where `go` is a mise shim with no
  version, and then that fixture measures nothing.
- Each script with its own spend pause needs the raise when a cap changes.
- Write docs with an editor tool or a quoted heredoc: an unquoted `$0.052`
  became `/bin/zsh.052`.
- `bin/sdlc audit` right after a merge can fail until GitHub links the
  commit to its PR. Retry after a minute.
- Known limitation: the `writing-audit` frontmatter blocks only plain command
  prefixes (`git -C <dir> push` and `git commit -a --amend` pass), so the
  README recommends deny rules.

## Layout and tracking

- `catalog.json`: ordered plugin catalog, one `claude-code` target each.
- `plugins/<name>/`: one self-contained Claude Code package per plugin.
- `workflows/`: ordinary Markdown guides with a browsable entry index; no native installable packages.
- `.claude-plugin/marketplace.json`: generated native marketplace index.
- `docs/catalog.md`: generated version table.
- `bin/`, `tests/`: portable delivery tools and real marketplace regressions.
- `evals/`: model-run eval suites outside plugin bytes. Claudit's suite and runner were removed
  when Claudit was retired in 4.4.0. `bin/writing-for-humans-eval` runs the Writing for Humans
  kit's release check, which checks for regressions (install, style selection, the user-only
  audit contract), not writing quality.
  `bin/writing-for-humans-quality-eval` runs the quality eval: the same writing tasks under the
  default, Concise and Writing for Humans styles, graded for cold-read clarity, pedantry and repetition.
- `docs/`: development, delivery and maintained investigation findings.
- `.sdlc/`: managed standard identity and repository-specific artifact profile.

[Project 40](https://github.com/orgs/acoz-labs/projects/40) uses Inbox, Ready,
In Progress, Review, Release, Done, Blocked and Parked. Plans are proportional;
future product choices remain to be made with the owner. Actions are opt-in on
trusted self-hosted runners. Local independent proof is the default.
