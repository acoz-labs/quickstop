Accounts, notifications and gateway are on the new logger, each committed with its tests passing; billing is about half done and search hasn't started. Could you get me read access to the search staging cluster, or ask Priya Raman to grant it? Without it I can't test the search migration, and the old logger can't be removed on 14 November while search still uses it.

**Billing** has 27 of about 55 call sites changed, uncommitted. It stopped at the invoice PDF renderer, which hands a logger to a vendored library that expects the old logger's interface. That needs a small adapter, which I'll write next.

**Search** needs 22 straightforward changes. I left its code alone because its tests run against staging, and my credentials are refused there (403, not a member of search-staging-readers).
