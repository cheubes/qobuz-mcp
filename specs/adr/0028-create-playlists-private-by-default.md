---
status: accepted
date: 2026-11-11
---

# Create playlists private by default

## Context and Problem Statement

`create_playlist` takes `is_public` and `is_collaborative`. When the assistant does not set them, what should the playlist be?

## Considered Options

* Private and non-collaborative, sent explicitly
* Whatever Qobuz defaults to when the fields are omitted

## Decision Outcome

Chosen option: "Private and non-collaborative, sent explicitly", because a playlist made by the assistant should not become public without the user asking for it, and Qobuz's own defaults are unknown and could change.

### Consequences

* Good, because nothing is published by accident.
* Bad, because making a playlist public takes an explicit request.
