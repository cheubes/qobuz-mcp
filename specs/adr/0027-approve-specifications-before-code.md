---
status: accepted
date: 2026-11-11
---

# Approve specifications before code

## Context and Problem Statement

The specifications are drafts, and some of their content depends on facts the proof of concept will establish: open questions, endpoints, output models. When may production code be written?

## Considered Options

* Specifications move from `draft` to `approved` once the proof of concept and the output models are done. No production code before that
* Code may start in parallel with the proof of concept
* No formal status

## Decision Outcome

Chosen option: "Approve specifications before code", because code written against unvalidated assumptions, such as API login or the reordering endpoint, would likely be rewritten.

The other options were rejected for these reasons:

* Coding in parallel risks building on assumptions the proof of concept overturns.
* Without a formal status, nothing marks when the specifications can be relied on.

After approval, specifications keep evolving through the usual process: specification update, plus an ADR when a decision changes. Their status stays `approved`.

### Consequences

* Good, because code starts from validated specifications.
* Bad, because nothing usable exists before the proof of concept and the output models are done.
