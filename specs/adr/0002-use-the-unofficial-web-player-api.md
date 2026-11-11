---
status: accepted
date: 2026-11-10
---

# Use the unofficial Qobuz web player API

## Context and Problem Statement

Qobuz has no public API. Access is granted only to professional partners, and Qobuz has explicitly declined open source integrations, citing its licensing agreements with major labels. How can a personal MCP server reach Qobuz data at all?

## Considered Options

* Official partner access
* A third-party aggregator holding Qobuz credentials (such as MusicAPI)
* The unofficial REST API used by the Qobuz web player

## Decision Outcome

Chosen option: "The unofficial REST API used by the Qobuz web player", because partner access is not available for a personal project, and an aggregator would route the user's library data through a third party.

### Consequences

* Good, because it covers the whole functional scope: catalog, favorites, playlists, purchases.
* Bad, because it is outside Qobuz's terms of service. Use is strictly personal.
* Bad, because the API and the `app_id` can change without notice. Live tests are the early warning (ADR-0011).
* Bad, because the account could in theory be blocked.
