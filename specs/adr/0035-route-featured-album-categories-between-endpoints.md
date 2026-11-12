---
status: accepted
date: 2026-11-12
---

# Route featured album categories between `discover/*` and `album/getFeatured`

## Context and Problem Statement

`list_featured_albums` uses `album/getFeatured`, which the current web player no longer calls, with 15 categories. The web player uses one `discover/*` endpoint per category, but only for six of them: new releases, Qobuzissimes, ideal discography, most streamed, press awards, and album of the week, which `album/getFeatured` does not offer. Should the tool move to `discover/*`?

## Considered Options

* Route each category: `discover/*` for the categories it covers, `album/getFeatured` for the others
* Migrate entirely to `discover/*`
* Keep `album/getFeatured` only, and add album of the week through `discover/albumOfTheWeek`

## Decision Outcome

Chosen option: "Route each category", because the categories the web player uses rest on endpoints in active use, and the ten others keep working.

| Category | Endpoint |
|---|---|
| `new-releases` | `discover/newReleases` |
| `qobuzissims` | `discover/qobuzissims` |
| `ideal-discography` | `discover/idealDiscography` |
| `most-streamed` | `discover/mostStreamed` |
| `press-awards` | `discover/pressAward` |
| `album-of-the-week` (new) | `discover/albumOfTheWeek` |
| The other ten | `album/getFeatured`, unchanged |

All accept `genre_ids`, `limit` and `offset`.

The other options were rejected for these reasons:

* A full migration would drop ten categories that work today, such as best sellers and editor picks.
* Keeping `album/getFeatured` leaves the most used categories on an endpoint the official client no longer uses.

### Consequences

* Good, because the main categories rest on endpoints in active use, and the tool gains album of the week.
* Bad, because the tool depends on two endpoint families, with two album formats to map.
* Bad, because pagination differs by category: `total` is present for `album/getFeatured` only (ADR-0032).
