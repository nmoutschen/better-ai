# Harbour Desk design language

Agents keep this tool open all day on a 24-inch screen next to the mail client. Dense but calm.

## Colour

| Token | Value | Use |
|---|---|---|
| `--bg` | #f6f7f9 | Page background |
| `--panel` | #ffffff | Tables, cards, panels |
| `--ink` | #17202a | Text |
| `--ink-2` | #556270 | Secondary text: customer, time, channel |
| `--line` | #dde2e8 | Borders and row dividers |
| `--accent` | #1d5fd1 | Links, primary buttons, selected row |
| `--urgent` | #b42318 | Urgent priority and breached targets only |
| `--warn` | #8a5a00 | High priority and targets due within the hour |

## Type

System UI stack. `--text` 14px for tables, `--text-lg` 18px for page titles. Numbers in tabular figures.

## Spacing

`--s1` 4px, `--s2` 8px, `--s3` 12px, `--s4` 16px, `--s5` 24px.

## Components

- **Priority badge**: text label (Urgent, High, Normal, Low), never colour alone.
- **Ticket row**: ID, subject, customer, priority badge, time to first-reply target.
- **Primary button**: `--accent` background, white text, 32px high.
