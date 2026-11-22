# Fixture units for `tools/smoke.py`

`tools/smoke.py` runs each committed `skills/<skill>/scripts/better.pyz` with `python -I`. For each skill it reads
`tests/fixtures/units/<skill>/smoke.json` and runs its steps in a fresh git repository (with one empty commit). The
skill's own task adds the folder; CI fails for a skill that has a `.pyz` and no fixture.

`smoke.json` holds:

- `steps`: commands run in order from the repository root. Each is `{"args": [...]}` with the arguments after
  `better.pyz`, and optionally:
  - `"stdin"` (text) or `"stdin_file"` (a file in this folder): what the command reads on stdin, such as a head
    record for `create` or a record's fields for `add`;
  - `"exit"`: the expected exit code (default 0);
  - `"stdout_matches"`: a regular expression the standard output must contain;
  - `"serve": true`: for `serve <unit> --no-browser --once`. The runner reads the first `http://` URL the
    command prints on stdout, fetches it once, and expects status 200 and then exit 0.
  The steps cover `create`, `add`, `set`, `check`, `render` and `serve --no-browser --once` against a unit of one of the skill's kinds.
- `worktree_steps`: steps run, after the others pass, from a second `git worktree` of the same repository. They
  prove an `add` from a task worktree writes into the main checkout's unit: `{repo}` in an argument stands for the
  main checkout's path, so `add {repo}/.code/demo ...` names that unit by an absolute path.
- `repo_files`: `{"<path in the repository>": "<file in this folder>"}`, copied into the repository before the first
  commit, for a unit that needs a design folder or another file in place before `create`.

The runner fails a fixture that does not cover `create`, `add`, `set`, `check`, `render`, a `serve` step and an `add` in
`worktree_steps`.

Before the steps the runner also checks that `better.pyz --help` exits 0 and prints
`better.pyz <skill> <hash>` as its first line, with the hash from the `.pyz`'s own `better_ai/_build.json`.
