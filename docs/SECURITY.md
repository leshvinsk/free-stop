# Security Policy

The Free Stop maintainers take the security of the project and its users seriously. This policy explains which versions are supported, how to report a vulnerability, and what reporters can expect in return.

## Table of Contents

- [Supported Versions](#supported-versions)
- [Reporting a Vulnerability](#reporting-a-vulnerability)
- [Information to Include](#information-to-include)
- [Response Process](#response-process)
- [Disclosure Policy](#disclosure-policy)
- [Scope](#scope)
- [Safe Harbour](#safe-harbour)
- [Security Controls](#security-controls)
- [Recognition](#recognition)

## Supported Versions

Security fixes are applied to the current production release only.

| Version | Supported |
|---|---|
| Current release on `main` | Yes |
| Unreleased changes on `dev` | Fixed before the next release |
| Earlier releases | No |

## Reporting a Vulnerability

**Security vulnerabilities must not be reported through public issues, discussions or pull requests.**

Please report vulnerabilities privately using GitHub's private vulnerability reporting:

1. Open the [Security tab](https://github.com/leshvinsk/free-stop/security) of the repository.
2. Select **Report a vulnerability**.
3. Complete the advisory form with the information listed below.

If you are unable to use GitHub's reporting feature, send your report by email to **leshvinsk@icloud.com** with the subject line `Security report: Free Stop`.

## Information to Include

To help the maintainers assess and resolve the issue quickly, please provide:

- The type of vulnerability, for example injection, cross site scripting or exposure of sensitive data
- The affected component, file path or endpoint
- The commit, branch or release in which the issue was observed
- Step by step instructions to reproduce the issue
- A proof of concept, where it can be provided safely
- The potential impact, including how an attacker might exploit the issue

## Response Process

| Stage | Target timeframe |
|---|---|
| Acknowledgement of the report | Within 72 hours |
| Initial assessment and severity rating | Within 7 days |
| Fix for a critical or high severity issue | Within 30 days |
| Fix for a medium or low severity issue | In a subsequent scheduled release |

The maintainers keep the reporter informed throughout the process. Fixes are developed in a private fork and released before the advisory is published.

## Disclosure Policy

Free Stop follows coordinated disclosure. Reporters are asked to allow the maintainers a reasonable period, normally up to 90 days, to release a fix before any details are made public. A GitHub security advisory is published once the fix has been deployed.

## Scope

### In Scope

- The Free Stop backend API in `backend/` and its production deployment
- The Free Stop frontend in `frontend/` and its production deployment
- The GitHub Actions workflows in `.github/workflows/`
- The deployment configuration in `applications/`

### Out of Scope

- Vulnerabilities in third party services that Free Stop consumes, including OpenF1, formula1.com and Jolpica, which should be reported to their owners
- Denial of service attacks, including high volume traffic against the hosting environment
- Findings from automated scanners that are submitted without evidence of exploitability
- Social engineering of maintainers or contributors
- Missing security headers or best practice recommendations without a demonstrable impact

## Safe Harbour

Free Stop considers security research carried out in good faith and in accordance with this policy to be authorised. The maintainers will not pursue action against researchers who:

- Make a good faith effort to avoid privacy violations, data destruction and interruption of service
- Access only the minimum data necessary to demonstrate the vulnerability
- Report the vulnerability promptly and do not disclose it publicly before a fix is released
- Do not exploit the vulnerability beyond what is needed to confirm it

## Security Controls

The repository applies the following controls:

| Control | Purpose |
|---|---|
| Protected `main` and `dev` branches | No change is merged without review and passing checks |
| Code owner approval | Every change is approved by a maintainer |
| Least privilege workflow permissions | Workflows receive only the permissions they require, and pull requests from forks run with read only access |
| Approval for first time contributors | Workflows on pull requests from new contributors run only after maintainer approval |
| Dependabot | Vulnerable dependencies are identified and updated automatically |
| Secret scanning and push protection | Credentials are prevented from being committed |
| CodeQL code scanning | Source code is analysed for common vulnerability patterns |

## Recognition

Reporters are credited in the published security advisory unless they request to remain anonymous. The maintainers are grateful to everyone who helps keep Free Stop and its users safe.
