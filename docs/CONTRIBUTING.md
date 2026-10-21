# Contributing to Free Stop

Thank you for your interest in contributing to Free Stop. This guide explains how contributions are proposed, developed, reviewed and released. Following it ensures that every change is traceable, reviewed and safe to deploy.

All participants are expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md). The roles and approval rules referred to in this guide are defined in [GOVERNANCE.md](GOVERNANCE.md).

## Table of Contents

- [Overview](#overview)
- [Ways to Contribute](#ways-to-contribute)
- [Access Model](#access-model)
- [Branching Model](#branching-model)
- [Contribution Workflow](#contribution-workflow)
- [Branch Naming Convention](#branch-naming-convention)
- [Commit and Pull Request Titles](#commit-and-pull-request-titles)
- [Pull Request Requirements](#pull-request-requirements)
- [Review Process](#review-process)
- [Keeping Your Branch Up to Date](#keeping-your-branch-up-to-date)
- [Development Environment](#development-environment)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Changes to Scoring](#changes-to-scoring)
- [Data Corrections](#data-corrections)
- [Release Process](#release-process)
- [Getting Help](#getting-help)

## Overview

Free Stop follows an issue driven workflow. Every change, however small, begins with an issue, is developed on a dedicated branch, and is merged through a reviewed pull request into the `dev` branch. Once a maintainer approves and merges a pull request into `dev`, the change is released to `main`, and therefore to production, automatically.

## Ways to Contribute

| Contribution | Where to start |
|---|---|
| Ask a question or discuss an idea | [Discussions](https://github.com/leshvinsk/free-stop/discussions) |
| Report a defect | [New issue](https://github.com/leshvinsk/free-stop/issues/new/choose), using the Bug report form |
| Correct inaccurate Formula 1 data | [New issue](https://github.com/leshvinsk/free-stop/issues/new/choose), using the Data correction form |
| Propose a new feature | [New issue](https://github.com/leshvinsk/free-stop/issues/new/choose), using the Feature request form |
| Report a security vulnerability | [Private security advisory](https://github.com/leshvinsk/free-stop/security/advisories/new). Never use a public issue |
| Contribute code or documentation | Follow the [Contribution Workflow](#contribution-workflow) below |

## Access Model

Free Stop does not grant direct write access to contributors. All changes are submitted from a personal fork through pull requests.

- The `main` and `dev` branches are protected. Neither accepts direct pushes.
- Every pull request requires passing checks and approval from a code owner before it can be merged.
- Workflows on pull requests from first time contributors run only after a maintainer approves them.
- Contributors who participate constructively over time may be invited to take on additional responsibilities, as described in [GOVERNANCE.md](GOVERNANCE.md).

## Branching Model

| Branch | Role | Accepts pull requests from | Merge method | Merged by |
|---|---|---|---|---|
| `dev` | Default and integration branch | Contributor branches | Squash merge | Maintainer |
| `main` | Production branch | `dev` only | Merge commit | Automated release workflow |
| `<type>/<issue>-<description>` | One branch per issue | Not applicable | Not applicable | Not applicable |

```text
issue #42 opened and assigned
   |
   v
feat/42-tyre-compound-timeline   created on your fork from dev
   |
   |  pull request into dev, checks pass, code owner approves, squash merge
   v
dev
   |
   |  release pull request into main, merged automatically once checks pass
   v
main   deployed to production
```

Pull requests must always target `dev`. Pull requests that target `main` from any branch other than `dev` fail the policy check and are closed.

## Contribution Workflow

### Step 1: Find or create an issue

Search the [existing issues](https://github.com/leshvinsk/free-stop/issues) first. If no issue describes your change, open one using the appropriate form. Issues labelled `good first issue` are suitable for new contributors.

### Step 2: Request the issue

Comment on the issue to ask for it to be assigned to you. Wait for a maintainer to assign it before starting work, so that effort is not duplicated. Significant changes should have their approach agreed in the issue before implementation begins.

### Step 3: Fork the repository

Select **Fork** on the repository page, then clone your fork:

```bash
git clone https://github.com/<your-username>/free-stop.git
cd free-stop
git remote add upstream https://github.com/leshvinsk/free-stop.git
```

### Step 4: Create a branch for the issue

Always branch from the latest `dev`:

```bash
git fetch upstream
git checkout -b feat/42-tyre-compound-timeline upstream/dev
```

Use one branch for one issue. Do not combine unrelated changes, and never work directly on `dev` or `main`.

### Step 5: Make your changes

Make your changes on the issue branch. Do not commit yet.

### Step 6: Bring your branch up to date with dev

Before every commit, update your branch with the latest `dev` so that your work is built on the current code. Other contributors' changes may have been merged since you started.

Run the sync script from the root of the repository:

```bash
sh .github/scripts/sync-with-dev.sh
```

The script performs the following steps in order and stops safely if any of them needs your attention:

| Order | Action | Equivalent command |
|---|---|---|
| 1 | Saves your uncommitted work, including new files | `git stash push --include-untracked` |
| 2 | Downloads the latest `dev` | `git fetch upstream dev` |
| 3 | Replays your branch on top of the latest `dev` | `git rebase upstream/dev` |
| 4 | Restores your uncommitted work | `git stash pop` |

If the rebase reports a conflict, resolve the conflicted files, run `git add <file>` followed by `git rebase --continue`, and then run `git stash pop` to restore your work.

On Windows, run the script from Git Bash, which is installed with Git for Windows.

### Step 7: Run all checks locally

Run the full set of [quality checks](README.md#quality-checks) before committing. Pull requests with failing checks are not reviewed.

### Step 8: Stage and commit

Stage only the files that belong to the change, then commit using the [title convention](#commit-and-pull-request-titles):

```bash
git add <files>
git commit -m "feat: show tyre compound on the race timeline"
```

### Step 9: Push the branch

```bash
git push --force-with-lease origin feat/42-tyre-compound-timeline
```

`--force-with-lease` is required whenever the branch has been rebased after an earlier push. It updates your branch safely and refuses to overwrite any commits you have not seen.

### Step 10: Open a pull request

Open a pull request from your branch into `leshvinsk/free-stop:dev`. Complete every section of the pull request template, and include `Closes #42` so that the issue closes automatically when the change is merged.

### Step 11: Respond to review

Address review comments on the same branch. Before each new commit, repeat steps 6 to 9 so that the branch stays rebased on the latest `dev`. Resolve each conversation once it has been addressed. When the pull request is approved, a maintainer squash merges it into `dev`.

### Workflow Summary

```bash
git checkout -b feat/42-tyre-compound-timeline upstream/dev   # once per issue
# make your changes
sh .github/scripts/sync-with-dev.sh                           # stash, fetch, rebase, stash pop
# run the quality checks
git add <files>
git commit -m "feat: show tyre compound on the race timeline"
git push --force-with-lease origin feat/42-tyre-compound-timeline
# open a pull request into dev
```

## Branch Naming Convention

Branches must follow the pattern `<type>/<issue-number>-<short-description>`, using lowercase letters, digits and hyphens only. The policy check rejects branches that do not follow this pattern.

| Type | Use for | Example |
|---|---|---|
| `feat` | A new feature | `feat/42-tyre-compound-timeline` |
| `fix` | A defect fix | `fix/57-dsq-field-average` |
| `docs` | Documentation only | `docs/63-baseline-explanation` |
| `refactor` | Restructuring without a change in behaviour | `refactor/71-split-pipeline` |
| `perf` | A performance improvement | `perf/80-season-cache` |
| `test` | Tests only | `test/85-red-flag-cases` |
| `data` | A correction to Formula 1 data | `data/90-alpine-principal-2025` |
| `style` | Visual or formatting changes with no logic change | `style/94-table-spacing` |
| `build` | Build tooling or dependencies | `build/97-vite-upgrade` |
| `ci` | Workflow configuration | `ci/99-cache-pip` |
| `chore` | Maintenance that fits no other type | `chore/101-remove-unused-assets` |

## Commit and Pull Request Titles

Commit messages and pull request titles follow the [Conventional Commits](https://www.conventionalcommits.org) specification. Because pull requests are squash merged, the pull request title becomes the commit message on `dev`, and the policy check enforces its format.

```text
<type>(<optional scope>): <summary in the imperative mood>
```

| Example | Accepted |
|---|---|
| `feat: show tyre compound on the race timeline` | Yes |
| `fix(scoring): exclude disqualified drivers from the field average` | Yes |
| `data: correct the 2025 Alpine team principal` | Yes |
| `Updated stuff` | No |
| `Fix bug.` | No |

## Pull Request Requirements

A pull request can be merged only when every requirement below is met.

| Requirement | Enforced by |
|---|---|
| Targets the `dev` branch | PR policy check |
| Branch follows the naming convention | PR policy check |
| Title follows Conventional Commits | PR policy check |
| Branch is rebased on the latest `dev` | PR policy check |
| Branch contains no merge commits | PR policy check |
| Backend checks pass | CI |
| Frontend checks pass | CI |
| Branch is up to date with `dev` | Branch ruleset |
| All review conversations are resolved | Branch ruleset |
| Approved by a code owner | Branch ruleset |

## Review Process

Maintainers aim to provide a first review within five working days. Reviews assess:

- Correctness of the change and its effect on displayed figures
- Test coverage for new or modified behaviour
- Consistency with the existing structure and coding standards
- Clarity of naming and of any user facing text
- Performance, security and accessibility implications

Requested changes are a normal part of review and should not be read as a rejection. Pull requests that receive no response from their author for 30 days may be closed, and can be reopened at any time.

## Keeping Your Branch Up to Date

Free Stop accepts rebased branches only. The PR policy check fails if a branch is behind `dev` or contains merge commits, so never use `git merge` or `git pull` without `--rebase` to update an issue branch.

Use the sync script whenever `dev` has moved on, including while a pull request is under review:

```bash
sh .github/scripts/sync-with-dev.sh
git push --force-with-lease origin <your-branch>
```

If a maintainer asks you to update a pull request through the GitHub interface, choose **Update with rebase**, not **Update with merge commit**.

## Development Environment

Installation, configuration and local start up are documented in the [README](README.md#getting-started). Both the backend and the frontend can run on a single machine without any external accounts or credentials.

## Coding Standards

| Area | Standard |
|---|---|
| Python formatting and linting | Ruff. Run `ruff format .` to apply formatting |
| Python typing | mypy in strict mode. All new code must be fully typed |
| TypeScript and Vue formatting | Prettier. Run `npm run format` to apply formatting |
| TypeScript and Vue linting | ESLint with the TypeScript and Vue rule sets |
| Comments | Explain why, where it is not obvious. Do not restate what the code does |
| User facing text | Plain, consistent wording. Times are shown to three decimal places |

## Testing Requirements

- Any change to scoring logic must include new or updated tests in `backend/tests/`.
- Defect fixes should include a test that fails without the fix.
- Frontend utilities should be covered by Vitest tests alongside the source file.
- Tests must not call external services. Use fixtures and mocked transports instead.

## Changes to Scoring

Changes to the scoring formula, the baseline calculation or the classification of race conditions affect every figure on the site, and are therefore reviewed with particular care. Such pull requests must include:

- A clear explanation of the change and the reason it improves accuracy
- New or updated tests in `backend/tests/test_formula.py` or `backend/tests/test_neutralised.py`
- A list of the races or seasons whose results change as a consequence
- An update to the methodology page where the explanation is affected

## Data Corrections

Free Stop publishes verified data only. Every correction must cite an official source, such as formula1.com, fia.com or the team's own website.

- To report inaccurate data, open an issue using the **Data correction** form.
- To submit a correction directly, edit `frontend/src/data/teamInfo.ts` on a `data/<issue>-<description>` branch and link the source in the pull request.
- Do not edit `frontend/src/data/teams_scraped.json`. It is maintained by an automated workflow and is overwritten on each synchronisation.

## Release Process

Contributors do not need to take any action to release a change. When a maintainer approves and merges a pull request into `dev`, the release workflow opens a release pull request from `dev` to `main` and enables auto-merge on it. As soon as the checks on `dev` pass, the release pull request merges itself and the change is deployed to production. No second approval is required, because every change on `dev` has already been reviewed and approved. Release notes and version tags are published by the maintainers on the [Releases](https://github.com/leshvinsk/free-stop/releases) page.

## Getting Help

Questions about contributing are welcome in [Discussions](https://github.com/leshvinsk/free-stop/discussions). Further guidance is available in [SUPPORT.md](SUPPORT.md).
