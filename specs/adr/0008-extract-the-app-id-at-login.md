---
status: accepted
date: 2026-11-10
---

# Extract the app_id at login

## Context and Problem Statement

The `app_id` is shared by all web player users, is not a personal secret, and can change at any time. How does the server get it?

## Considered Options

* Extract it from the web player bundle during `login`, with a `QOBUZ_APP_ID` override
* Manual configuration only
* Automatic re-extraction whenever an API error shows it is invalid

## Decision Outcome

Chosen option: "Extract it during `login`, with a `QOBUZ_APP_ID` override", because the normal case needs no manual step, and re-running `login` handles a rotation.

The other options were rejected for these reasons:

* Manual configuration makes the user dig the value out of the web player's code.
* Re-extracting on every invalid `app_id` error adds retry logic for a rare case.

### Consequences

* Good, because it needs no manual step in the normal case.
* Bad, because extraction relies on the bundle's structure. The override and a live test (AC-LIVE-01) cover breakage.
