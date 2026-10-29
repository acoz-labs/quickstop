---
type: llm
weight: 1
---
The fixture ships a Claude Code plugin (`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `skills/changelog-entry/SKILL.md`). Its CI workflow `.github/workflows/ci.yml`, README and CONTRIBUTING run only Python unit tests; nothing validates the plugin manifest, marketplace file or skill frontmatter.

PASS only if the report (1) identifies that the plugin is never validated (no `claude plugin validate` in CI or in the documented contributor steps), and (2) recommends running `claude plugin validate .` (or `claude plugin validate` against the plugin directory) in CI and/or the documented checks.

FAIL if the report only suggests "more tests" or "validate the JSON" with a generic JSON linter, or mentions validation without saying to add it to CI or the docs.
