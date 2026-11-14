---
status: accepted
date: 2026-11-14
---

# Report unknown purchases on incomplete lists

## Context and Problem Statement

`check_library` reads the user's purchased IDs from `purchase/getUserPurchasesIds`, which returns them under `albums.items` and `tracks.items`, each with a `total`. Whether this endpoint paginates, and which parameters it would take, was never observed: the maintainer's account has no purchase. The code ignored `total`, so if Qobuz returned only part of the purchases, an album or track bought but missing from the list was reported as `purchased: false`. How should `check_library` treat a list with fewer IDs than its `total`?

## Considered Options

* Report `purchased: null` for an item missing from an incomplete list
* Request further pages with `limit` and `offset` until the list is complete
* Keep the current behavior, and record the limitation

## Decision Outcome

Chosen option: "Report `purchased: null` for an item missing from an incomplete list", because it never states a false answer, adds no request, and relies only on the `total` Qobuz already returns.

* A group of purchases is incomplete when its `total` is an integer greater than the number of items received.
* For an incomplete group, a listed item stays `purchased: true`, and an item missing from the list gets `purchased: null`, meaning unknown. A complete group keeps `true` and `false`.

The other options were rejected for these reasons:

* Paginating relies on parameters the endpoint was never seen to accept, and the loop could not be checked against a real account.
* Keeping the current behavior leaves a possible false `false` on an account with many purchases.

### Consequences

* Good, because `check_library` never reports an album or track as not purchased without knowing it.
* Bad, because `purchased: null` now means either "cannot be purchased" (artists) or "unknown", which the tool description has to state.
