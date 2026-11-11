---
status: accepted
date: 2026-11-11
---

# Use synthetic test fixtures

## Context and Problem Statement

Unit tests need API responses and web player files to run against. In a public repository, real ones would raise three problems:

* The web player bundle is Qobuz's copyrighted code and contains the real `app_id`.
* API responses contain copyrighted editorial texts and biographies.
* A failed anonymization becomes a permanent public leak. gitleaks catches tokens, not playlist names or user IDs.

## Considered Options

* Synthetic fixtures only: hand-written minimal JSON and invented HTML and bundle snippets
* Real responses, trimmed and anonymized by hand
* Real responses, anonymized by a script

## Decision Outcome

Chosen option: "Synthetic fixtures only", because nothing from Qobuz or from the user's account ever enters the repository, and the fixtures stay small and readable.

The other options were rejected for these reasons:

* Hand anonymization keeps all three problems and relies on human vigilance.
* A script adds code to maintain, and any field it misses still leaks.

### Consequences

* Good, because there is no copyright or privacy exposure in the repository.
* Bad, because synthetic fixtures do not follow changes in Qobuz's response format. Live tests cover that (ADR-0011).
