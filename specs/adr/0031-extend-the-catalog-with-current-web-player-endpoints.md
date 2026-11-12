---
status: accepted
date: 2026-11-12
---

# Extend the catalog with the current web player endpoints

## Context and Problem Statement

The first tool catalog was built from the endpoints found during the proof of concept. A static analysis of the current web player bundle lists about 70 API endpoints, against 25 used by the server. Several of them fall within the scope of ADR-0003: recommendations, new releases from favorite artists, awards, magazine stories, artist and label sections, and the library status of given items. Read-only probes on the maintainer's account confirmed their parameters and response structures.

Which of them should become tools, and how should they be grouped?

## Considered Options

* One tool per user intent, with a type parameter when results are of the same nature, as `list_favorites` and `search_catalog` already do
* One tool per endpoint
* A few generic tools, such as a single `get_editorial(kind)`

## Decision Outcome

Chosen option: "One tool per user intent", because it adds 11 tools instead of about 25, keeps each tool's description specific enough to guide the model, and follows the convention already in place.

The other options were rejected for these reasons:

* One tool per endpoint would bring the catalog to about 48 tools, with near-identical pairs, such as four label tools. The model chooses less reliably in a long catalog, and every tool adds to the context of each conversation.
* Generic tools would need huge enumerations and heterogeneous outputs, with descriptions too vague to guide the model.

Endpoints that duplicate existing tools do not become tools: they are migration targets for those tools, decided one by one (ADR-0033 to ADR-0036).

Endpoints left out:

* `user/lastUpdate`: the web player uses it to invalidate its cache. It is of no use to an assistant.
* `favorite/getUserFavoriteIds` and `purchase/getUserPurchasesIds` as raw lists: `check_library` answers the useful question, whether given items are in the library, instead of returning thousands of IDs. The purchase endpoint also returns the account's login, which never reaches a result.
* The full text of a story: the web player fetches it from a third-party host, Arc XP (`qobuz-qobuz-prod.web.arc-cdn.net`), while FS-BEH-3 limits requests to Qobuz hosts. Story lists and summaries come from the Qobuz API and are kept.
* `label/explore`: it returns 25 labels whatever the `limit`, and its `offset` does not shift the list. It cannot be paginated as FS-BEH-1 requires.
* `award/getPlaylists`: it returned no playlist for the awards observed. It can be added once observed.
* `magazine/search`: a web player route, not an API endpoint.

The new tools are listed in the tool catalog before their code, marked `(planned)` after their name. A marked tool is specified but not exposed yet, and the AC-BEH-01 test ignores it. The pull request that implements a tool removes its marker.

`dynamic/suggest`, behind `suggest_tracks`, is a `POST` with a JSON body, but it only reads: it is annotated `read-only`. Since the live test guard blocks every `POST`, `suggest_tracks` has no live test.

### Consequences

* Good, because the assistant gains recommendations, editorial content and library checks with a moderate catalog growth.
* Good, because every new tool is read-only: no new write path, and the safeguards of ADR-0025 are unchanged.
* Bad, because the new endpoints are unofficial like the others, and some were observed only once.
* Bad, because one read tool, `suggest_tracks`, uses a `POST` and is only covered by mocked tests.
