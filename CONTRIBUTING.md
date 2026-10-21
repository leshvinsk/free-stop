# Contributing to Free Stop

Thank you for your interest in contributing. Free Stop is a community project and all contributions are welcome — bug fixes, new analyses, UI improvements, data corrections, or documentation.

## Before you start

- Check the [open issues](https://github.com/leshvinsk/free-stop/issues) to see if someone is already working on what you have in mind.
- For significant changes, open an issue first to discuss the approach before writing code.
- Join the conversation in [Discussions](https://github.com/leshvinsk/free-stop/discussions).

## Workflow

1. **Fork** the repository and create a branch from `main`:
   ```bash
   git checkout -b fix/your-description
   # or
   git checkout -b feat/your-description
   ```

2. **Make your changes.** Keep each PR focused on one thing.

3. **Run all checks locally before pushing:**

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

4. **Open a pull request** against `main`. Fill in the PR template — especially the "How to test" section.

5. **CI must be green** before your PR can be reviewed. Fix any failures before requesting a review.

6. One of the maintainers will review and merge. Expect feedback — it is not a rejection, it is part of the process.

## Code style

- **Python:** ruff enforces formatting and linting. Run `ruff format .` to auto-fix formatting.
- **TypeScript / Vue:** Prettier enforces formatting. Run `npm run format` to auto-fix.
- **Comments:** only where the *why* is non-obvious. Do not describe what the code does.
- **Tests:** scoring logic changes must include or update a test in `backend/tests/`.

## Scoring changes

Changes to the luck formula, baseline calculation, or classification logic require extra care — they affect every displayed number on the site. Please include:

- A clear explanation of what changed and why it is more accurate.
- Updated or new tests in `backend/tests/test_formula.py` or `backend/tests/test_neutralised.py`.
- A note in the PR about which races or seasons produce different scores after the change.

## Data corrections

If you spot incorrect team principals, chassis names, driver suits, or other static data, open a bug report or submit a PR editing `frontend/src/data/teamInfo.ts` directly. Include a source link.

## Questions?

Open a [Discussion](https://github.com/leshvinsk/free-stop/discussions) — do not use issues for questions.
