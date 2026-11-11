---
status: accepted
date: 2026-11-11
---

# Log in through the Qobuz OAuth browser flow

## Context and Problem Statement

ADR-0007 chose a `login` command exchanging email and password through `user/login`, with `login --token` as a fallback. During the proof of concept, `user/login` returned 401 "User authentication is required" for valid credentials, with every parameter variant. Community reports say Qobuz moved sign-in to an OAuth flow protected by reCAPTCHA around April 2026.

The web player bundle shows that flow:

1. The browser opens `www.qobuz.com/signin/oauth` with `ext_app_id` and `redirect_url`.
2. Qobuz redirects to that URL with `code_autorisation`.
3. `oauth/callback` exchanges the code, together with a private key held in the bundle, for a token.

A test with `http://127.0.0.1:<port>/callback` as redirect succeeded and returned a working token.

## Considered Options

* OAuth browser flow with a local callback server, keeping `login --token` as a fallback
* `login --token` only, with the token copied by hand from the browser's developer tools
* Reading the token from the browser's or the desktop app's local storage

## Decision Outcome

Chosen option: "OAuth browser flow with a local callback server, keeping `login --token` as a fallback", because it gives a one-step login on Qobuz's own page, the CLI never sees the password, and it worked against the real account.

The other options were rejected for these reasons:

* A manual token only means digging into developer tools at every expiry.
* Reading another application's storage is fragile and intrusive.

This decision supersedes ADR-0007.

### Consequences

* Good, because the password never goes through the CLI, and reCAPTCHA is handled by the user in the browser.
* Good, because the fallback still works if the flow changes: `user/get` validates a pasted token.
* Bad, because login now depends on a second value extracted from the bundle (the private key), and on Qobuz keeping accepting a local redirect.
* Bad, because the flow has no `state` parameter. A random path segment in the callback URL replaces it.
