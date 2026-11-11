---
status: accepted
date: 2026-11-11
---

# Read credentials at each tool call

## Context and Problem Statement

`login` and `logout` must take effect without restarting the MCP client (FS-SETUP-2). When should the server read the Keychain?

## Considered Options

* Once at startup
* On first use, with an in-memory cache cleared on authentication errors
* At each tool call

## Decision Outcome

Chosen option: "At each tool call", because it is the only option where both `login` and `logout` take effect immediately.

The other options were rejected for these reasons:

* Reading once at startup keeps an expired token until the client restarts.
* A cache cleared on authentication errors keeps using the token after `logout`, since logging out does not revoke the token on Qobuz's side.

### Consequences

* Good, because it is the simplest option and always matches the Keychain.
* Bad, because it adds one Keychain read per call, which costs a few milliseconds.
