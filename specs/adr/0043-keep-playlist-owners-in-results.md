---
status: accepted
date: 2026-11-14
---

# Keep playlist owners in results

## Context and Problem Statement

FS-BEH-3 forbids account identifiers in tool results, with the login as its only example. `PlaylistSummary` carries the playlist's `owner`, an ID and a name. For the user's own playlists, returned by `list_my_playlists` and by the playlist write tools, the owner is the user. A read-only check on the maintainer's account showed that the owner's `id` is the account's numeric ID, and its `name` is the account's `display_name`, not the login or the email. Qobuz shows the same owner on any public playlist of the user, to every other user. Without a filter, `list_my_playlists` mixes owned and followed playlists, and the owner is what tells them apart. Is a playlist's owner an account identifier?

## Considered Options

* Keep the owner, and define account identifiers in FS-BEH-3
* Replace the owner of the user's own playlists by an `is_owned` flag
* Drop the owner's ID from every playlist, and keep its name

## Decision Outcome

Chosen option: "Keep the owner, and define account identifiers", because the owner is public catalog data, the same for the user's playlists as for anyone else's, and the assistant needs it to tell owned from followed playlists.

* FS-BEH-3 defines account identifiers as the login, the email and the other private fields of the user's profile, which some endpoints return alongside the requested data. They stay excluded from results, as in `check_library` (AC-LIB-08).
* A playlist's owner, its public ID and display name, is catalog data, kept for every playlist, the user's own included.

The other options were rejected for these reasons:

* An `is_owned` flag needs the user's ID on the server side, from one more `user/get` call per tool call or from storage, to hide data Qobuz shows publicly.
* Owner names are not unique: without the ID, owned and followed playlists cannot be told apart reliably.

### Consequences

* Good, because results and FS-BEH-3 agree, with no change to the code.
* Bad, because the user's numeric account ID and display name reach the assistant's context, as they would on any public playlist page.
