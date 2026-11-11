---
status: accepted
date: 2026-11-11
---

# Record decisions with MADR

## Context and Problem Statement

Design decisions and the alternatives they rejected were only discussed in conversation. Without a written record, the rationale is lost between sessions and settled questions get reopened.

## Considered Options

* One Markdown file per decision, following MADR 4, in `specs/adr/`
* A single append-only `specs/decisions.md` log
* A "Why" line next to each choice in the specifications

## Decision Outcome

Chosen option: "One Markdown file per decision, following MADR 4", because it is the standard format for architecture decision records and gives each decision its own history.

### Consequences

* Good, because every decision states its context, the options considered and why they were rejected.
* Good, because a revised decision gets a new record, and the old one is marked `superseded by ADR-NNNN` instead of being edited away.
* Bad, because it means more files than a single log for a project of this size.
