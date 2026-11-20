# Contributing

## Layout

- `common/`: helpers shared between packages.
- `invoicing/`, `payroll/`: one package per product. Each package has notes
  in `docs/packages/`.

## Tests

Run every package's tests from the repository root:

    python -m unittest discover -p 'test_*.py'

## Changes

Keep each change to one purpose and describe it in the commit message.
