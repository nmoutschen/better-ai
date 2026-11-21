# Lessons: <short name of the change>

<HOW TO FILL THIS IN — delete this block when done.
- SAVE them in `.code/<change>/lessons.jsonl`, one line per lesson, in the format of `schemas/lessons.schema.json`, which is the authority. Only the coordinator writes it.
- Conventions: START each record with `type`, `at` (UTC, ending in Z) and `by` (your agent name). WRITE a list as a JSON array. A field the schema does not name is an error. WRITE one record per line, as ASCII JSON, and the task a `found_in` entry names before the lesson. AFTER each write, RUN `python3 <skill dir>/scripts/schema.py check <the file>` and FIX what it reports.
- WRITE one lesson for each finding of a verifier that could recur in another task. `id` is L<n>, counting up; `class` is a short name for the bug class; `rule` is what to do, in one sentence. `found_in` lists each task whose verifier found it, with a short label of the finding.
- WHEN a later finding is of a class a lesson already names, ADD its task to that lesson's `found_in`; WRITE no second lesson.>

Conventions and fields: `schemas/*.schema.json` of this skill.

{"type": "lesson", "at": "<UTC time>", "by": "<agent>", "id": "L<n>", "class": "<short name of the bug class>", "rule": "<what to do, in one sentence>", "found_in": [{"task": "T<n>", "finding": "<short label of the finding>"}]}
