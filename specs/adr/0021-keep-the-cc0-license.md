---
status: accepted
date: 2026-11-11
---

# Keep the CC0 license

## Context and Problem Statement

The repository is licensed under CC0 1.0 Universal and is about to become public. Should it keep CC0 or switch to a conventional open source license?

## Considered Options

* Keep CC0 1.0
* MIT
* Apache 2.0

## Decision Outcome

Chosen option: "Keep CC0 1.0", the author's choice: the code is dedicated to the public domain.

### Consequences

* Good, because it is the most permissive option: anyone may reuse the code without conditions.
* Bad, because CC0 is not approved by the Open Source Initiative and explicitly excludes patent rights. Some organizations do not accept CC0 dependencies.
* Bad, because CC0's warranty disclaimer is shorter than MIT's or Apache's. The README states explicitly that the project comes with no guarantee and relies on an unofficial API.
