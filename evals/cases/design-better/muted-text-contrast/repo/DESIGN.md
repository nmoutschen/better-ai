# Kettle & Crumb design language

The shop's look, agreed with the brand agency in March. tokens.css holds every value; styles.css uses only tokens.
Ask Hanna (brand) before changing a token or adding one.

## Colour

| Token | Value | Use |
|---|---|---|
| `--surface` | #ffffff | Page and card background |
| `--text` | #262626 | Body text, labels, field values |
| `--text-muted` | #a3a3a3 | Helper text under fields, secondary details in the order summary |
| `--brand` | #c2410c | Primary buttons, links, focus ring |
| `--brand-ink` | #ffffff | Text on `--brand` |
| `--border` | #e5e5e5 | Field and card borders |
| `--error` | #b91c1c | Error messages and invalid field borders |

## Type

- Body: Inter, `--size-body` (16px), line height 1.5.
- Small: `--size-small` (13px), for helper text and summary details.
- Headings: Fraunces, `--size-h1` (28px) and `--size-h2` (20px).

## Spacing

Multiples of 4px: `--space-1` (4px) to `--space-6` (32px).

## Components

### Field

A label above the input, the input, then optional helper text.

- Label: `--text`, `--size-body`, weight 500.
- Input: `--border`, 1px, radius 6px, padding `--space-3`.
- Helper text: `--text-muted`, `--size-small`, `--space-1` above. Keep it quiet: it must not compete with the label.

Right: "We'll only call if the courier can't find you" under the phone field, in helper text style.
Wrong: helper text in `--text` or in bold, which reads as a second label.

### Primary button

`--brand` background, `--brand-ink` text, full width on phones.
