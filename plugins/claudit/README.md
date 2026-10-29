# Claudit

Claudit grades a project's Claude Code setup against what the project is for, then
recommends the few changes that would improve it most and can apply the ones you pick.

## Installation

From the Quickstop marketplace in Claude Code:

```text
/plugin install claudit@quickstop
```

For local development, load the checkout with
`claude --plugin-dir /path/to/quickstop/plugins/claudit`. The marketplace advertises
only the accepted release; a development checkout can contain a newer candidate.

## Use

```text
/claudit:claudit                  # audit this project, then offer to apply changes
/claudit:claudit hooks            # same, with a deeper look at hooks
/claudit:claudit --read-only      # report only
/claudit:claudit --user           # also check your ~/.claude settings and CLAUDE.md
```

Asking Claude to audit or improve the Claude Code setup also invokes it.

## What you get

1. **Intent**: what the project builds, how work gets done (check and CI commands,
   procedure docs, release flow) and who drives it. Interactive runs ask you to
   confirm or correct it once; headless runs state the assumption.
2. **Three grades**, each a letter with a confidence:
   - **Correctness**: does what's configured work?
   - **Alignment**: does it serve the project's intent?
   - **Coverage**: what's missing that a project like this should have? Graded
     against a baseline every project should meet (a short CLAUDE.md, a check Claude
     can run, routine commands pre-approved, secret paths denied, must-always rules
     enforced by hooks or permissions) plus profiles picked from project signals:
     agent-run repository, plugin or marketplace repository, typed codebase,
     repository with procedure docs.
3. **The top 3 to 7 changes**, ranked by impact across the three grades. Each has
   the reason, the exact diff or command, the doc URL and heading it rests on, and
   the effort.
4. **An offer to apply** the changes you select, in place or on a branch in an
   isolated worktree with a pull request through `gh`.

Process detail stays in a short footer, including Claude Code documentation pages
that are newer than Claudit's feature catalog.

## How it works

- `skills/claudit/scripts/claudit.py` scans the project: inventory, project signals,
  and the misconfigurations the docs name (for example `Write(...)` path rules,
  `.claudeignore`, flat skill files, project `bypassPermissions`, array hook
  matchers, oversized CLAUDE.md, broken `@` imports and stale paths). It is
  read-only and needs only the standard library of Python 3.9 or later.
- `skills/claudit/catalog.json` is the versioned feature catalog: each feature, the
  intent it fits, how to tell it's in use, its doc URL and heading, and its minimum
  Claude Code version. It carries every check and recommendation, so an audit works
  with the docs unreachable.
- Each audit reads `https://code.claude.com/docs/llms.txt` and at most a couple of
  pages live with WebFetch (pre-approved for `code.claude.com` while the skill runs),
  cites the URL and heading for each claim, and lists index pages the catalog
  doesn't know yet.
- One read-only Sonnet `auditor` agent handles cross-file review on large setups;
  small repositories don't use it. The skill itself runs on Sonnet.
- Claudit points you to the native checks it can't run for you: `/doctor`,
  `/doctor prompt-audit`, `/insights` and `/skill-doctor`.

## State and writes

Claudit keeps no cache and writes nothing outside the project. An audit writes
nothing at all. It writes only when you apply changes, or when you ask it not to
repeat a suggestion: that goes in `.claude/claudit-dismissed.json` in the project.

## Requirements

Claude Code 2.1.312 (tested). `python3` 3.9 or later; without it Claudit reads the
files itself at lower confidence. Git for branch delivery and `gh` for pull requests.

## Upgrading from 3.x

4.0 removes the `knowledge`, `refresh` and `status` skills, the research and the
three audit agents, the docs cache and the decision store. Old files under
`~/.cache/claudit` (or `CLAUDIT_CACHE_DIR`) are no longer read; delete them when you
no longer need them. Project `.claude/claudit-decisions*.json` files are ignored.

MIT licensed; see [LICENSE](LICENSE).
