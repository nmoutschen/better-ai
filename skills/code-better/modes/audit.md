---
name: audit
description: Use when the user asks for an audit of existing code, such as its technical debt, anti-patterns or what to improve, and wants a ranked list of opportunities rather than a change.
---

# Mode: audit

FOLLOW these steps in order. The general rules of SKILL.md apply throughout.

An audit reports; it does not change the code. DO NOT edit, create or delete any file outside `.code/`, even for a one-line fix: PROPOSE each fix as a task instead.

## 1. Name what the audit is for

NAME the scope: the path or area given as argument, OTHERWISE the whole repository.

NAME the GOAL: what the user will do with this code next, such as add features to one area, hand it over, or keep it running with less effort. The GOAL decides which debt costs the user something: debt costs when someone changes the code, and rankings made from the code alone match what the business needs only about half the time.

READ the repository's documentation: README.md, docs/, CONTRIBUTING.md, AGENTS.md, and any roadmap, issue list or TODO file that names planned work. IF they do not say what work comes next, ASK the user that one question, as the general rule [Ask the user](../SKILL.md#ask-the-user) says, and KEEP collecting evidence while you wait.

## 2. Collect the evidence

COLLECT, for the scope:

1. From the Git history of the last twelve months: how often each file changed, which files changed together in the same commits, and which commits fixed bugs, by their messages. Change history locates code that causes defects better than measures of the code itself.
2. The result of the tests and of the static, type, lint and security checks the project uses.
3. The rules the repository states for its code, in its documentation and in its linter and formatter settings.

READ [../formats/audit.md](../formats/audit.md). MAKE the audit folder with `python3 <skill dir>/scripts/better.pyz create .code/audit/<YYYY-MM-DD> --by <your agent name, such as builder>`, with the GOAL, the commit and `not_read` set to `null` as JSON on stdin. ADD these facts with `python3 <skill dir>/scripts/better.pyz add .code/audit/<YYYY-MM-DD> <type> --by <your agent name>`, with the type `history`, `check` or `rule`, in the format's fields, one record for each, with the command that produced it.

TREAT a debt rating or a remediation-time estimate from a tool as a pointer, not as a cost: such tools disagree with each other, relate weakly to defects, and mostly overestimate the time. TREAT comments that admit debt, such as TODO, FIXME or HACK, as pointers too.

IF the repository has no history, or less than the period above, SAY so in the report and RANK without change frequency.

## 3. Run the review

START a separate reviewer for every audit, however small the scope: DO NOT review the code yourself instead. USE `/review-better` to run the review, if available. The work is the code in scope. The GOAL of the review is that the user can choose what to improve next. The reviewer does not change the code, and reports every finding it confirms, however small, because the full list is for agents to work from: the report to the user stays short in step 6. GIVE the reviewer `evidence.jsonl` and this list of what to look for:

1. Code that gives wrong results now, or loses data, money or what users are told.
2. Knowledge written in more than one place, such as a rate, a rule or a format, where the copies already differ, or where the history shows one copy changed without the other. Repeated lines alone are not a finding: duplicated code causes defects in some systems and not in others.
3. Failures the code hides: errors caught and ignored, a failure reported as success, input that is not validated.
4. Code that changes often and is hard to change: files high in the history of step 2 that are long, complex or untested, and files that must change together without the code showing why.
5. Abstractions that fit their callers badly, such as a flag or branch per caller, and code written for needs that never came, such as unused parameters, modules or extension points. Speculative code has not been shown to cause defects: it costs only where the code changes.
6. Code that breaks a rule the repository states.
7. Small cleanups: unused imports or code, leftover debug output, unnamed constants, and names that break the codebase's conventions.

FOR a scope too large for one reviewer to read, START one reviewer per area, each with the same list.

IF `/review-better` is not available, START a sub-agent as the reviewer, with what to look for, the evidence records and the scope, and without your own view of the code.

WAIT until each reviewer hands back its report. DO NOT write to the user while a reviewer runs.

CONFIRM each finding with evidence you can show: a failing test or a reproduction, the history entries, or the exact lines and the input that make it fail. KEEP a finding you could not confirm, marked unconfirmed.

## 4. Rank by value

RANK the findings, highest value first:

1. Findings that cost the user now: wrong results, lost data or money, security problems, hidden failures.
2. Debt in code that changes often or that the work of the GOAL will change, with the cheaper fix first where two findings cost the same.
3. The rest, such as speculative code in files that rarely change, and style the repository's rules require.

DO NOT rank by a tool's rating or by the number of findings in a file.

## 5. List every finding

READ [../formats/audit.md](../formats/audit.md). SET `not_read` of the audit with `python3 <skill dir>/scripts/better.pyz set .code/audit/<YYYY-MM-DD> audit` to what you did not read or run. ADD every finding, confirmed and unconfirmed, with `python3 <skill dir>/scripts/better.pyz add .code/audit/<YYYY-MM-DD> finding --by <your agent name>`, in the format's fields and in the order of step 4, with `evidence_ids` pointing to the records of step 2. The records are for agents that pick up a finding later: LIST every finding, however small, each with its evidence and a proposed task.

## 6. Report

REPORT in the conversation, USING `/write-better` for the wording if available:

1. Whether anything in the scope costs the user now, and what.
2. The five to ten findings of highest value, or every finding when there are fewer than five, highest value first, each with its effect on the GOAL and the proposed task.
3. How many `finding` records the audit holds, and the path of its folder.
4. What you did not read or run, such as history you could not see or checks that did not run.

DO NOT list the other findings in the report, not even as a short list of smaller items: the file holds them. OFFER to start the first proposed task with `/code-better`.
