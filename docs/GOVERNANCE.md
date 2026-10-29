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
- [Maintainer Setup](#maintainer-setup)
- [Changes to This Document](#changes-to-this-document)

## Principles

- **Transparency.** Decisions are discussed and recorded in public issues, pull requests and discussions.
- **Accuracy.** Free Stop publishes verified data and reproducible scores. Accuracy takes priority over speed.
- **Review.** No change reaches production without review and passing checks. The one exception is the automated team data update, which merges itself only when the frontend checks pass with the new data.
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
| `dev` | `bot/sync-team-data`, opened by the `free-stop-data-sync` App | Frontend checks run against the new data | None | Squash merge | The `free-stop-data-sync` App |
| `main` | `dev` only | Backend checks, Frontend checks | None, as every change was approved on `dev` | Merge commit | Automated release workflow |

Additional rules for both branches:

- Direct pushes, force pushes and branch deletion are blocked.
- Pull requests into `dev` must be rebased on the latest `dev` and must not contain merge commits.
- Approvals are dismissed when new commits are pushed.
- All review conversations must be resolved before merging.
- Release tags matching `v*` may be created, moved or deleted by maintainers only. The `free-stop-data-sync` App may also bypass this rule, and the daily release workflow uses it only to create new tags.
- The `free-stop-data-sync` App is the only bot that may bypass review on `dev`, and only through a pull request. Its private key is held as a repository secret and is never shared with other workflows.

## Decision Making

Routine decisions, such as accepting a defect fix or a data correction, are made by the maintainer through the normal review process.

Significant decisions, such as changes to the scoring methodology, the addition or removal of a season, or changes to this governance model, are proposed in an issue or a discussion and remain open for comment for at least seven days before a decision is made. The maintainer records the decision and its rationale in that thread.

## Release Management

1. Approved pull requests are squash merged into `dev`, which closes their linked issues.
2. The release workflow opens a release pull request from `dev` to `main`, listing every included change, and enables auto-merge on it.
3. Once the checks on `dev` pass, the release pull request merges itself with a merge commit. The maintainer may close or pause it at any time to hold a release.
4. Merging into `main` deploys the change to production.
5. At 00:05 Malaysia time (UTC+8), the daily release workflow publishes everything that reached `main` the previous day as one release and version tag on the [Releases](https://github.com/leshvinsk/free-stop/releases) page. Days without changes produce no release, and a missed run is caught up on the next one.

Versions follow [Semantic Versioning](https://semver.org). A major version marks a change in the scoring methodology that alters published figures, a minor version adds functionality or seasons, and a patch version contains fixes and data corrections. The daily release reads the bump from the day's pull request titles: a `!` after the type is a major version, a `feat` is a minor version, and anything else is a patch. Reviewers must therefore make sure that a pull request which alters published figures carries a `!` before it is merged. The maintainer can override the bump, or release a single day, from the **Daily release** workflow's **Run workflow** button.

## Becoming a Triager or Reviewer

Contributors may be invited to become triagers or reviewers once they have demonstrated:

- A record of accurate, well tested and well documented contributions
- Constructive and respectful participation in reviews and discussions
- Familiarity with the scoring methodology and the project's data standards

Invitations are extended by the maintainer. A role may be withdrawn after an extended period of inactivity or in response to a breach of the [Code of Conduct](CODE_OF_CONDUCT.md).

## Code Ownership

Code ownership is defined in `.github/CODEOWNERS`. A code owner must approve every pull request into `dev`, apart from the automated team data updates described above. Release pull requests into `main` need no further approval, because every change they contain was approved on `dev`. As additional reviewers are appointed, ownership of specific areas, such as the backend scoring pipeline or the frontend, may be delegated to them.

## Maintainer Setup

Some of what keeps Free Stop running lives outside the repository: repository settings, a GitHub App, the hosting accounts and their credentials. This section records all of it, so that the project can be rebuilt from scratch, or handed to another maintainer, without guesswork. Credentials are never written here or anywhere in the repository.

### GitHub Repository Settings

| Setting | Where | Value |
|---|---|---|
| Default branch | Settings, General | `main` |
| Merge methods | Settings, General, Pull Requests | Squash merging and merge commits both allowed, for `dev` and `main` respectively, auto-merge allowed, and head branches deleted automatically after merging |
| Workflow permissions | Settings, Actions, General | Allow GitHub Actions to create and approve pull requests, which the release workflow needs |
| Rulesets | Settings, Rules, Rulesets | Import the three files in `.github/rulesets/`, which are only enforced while the repository is public |
| Labels | Issues, Labels | `bug`, `data`, `data-alert`, `dependencies`, `enhancement` and `triage`, which the issue forms and workflows apply |
| Discussions | Settings, General, Features | Enabled, with an **Ideas** category for the ideas form |
| Security | Settings, Advanced Security | Dependabot alerts and updates, secret protection with push protection, and CodeQL default setup enabled |

### The Automation App

The `free-stop-data-sync` GitHub App is the identity the team data sync and the daily release act as. It is the only bot allowed to bypass review on `dev`, and the only bot allowed to create release tags.

1. Create it from the maintainer's account under **Settings, Developer settings, GitHub Apps, New GitHub App**, with the repository as its homepage, the **Webhook** turned off, and installation limited to this account.
2. Grant only these repository permissions: **Contents** read and write, **Pull requests** read and write, **Commit statuses** read and write, and **Metadata** read-only.
3. Install it on this repository only.
4. Under **Credentials, Key pairs**, create a key. Save the downloaded `.pem` file's full contents as the repository secret `DATA_SYNC_APP_PRIVATE_KEY`, then delete the file.
5. Save the App's **Client ID** as the repository variable `DATA_SYNC_APP_CLIENT_ID`. It is not secret.
6. Add the App to the bypass list of **Protect dev**, set to *For pull requests only*, and of **Protect release tags**, set to *Always allow*.

The ruleset files name the App by its numeric App ID. An App created again from scratch has a new ID, which must be updated in `.github/rulesets/protect-dev.json` and `protect-release-tags.json`.

To rotate the key, create a new one, update the secret, then delete the old key under **Key pairs**.

### Render

1. Create a Blueprint from this repository with the name `free-stop`, the branch `main` and the path `applications/render.yaml`. It creates `free-stop-api` in Frankfurt and the `free-stop-ui` static site.
2. In **free-stop-api, Environment**, set `REDIS_URL` to the Upstash connection string described below.

A Render service cannot move to another region. Changing `region` in the Blueprint means deleting the service and creating the Blueprint again, after which its address stays the same as long as the old service was deleted first.

### Upstash Redis

1. Create a free, regional Redis database in **AWS eu-central-1 (Frankfurt)**, next to the API, with **Eviction** turned on.
2. In the database's **CLI** tab, create the restricted user the API connects as:
   ```text
   ACL SETUSER free-stop-api on ~fs:* -@all +ping +get +getex +setex
   ACL GENTOKEN free-stop-api
   ACL SETUSER free-stop-api resetpass >TOKEN_FROM_GENTOKEN
   ```
3. Set Render's `REDIS_URL` to `rediss://free-stop-api:TOKEN_FROM_GENTOKEN@HOST:6379`. The scheme must be `rediss://`, with two s's, for an encrypted connection. Never use the `default` user, which has full access and is kept for the Upstash console.
4. Turn on multi-factor authentication for the Upstash account.

The API checks the connection when it first needs the cache and logs `Redis connected` or `Redis unavailable`. If the backend ever needs another Redis command, grant it to the user with `ACL SETUSER free-stop-api +<command>` before deploying.

To rotate the token, run `ACL GENTOKEN free-stop-api`, then `ACL SETUSER free-stop-api resetpass >NEW_TOKEN`, then update `REDIS_URL` in Render. To rotate the `default` password, use **Reset password** in the database settings.

### UptimeRobot

Create an **HTTP(s)** monitor for `https://free-stop-api.onrender.com/health` with a 5 minute interval, alerting the maintainer by email. It keeps the API from idling on Render's free tier. The repository's keep warm workflow is a backup.

### After a Rebuild

1. Run **Actions, Sync team data, Run workflow** and confirm the data pull request opens and merges itself.
2. Run **Actions, Daily release, Run workflow** with **dry run** ticked and check the release notes.
3. Open every season and race once, so the cache is filled before visitors arrive. The first pass takes about 20 minutes because of OpenF1's rate limit.

## Changes to This Document

Changes to this document follow the significant decision process described above and are submitted as a pull request.
