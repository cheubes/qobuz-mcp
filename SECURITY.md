# Security policy

## Reporting a vulnerability

Report vulnerabilities through [GitHub private vulnerability reporting](https://github.com/cheubes/qobuz-mcp/security/advisories/new). Never report them in a public issue, and never include a working token or real account data in a report.

## Scope

In scope:

- Handling of credentials: the Qobuz token, the authorization code during login, the macOS Keychain item.
- Leaks of tokens or personal data, in tool results, logs, error messages, CLI output or the repository.
- Unsafe writes to the user's Qobuz account, including writes triggered by instructions injected in third-party content, such as playlist descriptions or editorial texts.

Out of scope:

- The Qobuz API itself, and vulnerabilities in Qobuz's own services. Report those to Qobuz.
- Risks the README already states, such as allowlisting write tools in the MCP client.

## Supported versions

Only the latest commit on `main` is supported.

## Response

This is a personal project maintained on a best-effort basis. Reports are read and handled as soon as possible, without a committed response time.
