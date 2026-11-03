Three of the five services are on the new logger: accounts, notifications and gateway, each committed with its tests passing. Could you get me read access to the search staging cluster, or ask Priya Raman to grant it? Without it I can't test the search migration, and the old logger can't be removed on 14 November while search still uses it.

Billing is about half done, and search hasn't started.

**Billing** has 27 of about 55 call sites changed, uncommitted. It stopped at the invoice PDF renderer, which hands a logger to a vendored library that expects the old logger's interface. That needs a small adapter, which I'll write next.

**Search** needs 22 straightforward changes. I left its code alone because its tests run against staging, and my credentials are refused there (403, not a member of search-staging-readers).
