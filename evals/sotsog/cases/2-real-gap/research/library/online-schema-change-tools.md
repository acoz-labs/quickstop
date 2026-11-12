# Online schema change tools: let a tool do the migration for you

Source: https://dbtools.example.org/guides/online-schema-change
Author: Lars Pettersen, database consultant
Published: 2026-01-27

Instead of hand-writing safe migrations, an online schema change tool builds a
shadow copy of the table, keeps it in sync with triggers, and swaps it in with
a brief lock. It handles type changes and big rewrites safely. It adds a
moving part to every deploy and needs extra disk for the copy, so it suits
teams with many large-table migrations and a database administrator to own it.
