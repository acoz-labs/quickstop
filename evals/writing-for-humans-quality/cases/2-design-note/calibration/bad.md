# Job queue discussion

This document summarises the discussion held on Tuesday 3 November between 14:00 and 14:35 about the job queue for the Ferrylog sync service. The attendees were Dana, Marco, Ines and Theo. The purpose of this record is to capture what was said so that people who were not in the meeting can understand it.

## Background

A job queue is a component that holds work items until a worker is ready to process them. SQLite is an embedded database that stores everything in a single file, and WAL (write-ahead logging) is a journal mode that lets readers and writers work at the same time. Postgres is a client-server database that many services can share over the network.

## Discussion

Dana opened the meeting by saying the question was whether the sync job queue stays in SQLite or moves to Postgres. Theo then gave a recap of the current setup. `sync-01` hosts the SQLite file and WAL mode was turned on last month. Marco then gave the platform team's position on Postgres. Ines then gave the SRE view. Theo then described the benchmark results. Marco then pointed out a limitation. Dana then summarised.

## Outcome

The queue stays in SQLite with WAL on sync-01. In short, the queue stays in SQLite with WAL on sync-01. Thanks to everyone who took part in the discussion.
