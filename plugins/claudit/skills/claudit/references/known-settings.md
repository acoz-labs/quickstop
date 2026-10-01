# Current baseline and evidence pointers

Reviewed against official documentation on 2026-10-01 and host 2.1.287. This is a
small fallback reference, not a permanently current schema. Fresh official source
claims and observed native behavior take precedence; unknown fields need research,
not automatic deletion. Record which host a finding applies to.

## Configuration and permissions

Settings scopes generally rank managed > CLI/session > local > project > user,
with merged arrays and field-specific security exceptions. `permissions.allow`,
`permissions.ask`, `permissions.deny` and `permissions.defaultMode` belong in
settings. `--allowedTools` and `--disallowedTools` are CLI/SDK surfaces, not
corresponding top-level settings lists. Current documented modes include
`default`, `acceptEdits`, `plan`, `dontAsk`, `bypassPermissions` and `auto` where
supported; availability depends on version/account/environment. Neither
`auto-edit` nor `full-auto` is the current setting spelling. Default permission
behavior is valid; more permissive modes are not an optimization for granular rules.
Inspect sandbox configuration separately from permission prompts. Resolve file
permission pattern anchors before judging their effect: in `Read`/`Edit` rules,
`//path` is filesystem-absolute, `/path` is relative to the settings source, and
`~/path` is home-relative (see Permissions → Read and Edit). A path outside the
current home is not intrinsically wrong. If the user explicitly intends an
absolute protected target but the rule uses a settings-relative anchor, the
verified mismatch is a real finding; never infer that intent from a path alone.

```json
{
  "permissions": {
    "defaultMode": "default",
    "allow": ["Bash(git status)"]
  },
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{"type": "command", "command": "./scripts/check-command.sh", "timeout": 30}]
    }]
  }
}
```

This illustrates schema, not a recommendation to install or execute the example
hook. Hook handlers are nested under matcher groups. Timeouts use **seconds**,
and omission selects a type-specific default. Current hooks include command,
prompt, agent, HTTP and `mcp_tool` handlers; event compatibility, async behavior, matchers,
exit/output contracts and auth fields differ by handler. Fetch the current event
reference rather than maintaining a guessed fixed event count.

## Plugins and context

`commands/` remains supported; new workflows may benefit from skills, but an
existing command is not broken. The plugin manifest is optional; when supplied,
`name` is required. Other metadata and component directories are optional.
Validate actual default and declared paths, including inline hook/MCP/LSP config.
Official marketplace entries receive the same evidence-based checks as others.

MCP transports have different requirements: stdio requires a command (args may
be omitted); HTTP/SSE endpoints do not require a local command. A configured name
is not proof of connection health or usage. Tool search/deferred loading and
`alwaysLoad` affect prompt overhead. Inspect actual `/context` or plugin cost
observations when available; do not assign a universal per-server token charge.

Skills/subagents use native Claude frontmatter. Model aliases resolve on the
host; do not freeze a stale model catalog or invent effort levels. Research uses
`sonnet` for source discrimination, no persistent memory, and `omitClaudeMd: true`
(supported since 2.1.271) to avoid unrelated instruction loading. This is an
architectural choice, not a measured latency/quality guarantee. Audit agents also
omit inherited instructions and receive the scoped files explicitly as data.

## Official sources

- [Settings and precedence](https://code.claude.com/docs/en/settings)
- [All settings](https://code.claude.com/docs/en/settings-reference)
- [Permissions](https://code.claude.com/docs/en/permissions)
- [Memory and instruction loading](https://code.claude.com/docs/en/memory)
- [Hooks](https://code.claude.com/docs/en/hooks)
- [MCP](https://code.claude.com/docs/en/mcp)
- [Plugin manifest](https://code.claude.com/docs/en/plugins-reference)
- [Plugin components](https://code.claude.com/docs/en/plugins/components)
- [Plugin cost measurement](https://code.claude.com/docs/en/plugins/measure)
- [Mods](https://code.claude.com/docs/en/plugins/mods/overview)
- [Skills](https://code.claude.com/docs/en/skills)
- [Subagents](https://code.claude.com/docs/en/sub-agents)
- [Models and effort](https://code.claude.com/docs/en/model-config)
