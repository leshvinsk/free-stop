# Governance

This document describes how the Free Stop project is organised, who is responsible for which decisions, and how changes are approved and released.

## Table of Contents

- [Principles](#principles)
- [Roles and Responsibilities](#roles-and-responsibilities)
- [Approval and Merge Rules](#approval-and-merge-rules)
- [Decision Making](#decision-making)
- [Release Management](#release-management)
- [Becoming a Triager or Reviewer](#becoming-a-triager-or-reviewer)
- [Code Ownership](#code-ownership)
- [Changes to This Document](#changes-to-this-document)

## Principles

- **Transparency.** Decisions are discussed and recorded in public issues, pull requests and discussions.
- **Accuracy.** Free Stop publishes verified data and reproducible scores. Accuracy takes priority over speed.
- **Review.** No change reaches production without review and passing checks.
- **Openness.** Anyone may contribute, and responsibility is extended to contributors who demonstrate sustained, constructive participation.

## Roles and Responsibilities

| Role | Responsibilities | Repository permission |
|---|---|---|
| Contributor | Opens issues and discussions, submits pull requests from a fork, and responds to review | None. Contributes through forks |
| Triager | Labels, assigns and deduplicates issues, moderates discussions, and helps new contributors | Triage |
| Reviewer | Reviews pull requests and recommends approval or changes | Write, with no ability to bypass branch protection |
| Maintainer | Sets project direction, approves and merges pull requests, manages releases, and enforces the Code of Conduct | Admin |

The current maintainer is [@leshvinsk](https://github.com/leshvinsk).

## Approval and Merge Rules

| Target branch | Accepted source | Required checks | Required approvals | Merge method | Merged by |
|---|---|---|---|---|---|
| `dev` | Contributor branches named `<type>/<issue>-<description>` | Backend checks, Frontend checks, PR policy | One code owner approval | Squash merge | Maintainer |
| `main` | `dev` only | Backend checks, Frontend checks | One code owner approval | Merge commit | Maintainer |

Additional rules for both branches:

- Direct pushes, force pushes and branch deletion are blocked.
- Approvals are dismissed when new commits are pushed.
- All review conversations must be resolved before merging.
- Release tags matching `v*` may be created, moved or deleted by maintainers only.

## Decision Making

Routine decisions, such as accepting a defect fix or a data correction, are made by the maintainer through the normal review process.

Significant decisions, such as changes to the scoring methodology, the addition or removal of a season, or changes to this governance model, are proposed in an issue or a discussion and remain open for comment for at least seven days before a decision is made. The maintainer records the decision and its rationale in that thread.

## Release Management

1. Approved pull requests are squash merged into `dev`.
2. An automated workflow opens and maintains a release pull request from `dev` to `main`, listing every included change.
3. The maintainer reviews the release pull request, confirms that all checks pass, and merges it with a merge commit.
4. Merging into `main` deploys the release to production.
5. The maintainer publishes release notes and a version tag on the [Releases](https://github.com/leshvinsk/free-stop/releases) page.

Versions follow [Semantic Versioning](https://semver.org). A major version marks a change in the scoring methodology that alters published figures, a minor version adds functionality or seasons, and a patch version contains fixes and data corrections.

## Becoming a Triager or Reviewer

Contributors may be invited to become triagers or reviewers once they have demonstrated:

- A record of accurate, well tested and well documented contributions
- Constructive and respectful participation in reviews and discussions
- Familiarity with the scoring methodology and the project's data standards

Invitations are extended by the maintainer. A role may be withdrawn after an extended period of inactivity or in response to a breach of the [Code of Conduct](CODE_OF_CONDUCT.md).

## Code Ownership

Code ownership is defined in `.github/CODEOWNERS`. A code owner must approve every pull request into `dev` and `main`. As additional reviewers are appointed, ownership of specific areas, such as the backend scoring pipeline or the frontend, may be delegated to them.

## Changes to This Document

Changes to this document follow the significant decision process described above and are submitted as a pull request.
