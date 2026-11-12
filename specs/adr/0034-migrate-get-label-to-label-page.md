---
status: accepted
date: 2026-11-12
---

# Migrate `get_label` to `label/page`

## Context and Problem Statement

`get_label` uses `label/get` with `extra=albums`, which the current web player no longer calls. The web player builds a label page from `label/page`, for the label itself, and `label/getAlbums`, for its paginated albums, which also accepts `genre_ids`. Should the tool move to them?

## Considered Options

* Migrate to `label/page` and `label/getAlbums`
* Keep `label/get`

## Decision Outcome

Chosen option: "Migrate to `label/page` and `label/getAlbums`", because they provide every field of `LabelDetail`, and are the endpoints the official client relies on.

`label/page` gives the name and description. Its album groups are not paginated, so the albums come from `label/getAlbums`. The tool makes both calls. The genre filter of `label/getAlbums` is not exposed: no need for it has been identified.

Keeping `label/get` was rejected: it leaves the tool exposed to the removal of an endpoint the official client no longer uses.

### Consequences

* Good, because the tool rests on endpoints in active use, with an unchanged result.
* Bad, because each call makes two requests instead of one.
* Bad, because `label/getAlbums` gives no total: pagination relies on `has_more` (ADR-0032).
