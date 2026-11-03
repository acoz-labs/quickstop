# Finding SEC-2291: static API tokens on the v1 auth path

Severity: medium. Remediation due: 30 November.

The v1 endpoints accept long-lived static tokens that never expire and can't be scoped. A leaked token gives full account access until someone revokes it by hand. v2 uses short-lived OAuth tokens.

Accepted remediations: remove the v1 auth path, or get a documented risk acceptance from the API owner with a new date.
