# Writing for Humans for Claude Code

Teams that work with agents get more documents than people can read. Writing for Humans is an output style that makes what Claude writes easy to take in at reading speed. It opens with the point, then what you need to do or decide, then what's at stake, and it writes for a colleague who wasn't in the session. The plugin also supplies a skill with fuller references and a writing audit you run yourself.

## Install and select

```sh
claude plugin marketplace add acoz-labs/quickstop
claude plugin install writing-for-humans@quickstop
```

Claude Code reads style files when it starts, so start a new session after installing, or run `/reload-plugins`. Then select the style:

```text
/output-style writing-for-humans:writing-for-humans
```

The command saves the selection to `.claude/settings.local.json`, so it applies to the current project on this machine. For a default across projects, set `outputStyle` in `~/.claude/settings.json`; a project's own setting takes precedence. Installing the plugin doesn't replace an existing style, because the style doesn't set `force-for-plugin`. Run `/output-style` to see which style is active.

From the mobile app or the web through Remote Control, `/output-style` can list and select only built-in styles, so you can't pick this one there. Setting `outputStyle` to `writing-for-humans:writing-for-humans` in a settings file works there.

## What the style does

- **The opening.** For anything a person reads (replies, reports, PR descriptions, design notes, handoffs, status updates), sentence 1 is the point, sentence 2 is what the reader needs to do or decide, or that nothing is needed, and sentence 3 is what's at stake. The rest is support the reader can stop reading.
- **The cold read.** No file name, path or identifier as a sentence's subject, no session-coined terms or unexplained acronyms, and no bare pointers to other documents. Code comments and review comments anchored to a line are exempt.
- **No pedantry, no repetition, no narration.** It doesn't explain what a competent colleague already knows, says each thing once, and gives conclusions rather than the steps taken to reach them. Evidence is kept but moved out of the main line.
- **Explicit asks and fewer documents.** Every ask can be answered without looking anything up. It updates an existing document rather than starting a new one.

Team and repository standards, templates and required attribution outrank the style. It preserves facts, uncertainty and quotations, and leaves structured data alone. It's an instruction Claude follows, not a guarantee, and it doesn't check facts or validate machine output.

The style keeps `keep-coding-instructions: true`. On Claude Code's shorter system prompt, which current models use, that field has no effect, because the shorter prompt doesn't include the coding-instructions section. It matters only on the full system prompt.

Output styles apply to the main conversation and to forks. Other subagents run their own system prompt, so the style tells Claude to rewrite subagent output to this standard before relaying it to you.

## Skills

- `writing-for-humans:writing-style` holds fuller references for workflow artifacts, questions asked of a person, and the optional cold-reader check. Claude can load it when writing one of those.
- `writing-for-humans:writing-audit` reviews the writing a change left behind: artifacts, code comments in the diff, PR descriptions and unpushed commit messages. It runs only when you type `/writing-for-humans:writing-audit`, and it follows your existing task authorization and repository rules.

The audit's boundaries are enforced where Claude Code supports it. Its `disallowed-tools` frontmatter removes `git push`, `git rebase`, `git commit --amend`, `git reset`, `git filter-branch`, `git filter-repo` and `gh pr merge` while it runs. A test confirmed that a Bash pattern there denies the matching command, even with Bash allowed. Some limits remain:
- The restriction clears when you send your next message.
- It matches command prefixes, so another spelling such as `git -C dir push`, an alias or a script isn't caught.
- `allowed-tools` only pre-approves tools and can't restrict anything, so the audit doesn't set it.

For hard guarantees, add deny rules to your permission settings.

## Upgrading from 0.3.1

1.0 is one style with no personal voice preset. It drops 0.3.1's em-dash ban, numeral and contraction rules, the "I means the user" convention, the register split and the conventional-comments mandate. If you want those, keep them in your own custom output style: create it under `~/.claude/output-styles/` with a distinct name and select that instead. Don't edit the installed plugin cache, because updates replace it.

## Update or remove

Run `claude plugin update writing-for-humans@quickstop`, then `/reload-plugins` or start a new session to pick up the update. To stop using the style, choose another one first, for example `/output-style default`, then disable or uninstall:

```sh
claude plugin disable writing-for-humans@quickstop
claude plugin uninstall writing-for-humans@quickstop
```

Earlier conversation context can keep old guidance, so check removal in a fresh session.

## Provenance

Converted from the privately retained original shared kit, then rebuilt for 1.0 around the opening and the cold read. Quickstop's release record lists the tested versions, and `docs/acceptance/writing-for-humans-quality-baselines.md` has the quality measurements. License: MIT.
