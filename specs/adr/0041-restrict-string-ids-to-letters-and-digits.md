---
status: accepted
date: 2026-11-13
---

# Restrict string IDs to letters and digits

## Context and Problem Statement

Album IDs are strings, while all other IDs are integers (technical specifications, section 10). Tools accepted any non-empty string as an album ID, and the API client sends lists comma-separated, as the web player does. An album ID such as `"111,222"` passed to `remove_favorites` therefore reached Qobuz as two IDs: a single write could affect more items than its arguments show, which an injected instruction could exploit (ADR-0025). `get_radio` and `list_related_stories` also take a string ID, an album ID or another ID in digits. Album IDs observed in the catalog are 13-digit codes or 13 lowercase letters and digits. Which string IDs should be validated, and how?

## Considered Options

* Letters and digits only, for every string ID parameter
* Letters and digits only, for the write tools only

## Decision Outcome

Chosen option: "Letters and digits only, for every string ID parameter", because one rule for one kind of ID is simpler to read and to test, and a malformed ID is a mistake in a read as much as in a write.

* String ID parameters match `^[0-9A-Za-z]+$`: album IDs in every tool, `seed_id` of `get_radio` and `entity_id` of `list_related_stories`. A malformed ID is rejected with a validation error, before any request is sent to Qobuz.
* The pattern does not restrict case or length, which Qobuz does not document.

The other option was rejected because it leaves two rules for the same kind of ID, and read tools would keep sending malformed IDs to Qobuz.

### Consequences

* Good, because no write can reach more items than its arguments list.
* Bad, because an album ID format Qobuz introduces with other characters would be rejected until the pattern is updated.
