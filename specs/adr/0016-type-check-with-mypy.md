---
status: accepted
date: 2026-11-11
---

# Type check with mypy

## Context and Problem Statement

The code relies on typed tool signatures and pydantic models, from which FastMCP derives the schemas the model sees. Which type checker should the project use?

## Considered Options

* mypy, strict mode, with the pydantic plugin
* pyright
* ty (Astral)

## Decision Outcome

Chosen option: "mypy, strict mode, with the pydantic plugin", because it is mature, installs as pure Python, and has an official pydantic plugin.

The other options were rejected for these reasons:

* pyright's PyPI package is a wrapper that downloads and runs a Node-based engine, which adds a moving part.
* ty is still in beta (0.0.x), too early to block commits on.

### Consequences

* Good, because type errors are caught before tests run, including in tool signatures.
* Bad, because strict mode demands complete annotations, including in tests.
* Bad, because ty, which is consistent with uv and ruff, may be worth reconsidering once it is stable.
