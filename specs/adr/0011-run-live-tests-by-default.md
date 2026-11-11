---
status: accepted
date: 2026-11-11
---

# Test with mocks and run live tests by default

## Context and Problem Statement

The main risk of the project is Qobuz changing its unofficial API without notice. What test strategy should the project use?

## Considered Options

* Mocked unit tests, tool tests through the FastMCP in-memory client, and read-only live tests against the real API, run by default
* The same, with live tests opt-in (`pytest -m live`)
* Mocked unit tests only
* No automated tests, manual checks with `fastmcp dev`

## Decision Outcome

Chosen option: "Live tests run by default", because they detect API drift with one command, and running them by default means drift is noticed at every test run.

The other options were rejected for these reasons:

* Opt-in live tests would only run when someone remembers to.
* Mocked tests alone cannot see changes on Qobuz's side.
* With no automated tests, 23 tools make every change risky.

Live tests are skipped, with an explicit reason, when no credentials are available (for example in CI), so they do not fail on a machine that is not logged in. Ruff is used for lint and format.

### Consequences

* Good, because API drift surfaces quickly.
* Bad, because the default run needs network access and credentials. `pytest -m "not live"` covers offline work.
