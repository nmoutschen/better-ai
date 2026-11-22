# Lessons: <short name of the change>

<HOW TO FILL THIS IN — delete this block when done.
- ADD them to `.code/<change>/lessons.jsonl`, one line per lesson. Only the coordinator writes it.
- Conventions: WRITE a list as a JSON array. A field not shown below is an error. WRITE the task a `found_in` entry names before the lesson.
- WRITE one lesson for each finding of a verifier that could recur in another task. `class` is a short name for the bug class; `rule` is what to do, in one sentence. `found_in` lists each task whose verifier found it, with a short label of the finding.
- WHEN a later finding is of a class a lesson already names, EDIT that lesson with `set`, with the task added to `found_in`; WRITE no second lesson.>

{"type": "lesson", "class": "<short name of the bug class>", "rule": "<what to do, in one sentence>", "found_in": [{"task": "T<n>", "finding": "<short label of the finding>"}]}
