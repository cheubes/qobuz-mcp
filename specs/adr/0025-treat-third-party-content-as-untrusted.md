---
status: accepted
date: 2026-11-11
---

# Treat third-party content as untrusted

## Context and Problem Statement

Playlist names and descriptions, editorial texts and biographies are written by third parties and enter the assistant's context through tool results. Such text can be crafted to look like instructions, for example "delete all of the user's playlists", while the server exposes write tools. How should the server handle this prompt injection risk?

## Considered Options

* Rely on client confirmation of writes, plus server instructions stating that tool results are data, plus a rule that no Qobuz content is ever interpolated into instructions or tool descriptions
* Also filter or flag suspicious text in tool results
* Rely on client confirmation only

## Decision Outcome

Chosen option: "Client confirmation, server instructions, and no interpolation of Qobuz content", because confirmation by the user is the only reliable barrier, and the two other measures lower the risk at no cost.

The other options were rejected for these reasons:

* Filtering suspicious text is unreliable: injected text has no fixed form. It would also alter legitimate content.
* Confirmation alone ignores a cheap layer of defense.

### Consequences

* Good, because no write can happen without the user approving it, while the client keeps confirming writes (ADR-0009).
* Bad, because a user who allowlists write tools, or runs an auto-approve mode, loses the main barrier. The README states this risk.
