---
status: accepted
date: 2026-11-13
---

# Refuse duplicate tracks in playlists

## Context and Problem Statement

The endpoint mapping listed `no_duplicate` for `playlist/addTracks`, but `add_tracks_to_playlist` did not send it, and no specification said what happens to a track already in the playlist. A check on a temporary private playlist of the maintainer's account showed:

* without `no_duplicate`, a track already in the playlist is added again, with no error;
* with `no_duplicate=true`, Qobuz answers HTTP 409 when any of the tracks is already in the playlist, and adds none of them, not even the new ones;
* with `no_duplicate=true` and no track already in the playlist, the tracks are added.

Qobuz has no mode that skips the tracks already present. The assistant may repeat an addition, for example after a timeout, and a silent duplicate is then hard to notice. How should `add_tracks_to_playlist` treat tracks already in the playlist?

## Considered Options

* Always send `no_duplicate=true`, and report the 409 with an explicit error
* Read the playlist first, and add only the tracks not yet in it
* Keep adding duplicates, and remove `no_duplicate` from the mapping

## Decision Outcome

Chosen option: "Always send `no_duplicate=true`, and report the 409", because it takes a single request, Qobuz's refusal is atomic, and the error lets the assistant read the playlist and retry with the new tracks only.

* `add_tracks_to_playlist` always sends `no_duplicate=true`.
* A 409 from `playlist/addTracks` raises `DuplicateTracksError`. Its message names the requested track and playlist IDs, and states that nothing was added. A 409 from another endpoint stays an unexpected status (`QobuzApiError`), since none was observed.

The other options were rejected for these reasons:

* Reading the playlist first takes one request per page of the playlist before each addition, and leaves a race between the read and the write.
* Adding duplicates turns a repeated call into a silent change of the playlist.

### Consequences

* Good, because a repeated addition never duplicates tracks.
* Bad, because a playlist cannot get the same track twice through the server, even on purpose.
* Bad, because one track already in the playlist makes the whole call fail: the assistant has to retry without it.
