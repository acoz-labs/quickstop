# Writing for Humans for Claude Code

Make explanations and questions understandable to someone who was not in the session. This plugin packages the original Writing for Humans kit: an opinionated output style, writing references, and an optional audit of a completed change.

## Install and select

Once this version is listed in Quickstop:

```sh
claude plugin marketplace add acoz-labs/quickstop
claude plugin install writing-for-humans@quickstop
```

Restart Claude Code to discover newly installed styles, then select:

```text
/output-style writing-for-humans:writing-for-humans
```

The native command saves the style selection for the current project. Use Claude Code's native settings if you deliberately want a user-wide default. Installing the plugin alone does not replace an existing style. Once selected, the style applies to ordinary replies without a writing command. It retains Claude Code's built-in coding instructions.

Run `/output-style` to inspect the active selection. The plugin also supplies `writing-for-humans:writing-style` and `writing-for-humans:writing-audit`. The writing references can load when relevant; invoke the audit when you want to review writing left by a change. It follows your existing task authorization and repository rules.

## What the kit does

The central test is whether a reader can understand the claim, what is being asked and why it matters without reconstructing the writer's investigation. Explain the behavior before attaching file locations or ticket references. Keep useful evidence. Spend more words when understanding requires them, and remove background the reader does not need.

The bundled preset also has deliberate tastes: spoken phrasing, no prose em dashes, concise updates and restrained code comments. These are preferences of the selected style, not findings to impose on colleagues. Explicit task instructions, required attribution and repository standards take precedence.

A cold-reader reference describes how a fresh reader can check a difficult question. It is available for bounded use when helpful and authorized; it is not an extra model call on every reply or an automatic approval gate. The audit similarly does not run a background rewrite loop.

## Boundaries and customization

This is a Claude Code writing aid. It does not guarantee factual accuracy or valid machine output. Preserve supplied facts and qualifications, and use caller-side validation when software consumes generated output. Output styles affect the main conversation and inherited forks; independent subagents have their own prompts. This plugin does not impose an orchestration architecture or claim universal subagent coverage.

Keep personal voice instructions and examples in your own configuration. Do not edit the installed plugin cache: updates can replace it. To make a separate custom style, use Claude Code's native user or project output-style support and give it a distinct name; you maintain that copy. See [adoption guidance](ADOPT.md).

No hooks, runtime dependencies, network service or global instruction installer are included. Codex and Pi versions from the earlier experiment are archived and are not distributed as this product.

## Update or remove

Use `claude plugin update writing-for-humans@quickstop` for an advertised update, then restart to reload files. To stop using the style, choose another native style first, for example `/output-style default`. You can then disable or uninstall:

```sh
claude plugin disable writing-for-humans@quickstop
claude plugin uninstall writing-for-humans@quickstop
```

Earlier conversation context can retain guidance, so check removal in a fresh session. Changing the style selection is deliberate; removal does not restore an unknown previous preference on your behalf.

## Provenance

Converted from the privately retained original shared kit. Changes cover native packaging, portable references, coding-instruction preservation, existing authorization and repository-rule precedence, optional bounded checks, and independently invented public examples. The core writing approach and opinionated preset are retained. See Quickstop's release record for tested versions and conversion evidence. License: MIT.
