## Summary

<!-- Describe the change in one or two paragraphs. -->

## Linked Issue

Closes #<!-- issue number -->

## Type of Change

- [ ] New feature (`feat`)
- [ ] Defect fix (`fix`)
- [ ] Data correction (`data`)
- [ ] Documentation (`docs`)
- [ ] Refactoring with no change in behaviour (`refactor`)
- [ ] Performance improvement (`perf`)
- [ ] Tests only (`test`)
- [ ] Build, workflow or maintenance (`build`, `ci`, `chore`)

## Description of Changes

<!-- List the main changes and the reasoning behind them. -->

## Testing

<!-- Describe how the change was verified. Include the season, race, driver or team used where relevant. -->

## Screenshots

<!-- For interface changes, include before and after screenshots. Remove this section if not applicable. -->

## Checklist

- [ ] This pull request targets the `dev` branch
- [ ] The branch is named `<type>/<issue-number>-<short-description>`
- [ ] The title follows Conventional Commits, for example `feat: show tyre compound on the race timeline`
- [ ] Backend checks pass locally: `ruff check .`, `ruff format --check .`, `mypy .`, `pytest -v`
- [ ] Frontend checks pass locally: `npm run type-check`, `npm run lint`, `npm run format -- --check`, `npm test`, `npx vite build`
- [ ] Tests were added or updated for any change to behaviour or scoring
- [ ] Documentation was updated where needed
- [ ] Data corrections cite an official source
- [ ] No credentials, personal data or generated files are included
