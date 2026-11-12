---
status: accepted
date: 2026-11-12
---

# Paginate with `has_more` and an optional `total`

## Context and Problem Statement

`Page[T]` requires a `total`, which every endpoint used so far provides. The current web player endpoints (`discover/*`, `award/*`, `label/*`, `artist/playlists`, `artist/getReleasesList`, `favorite/getNewReleases`, the story lists) paginate with `has_more` and give no total. Some new endpoints also return a fixed list, such as the 30 tracks of a radio. How should list results represent pagination?

## Considered Options

* One `Page` model with `has_more` always set and `total` optional
* A second model, such as `CursorPage`, for the endpoints without a total
* An estimated `total`

## Decision Outcome

Chosen option: "One `Page` model with `has_more` always set and `total` optional", because the assistant follows a single rule, and `has_more` is the signal it actually needs to fetch the next page.

`has_more` comes from Qobuz when it sends it, and is computed as `offset + len(items) < total` otherwise. `total` is `None` when Qobuz does not provide it. A fixed list is one complete page: `total` is its length, `has_more` is `false` and `offset` is 0.

The other options were rejected for these reasons:

* Two pagination models would differ from tool to tool, and a migration would change the output format of an existing tool.
* An estimated total would be an invented value presented as Qobuz data.

### Consequences

* Good, because every list result keeps the same shape.
* Bad, because the assistant can no longer rely on `total` being present: the server instructions and FS-BEH-1 point it to `has_more`.
* Bad, because the existing tests of the `Page` shape are extended to the new field.
