I looked into the nightly partner export failure as you asked. First I read through the evidence directory, starting with the worker log, then the notes, then the config and the diff. Here is a summary of the investigation, organised into sections.

## Background

A nightly export is a scheduled job that runs once a day, usually at night, to copy data from one system to another. Parquet is a columnar file format that is commonly used for analytics, and a row group is a chunk of rows that the writer keeps in memory before flushing it to disk. Memory limits are set on containers so that one job cannot use all of a machine's memory.

## Findings

`export-worker.log` shows the run on 2026-10-31T02:00Z ending in OOMKilled (exit 137). `notes.md:4` says Dependabot PR #412 bumped parquet-writer 2.8.4 -> 3.0.1. `row_group_size` defaulted to 1000000 because `config/export.yaml` never set it. The export ran out of memory because the row group default changed. `fix/export-row-groups` adds one line.

## Summary

To summarise, the export ran out of memory because the row group default changed. The fix is on a branch. Let me know if you have any questions or if there is anything else I can look into.
