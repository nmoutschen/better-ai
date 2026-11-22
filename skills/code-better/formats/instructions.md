# Instruction records

ADD each with `python3 <skill dir>/scripts/better.pyz add <unit> instruction --by <your agent name>`, its fields as JSON on stdin, where `<unit>` is the change folder `.code/<change>`; one for each instruction. IF the command refuses a record, FIX the record and RUN it again. In coordinate mode only the coordinator adds them.

- ADD only an instruction on how to work, such as never touch a folder or run a check before each commit, with the user's words in `said`. A constraint on what the code does goes into the spec.
- GIVE a missing value as `null` and a list as a JSON array. A field not shown below is an error.

{"type": "instruction", "instruction": "<the instruction, in one sentence>", "said": "<the user's words>"}
