# Review and Reference chunks

The last two chunks of a lesson page, after the last quiz. SKILL.md section 3.5 says what goes in them. Copy the cards below into `lesson.json` and replace the `<placeholders>`. Leave out a card or row that has nothing to hold, such as "Mistakes to watch" when there are none.

In the chat, SEND the same cards as one message, with each card title as a heading and the worked solutions at the end.

## Review

```json
{"id": "review", "title": "Review", "cards": [
  {"kind": "text", "title": "When to come back", "blocks": [
    {"type": "p", "text": "Do these tasks on <date 1>, <date 2> and <date 3>, or as soon as you next use this. Answer each one before you open its solution. Then reread the part of the Reference that covers anything you missed, and do a new task like it, from your own work if you can."}]},
  {"kind": "practice", "id": "review-1", "title": "<task title>",
   "blocks": [{"type": "p", "text": "<task from a situation where the LEARNER will use the topic>"}],
   "solution": [{"type": "p", "text": "<solution, each step with its reason>"}]},
  {"kind": "practice", "id": "review-2", "title": "<task title>",
   "blocks": [{"type": "p", "text": "<task in a different situation, that applies a rule to a case the lesson did not show>"}],
   "solution": [{"type": "p", "text": "<solution, each step with its reason>"}]}]}
```

## Reference

```json
{"id": "reference", "title": "Reference", "cards": [
  {"kind": "text", "title": "When to use this", "blocks": [
    {"type": "table", "columns": ["When you see", "Use"], "rows": [
      ["<a sign in the LEARNER's situation that a rule applies>", "<rule or step, and the card below that covers it>"]]}]},
  {"kind": "text", "title": "<chunk title>", "blocks": [
    {"type": "steps", "items": [{"label": "<step>", "note": "<optional detail>"}]},
    {"type": "p", "text": "Rule: <rule, with the conditions under which it holds>"},
    {"type": "p", "text": "Why it works: <one or two sentences, so the LEARNER can adapt the steps to a case the lesson did not show>"},
    {"type": "p", "text": "Example: <the worked example from the chunk, each step with its reason>"},
    {"type": "p", "text": "Source: [<source title>](<url>)"}]},
  {"kind": "text", "title": "Mistakes to watch", "blocks": [
    {"type": "list", "items": ["<mistake> → <the rule it misapplies, and the card that covers it>"]}]},
  {"kind": "practice", "id": "plan", "title": "Your plans",
   "blocks": [{"type": "p", "text": "Write one to three plans in the form \"When <situation>, I will <step from this lesson>.\" Optional."}],
   "fields": [{"id": "plans", "label": "Your plans"}],
   "solution": [{"type": "p", "text": "<what a good plan names: a situation from the LEARNER's work and one step from this lesson>"}]},
  {"kind": "text", "title": "Not covered", "blocks": [
    {"type": "list", "items": ["<chunk not taught>"]}]}]}
```

Add one "<chunk title>" card per chunk taught. Add a symbol table to a chunk's card when its rule uses symbols, with one row per symbol and what it stands for in the example.
