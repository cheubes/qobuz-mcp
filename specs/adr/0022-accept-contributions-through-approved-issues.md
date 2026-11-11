---
status: accepted
date: 2026-11-11
---

# Accept contributions through approved issues

## Context and Problem Statement

The repository is about to become public, with a single maintainer and an unofficial API that can break at any time. Which contributions should it accept, and how?

## Considered Options

* Open but framed: issues open with templates, pull requests accepted only when linked to an issue the maintainer has approved
* Fully open: issues and pull requests without conditions
* Closed: bug reports only, no pull requests

## Decision Outcome

Chosen option: "Open but framed", because it keeps useful contributions possible, such as fixes after an API change, while filtering unsolicited changes.

The other options were rejected for these reasons:

* A fully open policy invites pull requests that ignore the specifications.
* A closed policy turns away useful help.

The policy has four parts:

* Two issue templates: bug report and feature request.
* A pull request template that asks for the linked issue, the specification and ADR updates, and the acceptance criteria covered.
* `CONTRIBUTING.md` describes the spec-driven workflow: specification, ADR and acceptance criteria first, then code.
* `main` requires passing CI before merge, without required reviews, since the sole maintainer cannot approve their own pull requests.

### Consequences

* Good, because contributors follow the same discipline as the project.
* Bad, because the entry barrier is higher for small fixes.
