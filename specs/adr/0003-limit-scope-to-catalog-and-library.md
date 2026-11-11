---
status: accepted
date: 2026-11-10
---

# Limit the scope to catalog and library

## Context and Problem Statement

Besides catalog and library features, the server could control playback in the Qobuz desktop app on the Mac. The desktop app has no AppleScript dictionary (checked with `sdef` on version 8.3.0) and does not appear in the macOS Now Playing widget. What should the scope be?

## Considered Options

* Catalog and library only: search, browse, favorites, playlists
* Playback control only
* Both, starting with catalog and library

## Decision Outcome

Chosen option: "Catalog and library only", because playback control relies on the least stable building blocks:

* Qobuz Connect is a proprietary protocol, only available through reverse-engineered implementations in alpha (qonductor, qconnect, QBZ).
* Simulated media keys need the Accessibility permission and give no state feedback.
* `qobuzapp://` deep links only open content in the app, without guaranteed playback.

### Consequences

* Good, because everything goes through one REST API, which keeps the server simple.
* Bad, because the assistant cannot start playback or see what is playing.

### More Information

A read-only "now playing" feature looks cheap to add later: another project reads a player state file written by the desktop app.
