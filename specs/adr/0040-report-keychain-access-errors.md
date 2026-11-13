---
status: accepted
date: 2026-11-13
---

# Report Keychain access errors

## Context and Problem Statement

The macOS Keychain can be locked, and macOS asks again for access when uv upgrades the Python interpreter (technical specifications, section 5). When the user denies access or the Keychain stays locked, `keyring` raises a `KeyringError`. The code did not handle it: tools returned FastMCP's masked generic error, `login` printed a traceback after a successful sign-in, and `logout` reported "Not logged in" with status 0 while the token stayed stored, since the macOS backend raises the same `PasswordDeleteError` for a missing item and for a denied deletion. How should the server and the CLI report a Keychain that cannot be accessed?

## Considered Options

* A dedicated `KeychainError`, raised by every Keychain read, write and deletion
* Fix `logout` only, and let other Keychain errors propagate

## Decision Outcome

Chosen option: "A dedicated `KeychainError`", because the user can act on it: unlocking the Keychain or allowing access fixes every case, and neither a masked error nor a traceback says so.

* `credentials.py` turns every `KeyringError` into `KeychainError`, a `QobuzError`. The server's error conversion and the CLI's error handling therefore report it like the other user-facing errors (FS-BEH-2).
* `delete_credentials` reads the item before deleting it: a missing item is reported as "Not logged in", a failing read or deletion as a `KeychainError`.

The other option was rejected because it leaves the tools with an error that does not tell the user what to do, and `login` with a traceback.

### Consequences

* Good, because the user is told to unlock the Keychain or allow access, from the CLI and from the assistant.
* Good, because `logout` never reports success while the token stays stored.
* Bad, because `logout` reads the Keychain item once more before deleting it.
