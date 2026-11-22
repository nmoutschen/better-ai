# Contributing

## The shipped `better.pyz`

Each skill that has scripts ships one file, `skills/<skill>/scripts/better.pyz`, built from the source in
`src/better_ai/`. The `.pyz` files are committed, so users get them with the skill. Nobody edits one by hand.

### Rebuild after you change `src/`

```
python3 tools/build.py
```

Needs Python 3.12 or later; the `.pyz` it writes runs on Python 3.10. The result is byte-identical on every machine:
the same source gives the same bytes. Commit the changed `.pyz` files with your source change.

`python3 tools/build.py --check` rebuilds and compares with what is committed, and reports every difference as
`<kind>: <file>: <fix>`. CI runs it. `python3 tools/build.py --which <hash>` prints the commit whose sources have
the source hash a `.pyz` reports (`better.pyz --help` prints it).

### Files to read closely

Three files carry the trust in the shipped bytes. A pull request that touches one of them gets a close read, and
CODEOWNERS asks the maintainer to review it:

- `tools/build.py`: it decides what goes into each `.pyz`;
- `src/better_ai/skills.json`: it lists what goes into which `.pyz`;
- `.github/workflows/`: it holds the checks that prove the committed `.pyz` files come from the source. The
  required check `Base build` builds the pull request's `src/` with the base branch's `tools/build.py` and fails if
  the committed `.pyz` files differ; it never runs the pull request's code.

Change `tools/build.py` in its own pull request, apart from `src/`: the base build is the reference that proves the
source change, and `--check --base <commit>` fails when one change touches both.
