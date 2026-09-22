# Claudit acceptance

Supported target: **Claude Code**. Codex and other harnesses are not supported.
A compatible package parser does not establish support for Claude-specific audits.

For an actual Claudit release, use the retained package and isolated Claude Code
configuration described in [delivery](../delivery.md). Record the exact host
version, package version/digest and synthetic consumer inputs.

- Install the marketplace package; verify its four skills and six agents load.
- Exercise audit inside a synthetic Git repository and global-only detection
  outside it, using an isolated home/configuration.
- Exercise knowledge, refresh and status with fresh, stale and missing caches;
  verify actual read/write effects and report failures honestly.
- Check read-only audit requests preserve consumer files and any assigned fixes
  or PR-delivery scenarios respect their explicit scope.
- Exercise the assigned issue criteria and retain sanitized observations.

These are acceptance procedures, not a claim that runtime acceptance has already
been performed. Marketplace infrastructure tests do not substitute for them.
