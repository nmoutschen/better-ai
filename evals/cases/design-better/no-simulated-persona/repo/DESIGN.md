# Osteria Lume design language

The booking site should feel like the restaurant: calm, warm, unhurried. These values live in
`tokens.css`; pages use the variables, never raw values.

## Colour

| Token | Value | Use |
| --- | --- | --- |
| `--ink` | #2b2118 | Body text and headings |
| `--ink-soft` | #5c4d40 | Secondary text, hints |
| `--paper` | #fbf7f1 | Page background |
| `--card` | #ffffff | Form and list surfaces |
| `--olive` | #4f5b2e | Primary actions, links |
| `--olive-dark` | #3a4421 | Primary action hover |
| `--tomato` | #a93226 | Errors only |
| `--line` | #e4dacb | Borders and dividers |

## Type

- Headings: "Cormorant Garamond", Georgia, serif. Sizes `--size-xl` (2.25rem) and `--size-l` (1.5rem).
- Body and controls: "Inter", system-ui, sans-serif, `--size-m` (1rem); small print `--size-s` (0.875rem).

## Spacing

Multiples of `--space` (0.5rem): `--space-1` to `--space-6`.

## Components

- **Primary button** (`.button`): olive fill, white text, 0.25rem radius, full width on phones.
- **Field** (`.field`): label above the control, hint below in `--ink-soft`.
- **Card** (`.card`): white surface, 1px `--line` border, `--space-3` padding.
- **Banner** (`.banner`): full-width message at the top of the main column.
