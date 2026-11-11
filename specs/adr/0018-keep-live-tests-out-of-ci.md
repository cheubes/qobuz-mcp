---
status: accepted
date: 2026-11-11
---

# Keep live tests out of CI

## Context and Problem Statement

Live tests detect Qobuz API drift (ADR-0011). Running them in CI would need the real account's token. Should CI run them?

## Considered Options

* No: CI runs `pytest -m "not live"`, and live tests stay local
* Yes: a weekly scheduled job, with the token in a GitHub secret behind a protected environment

## Decision Outcome

Chosen option: "No", because:

* It keeps the real account's token out of GitHub, in a repository meant to become public.
* It avoids repeated API calls from GitHub datacenter IPs, which raise the risk of the account being flagged.
* It respects FS-BEH-3: credentials are stored only in the macOS Keychain.

API drift is still detected locally, since live tests run by default with every local test run.

This decision refines ADR-0011. CI excludes live tests explicitly instead of relying on them being skipped, so CI never touches a Keychain.

### Consequences

* Good, because no credential ever leaves the user's Mac.
* Bad, because drift goes unnoticed while there is no local activity on the project.
