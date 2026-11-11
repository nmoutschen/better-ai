# Reference page

One page of a reference: one chunk in `lesson.json`, with its cards in the order below. modes/static.md section 3 says what goes in each part. Copy the chunk and replace the `<placeholders>`. Repeat the three core-idea cards once per idea. The page labels an `example` card "Example", or "Try it" when it has a solution, so its title names only the situation. Leave out a card that has nothing to hold.

In the chat, SEND the same parts as one message, with each card title as a heading and each solution at the end of the message.

```json
{"id": "<page-id>", "title": "<what the reader will do, such as 'Review an automation design'>", "cards": [
  {"kind": "text", "title": "Summary", "blocks": [
    {"type": "p", "text": "<what the topic lets the reader do>"},
    {"type": "p", "text": "For: <readers>. Builds on: [<page title>](#<page-id>/1)."}]},
  {"kind": "text", "title": "When to use this", "blocks": [
    {"type": "table", "columns": ["When you see", "Use"], "rows": [
      ["<a sign in the reader's situation that the topic applies>", "<the idea, and the card that covers it>"],
      ["<a near miss: looks similar but lacks a feature the idea needs>", "Not this: <why>"]]}]},
  {"kind": "text", "title": "<idea, named by what the reader does>", "blocks": [
    {"type": "p", "text": "<the idea in plain words, then its term>"},
    {"type": "p", "text": "Why it works: <one or two sentences> ([<source>](<url>))"}]},
  {"kind": "example", "title": "<situation>", "blocks": [
    {"type": "steps", "items": [{"label": "<step>", "note": "<why>"}]}]},
  {"kind": "example", "title": "<situation>", "blocks": [
    {"type": "p", "text": "<a problem like the example, in a different situation>"}],
   "hints": ["<where attempts go wrong>", "<the rule, quoted>"],
   "solution": [{"type": "p", "text": "<every step with its reason>"}],
   "wrong": [{"answer": "<likely wrong answer>", "why": "<the idea it misapplies>"}]},
  {"kind": "text", "title": "Cases", "blocks": [
    {"type": "p", "text": "<a real case, what happened, and how the idea explains it> ([<source>](<url>))"}]},
  {"kind": "text", "title": "Common mistakes", "blocks": [
    {"type": "list", "items": ["<mistake> → <the idea it misapplies>"]}]},
  {"kind": "text", "title": "Limits and disagreements", "blocks": [
    {"type": "list", "items": ["<where evidence is thin, sources disagree, or the page does not reach>"]}]},
  {"kind": "text", "title": "Quick reference", "blocks": [
    {"type": "steps", "items": [{"label": "<step>", "note": "<optional detail>"}]}]},
  {"kind": "text", "title": "Sources", "blocks": [
    {"type": "list", "items": ["[<author, year, title>](<url>)"]}]}]}
```
