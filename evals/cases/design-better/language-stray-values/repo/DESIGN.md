# Kestrel Physio design language

Clear and quiet: patients come to book, check opening hours or find the clinic, often in pain.
All values come from `tokens.css`. Do not use raw colours, sizes or spacing in pages or styles.

## Colour

- `--text` #1d2b36 for all body text; `--text-soft` #4c5d69 for secondary text.
- `--bg` #f7f9fa page background; `--surface` #ffffff for cards.
- `--brand` #1f6f8b for links and primary buttons; `--brand-dark` #17566c on hover.
- `--border` #d6dee3.

## Type

- One family: `--font` ("Source Sans 3", system-ui, sans-serif).
- Sizes: `--size-s` 14px (small print), `--size-m` 16px (body), `--size-l` 20px, `--size-xl` 28px.

## Spacing

An 8px grid: `--space-1` 8px, `--space-2` 16px, `--space-3` 24px, `--space-4` 32px.

## Components

- **Card** (`.card`): `--surface` background, 1px `--border`, `--space-3` padding, 8px radius. Use it for every
  boxed block: a service, a therapist, opening hours.
- **Button** (`.button`): `--brand` fill, white text, `--space-1` `--space-2` padding, 6px radius.
