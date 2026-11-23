# Lesson records

ADD each with `python3 <skill dir>/scripts/better.pyz add <unit> lesson --by <your agent name>`, its fields as JSON on stdin, where `<unit>` is the change folder `.code/<change>`; one for each lesson. CHANGE one with `python3 <skill dir>/scripts/better.pyz set <unit> <id>`. IF the command refuses a record, FIX the record and RUN it again. Only the coordinator adds lessons.

- GIVE a list as a JSON array. A field not shown below is an error. ADD the task a `found_in` entry names before the lesson.
- ADD one lesson for each finding of a verifier that could recur in another task. `class` is a short name for the bug class; `rule` is what to do, in one sentence. `found_in` lists each task whose verifier found it, with a short label of the finding.
- WHEN a later finding is of a class a lesson already names, CHANGE that lesson with `set`, with the task added to `found_in`; ADD no second lesson.

{"type": "lesson", "class": "<short name of the bug class>", "rule": "<what to do, in one sentence>", "found_in": [{"task": "T<n>", "finding": "<short label of the finding>"}]}
