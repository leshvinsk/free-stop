# Contributing to Free Stop

Thank you for your interest in contributing. Free Stop is a community project, and bug fixes, new analyses, UI improvements, data corrections and documentation are all welcome.

By taking part you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## How access works

Nobody gets direct write access to this repository. Everything comes in through a fork and a pull request:

| What you want to do | Where |
|---|---|
| Ask a question or float an idea | [Discussions](https://github.com/leshvinsk/free-stop/discussions) |
| Report a bug | [New issue → Bug report](https://github.com/leshvinsk/free-stop/issues/new/choose) |
| Fix wrong F1 data | [New issue → Data correction](https://github.com/leshvinsk/free-stop/issues/new/choose) |
| Propose a feature | [New issue → Feature request](https://github.com/leshvinsk/free-stop/issues/new/choose) |
| Report a security problem | [Private advisory](https://github.com/leshvinsk/free-stop/security/advisories/new). Never use a public issue for this |
| Change code | Fork → branch → pull request (below) |

`main` is protected. Every change needs a pull request, green CI, resolved review comments and approval from the code owner. Workflows on a first-time contributor's pull request only run after a maintainer approves them.

Contributors who help consistently over time may be invited to triage issues or review pull requests.

## Before you start

- Look through the [open issues](https://github.com/leshvinsk/free-stop/issues) in case someone is already working on the same thing.
- Issues labelled `good first issue` are a good place to begin.
- Comment on an issue to claim it before you start, so work isn't duplicated.
- For significant changes, agree the approach on the issue before writing code.

## Workflow

1. **Fork** the repository, then create a branch from `main`:
   ```bash
   git checkout -b fix/short-description
   # or
   git checkout -b feat/short-description
   ```

2. **Make your changes.** Keep each pull request focused on one thing.

3. **Write commit messages** in the [Conventional Commits](https://www.conventionalcommits.org) style used across this repo:
   ```text
   feat: show tyre compound on the race timeline
   fix: keep DSQ drivers out of the field average
   docs: explain the trimmed baseline
   data: correct the 2025 Alpine team principal
   ```

4. **Run every check locally before pushing.**

   Backend:
   ```bash
   cd backend
   ruff check .
   ruff format --check .
   mypy .
   pytest -v
   ```

   Frontend:
   ```bash
   cd frontend
   npm run type-check
   npm run lint
   npm run format -- --check
   npm test
   npx vite build
   ```

5. **Open a pull request** against `main` and fill in the template, especially **How to test**.

6. **Get CI green.** A pull request can't be merged until both CI jobs pass.

7. **Respond to review.** Feedback is part of the process, not a rejection. Pull requests are squash-merged, so the title becomes the commit message on `main`.

## Code style

- **Python:** ruff enforces formatting and linting. Run `ruff format .` to fix formatting automatically.
- **TypeScript / Vue:** Prettier enforces formatting. Run `npm run format` to fix it automatically.
- **Comments:** only where the *why* isn't obvious. Don't describe what the code does.
- **Tests:** any change to scoring logic must add or update a test in `backend/tests/`.

## Scoring changes

Changes to the luck formula, the baseline calculation or the lap classification affect every number on the site, so they need extra care. Please include:

- A clear explanation of what changed and why it is more accurate.
- New or updated tests in `backend/tests/test_formula.py` or `backend/tests/test_neutralised.py`.
- A note in the pull request listing which races or seasons score differently after the change.

## Data corrections

Free Stop only publishes verified data. To correct a team principal, chassis, power unit, driver photo or flag, open a **Data correction** issue with an official source (formula1.com, fia.com or the team's own site). You can also edit `frontend/src/data/teamInfo.ts` directly in a pull request, with the source linked.

`frontend/src/data/teams_scraped.json` is maintained by a bot. Don't edit it by hand, because the next sync overwrites it.

## Questions?

Open a [Discussion](https://github.com/leshvinsk/free-stop/discussions). Please don't use issues for questions.
