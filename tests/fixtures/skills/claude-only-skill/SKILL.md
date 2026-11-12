---
name: claude-only-skill
description: A fixture that uses one feature only Claude Code supports per rule.
argument-hint: "[file]"
---

# Skill that only Claude Code can run

Summarize $ARGUMENTS for the user.
Today's branch: !`git branch --show-current`
Read ${CLAUDE_PLUGIN_ROOT}/references/guide.md before you start.
Use the `Read` tool to open the file.
Follow the `writing-for-humans` output style.
Add a PreToolUse entry to block pushes.
