# Security Policy

## Supported versions

Only the latest release, deployed from `main`, receives security fixes.

| Version | Supported |
|---|---|
| Latest (`main`) | Yes |
| Older releases | No |

## Reporting a vulnerability

**Please do not report security vulnerabilities through public issues, discussions or pull requests.**

Report them privately through GitHub:

1. Go to the [Security tab](https://github.com/leshvinsk/free-stop/security) of this repository.
2. Click **Report a vulnerability**.
3. Describe the issue, the steps to reproduce it and the impact you expect.

You will receive an acknowledgement within 72 hours. Once the issue is confirmed, a fix is prepared in a private fork and released before the advisory is published. Reporters are credited in the advisory unless they ask not to be.

## Scope

In scope:

- The Free Stop API (`backend/`) and its deployed instance
- The Free Stop frontend (`frontend/`) and its deployed instance
- The GitHub Actions workflows in `.github/workflows/`

Out of scope:

- Vulnerabilities in third-party services Free Stop reads from (OpenF1, formula1.com, Jolpica). Report those to their owners.
- Denial of service through high request volume against the free-tier hosting.
