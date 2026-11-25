# Working in this repository

Rules for every agent and person who changes this repository. To write or change a skill, also follow
[PRINCIPLES.md](PRINCIPLES.md); for evals, [evals/PRINCIPLES.md](evals/PRINCIPLES.md); for the shipped `better.pyz`,
[CONTRIBUTING.md](CONTRIBUTING.md).

## Branches

- Several agents work in this repository at once. Do branch work in a git worktree under `.claude/worktrees/<name>`,
  never in the main checkout, which stays on `main`, and never in another folder.
- Before you push to a pull request's branch, check that the pull request is still open (`gh pr view <n> --json
  state`). If it is merged, put the new commits on a new branch from `main` and open a new pull request.

## Before you push

Run what CI runs, and merge `origin/main` first if it moved:

- `uvx ruff check .` and `uvx ruff format --check .`
- `python3 tools/build.py --check` (rebuild with `python3 tools/build.py` after any change to `src/` or after a merge)
- `python3 -I tools/smoke.py` and `python3 tests/run.py`
- when page files change: the `pages` job in `.github/workflows/scripts.yml` (stylelint, html-validate,
  `node --check`, `node --test tests/*.test.js`)
- when skill text changes: `vale skills`
- when `evals/` changes: the jobs in `.github/workflows/evals.yml`

Run Python tools with `uv run --frozen`, so that no run rewrites a `uv.lock`. Before you commit, check `git status`
for lockfile changes you did not intend.

## Tests

- Never open a real browser from a test or a check: stub `webbrowser.open` or pass `--no-browser`.
- Run page tests on a copy of a board or canvas, served on its own, never on one a person has open.
- When a script links two pieces of data, match an exact ID from a structured field, such as a JSON field. Do not
  parse free text with regular expressions.
- Never read `.env`.

## Public repository

This repository is public. In issues, pull requests and commit messages:

- describe changes and feedback as general patterns: no links to private pages or artifacts, no names of private
  projects or research, no private data;
- write pull request descriptions for public readers: state what changed and the results, with no questions or asks
  addressed to the maintainer;
- give a pull request that changes how a page looks before and after screenshots, rendered from made-up data, pushed
  to the `pr-screenshots` branch under `pr<N>/` and linked by commit SHA;
- give each issue a skill label (`skill: <name>`) and one type label: `bug` (broken skill or tool behaviour),
  `enhancement`, `question` or `eval` (eval cases, graders and runs).
