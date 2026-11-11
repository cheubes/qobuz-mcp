---
status: accepted
date: 2026-11-11
---

# Harden the supply chain

## Context and Problem Statement

A public repository is exposed to supply chain attacks, such as a moved action tag or a compromised dependency, and to permanent leaks: a secret pushed once stays in the history. What safeguards should the project have?

## Considered Options

* Actions pinned by commit SHA, Dependabot updates, gitleaks on the full history, CodeQL, zizmor
* Actions pinned by version tag, with manual updates
* No specific safeguard

## Decision Outcome

Chosen option: "Actions pinned by commit SHA, Dependabot updates, gitleaks, CodeQL, zizmor", because each covers a distinct risk at no cost for a public repository:

* SHA pinning means a moved tag cannot inject code.
* Dependabot keeps pins and dependencies current.
* gitleaks catches secrets before and after they land.
* CodeQL statically analyzes the Python code.
* zizmor audits the workflows themselves.

### Consequences

* Good, because the main supply chain and leak risks are covered automatically.
* Bad, because Dependabot opens weekly pull requests to review.
