---
status: accepted
date: 2026-11-12
---

# Migrate featured playlists to `discover/playlists`

## Context and Problem Statement

`list_featured_playlists` uses `playlist/getFeatured`, which the current web player no longer calls. Endpoints the official client has dropped may be removed without notice. The web player now uses `discover/playlists`, which accepts `genre_ids` and a `tags` filter whose values come from `playlist/getTags`. Should the tool move to it?

## Considered Options

* Migrate to `discover/playlists`, and add a `tag` filter
* Keep `playlist/getFeatured`

## Decision Outcome

Chosen option: "Migrate to `discover/playlists`", because it covers the same editorial playlists, adds a filter by tag, and is the endpoint the official client relies on.

The accepted tags are the 13 slugs returned by `playlist/getTags` when observed: `hi-res`, `new`, `focus`, `mood`, `artist`, `danslecasque`, `label`, `qobuzdigs`, `event`, `auditoriums`, `speakers`, `ideal-discography`, `popular`. They are written in the specification, not read at run time, so no Qobuz text reaches the tool description (FS-BEH-4).

Keeping `playlist/getFeatured` was rejected: it leaves the tool exposed to the removal of an endpoint the official client no longer uses, for no benefit.

### Consequences

* Good, because the tool rests on an endpoint in active use, and gains a tag filter.
* Bad, because `discover/playlists` gives no total: pagination relies on `has_more` (ADR-0032).
* Bad, because the tag list may drift from Qobuz's: an unknown tag is rejected by the tool until the specification is updated.
