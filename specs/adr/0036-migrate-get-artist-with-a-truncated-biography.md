---
status: accepted
date: 2026-11-12
---

# Migrate `get_artist` to `artist/page`, with a truncated biography

## Context and Problem Statement

`get_artist` uses `artist/get` with `extra=albums`, which the current web player no longer calls. It returns Qobuz's biography summary by default, and the full biography on request. The web player uses `artist/page` for the artist and `artist/getReleasesList` for a paginated discography, filtered by release type. `artist/page` has no biography summary: only the full text, in simple HTML (`<p>`, `<br>`, `<em>`), up to about 12,000 characters. Should the tool move, and how should it keep the default result short?

## Considered Options

* Migrate, and truncate the biography by default
* Migrate, and drop the default biography
* Keep `artist/get`

## Decision Outcome

Chosen option: "Migrate, and truncate the biography by default", because the tool rests on endpoints in active use and gains a release type filter, while its default result stays short.

* `biography` holds, by default, the longest prefix of Qobuz's text of at most 1,000 characters that ends at a sentence end (`.`, `!` or `?`), or at the last whitespace when no sentence end fits. `biography_truncated` states whether text was cut.
* With `full_biography` set, `biography` holds the full text and `biography_truncated` is `false`.
* The text is never rewritten: the excerpt is an exact prefix of Qobuz's text. This is the only exception to the rule that third-party text is returned unmodified (FS-BEH-4), and it removes text, never adds any.
* The discography comes from `artist/getReleasesList`, with an optional `release_type` filter.

The other options were rejected for these reasons:

* Dropping the default biography would force a second call, and the full text, for the most common question about an artist.
* Keeping `artist/get` leaves the tool exposed to the removal of an endpoint the official client no longer uses.

### Consequences

* Good, because the default result stays short, and the full text remains one parameter away.
* Good, because the discography can be filtered by release type.
* Bad, because the excerpt is the start of the biography, not an editorial summary.
* Bad, because each call makes two requests instead of one, and `albums_count` is no longer provided.
* Bad, because the discography gives no total: pagination relies on `has_more` (ADR-0032).
