---
status: accepted
date: 2026-11-10
---

# Authenticate with a one-time login command

## Context and Problem Statement

Every API call needs a user auth token. How does the user obtain it, and where is it stored?

## Considered Options

* A `login` command that exchanges email and password for a token and stores only the token in the macOS Keychain, with a `login --token` fallback
* A token copied by hand from the web player
* Reusing the Keychain entry written by `qobuz-cli`

## Decision Outcome

Chosen option: "A `login` command with a `login --token` fallback", because it is a one-time step, the password is never stored, and the fallback covers the case where Qobuz blocks API login.

### Consequences

* Good, because credentials live only in the Keychain.
* Good, because the server does not depend on a third-party tool.
* Bad, because API login may be blocked by a captcha (FS Q1). `login --token` would then become the main path.
