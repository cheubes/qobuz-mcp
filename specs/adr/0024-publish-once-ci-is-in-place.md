---
status: accepted
date: 2026-11-11
---

# Publish once CI is in place

## Context and Problem Statement

The repository is meant to become public quickly. When should it switch to public, and how should it be configured?

## Considered Options

* After the project scaffold and CI (implementation plan, "Publication" step)
* Now, with specifications only
* After the first usable version, with read tools

## Decision Outcome

Chosen option: "After the project scaffold and CI", because the CI, secret scanning, CodeQL and branch rules are then active before the first real code is committed, so everything public has been checked.

The other options were rejected for these reasons:

* Publishing now leaves the repository public for a while without CI or protection.
* Waiting for a usable version delays a publication meant to be quick.

At publication, the repository is configured to limit exposure:

* Squash merge only.
* A ruleset on `main`: pull requests with passing CI, no force push, admin bypass.
* Secret scanning with push protection.
* Private vulnerability reporting.
* Only the actions in use are allowed, and `GITHUB_TOKEN` is read-only by default.

### Consequences

* Good, because nothing reaches the public repository without the full set of checks.
* Bad, because the first public README states that the server is not usable yet.
