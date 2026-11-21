# What the verifiers' probes became

The verifiers of the agent-file-formats build (T1 to T11b, and the merge fix) each ran scripts and inputs of their own
to find what the builders missed. This lists every probe, and the test that now keeps what it found, or why none does.
"Covered" names a test that already existed on this branch when the probes were harvested; "new" names a test added by
the harvest. A test is written as `file::Class::test`.

Branch base: `feat/agent-file-formats` at 555f501. Two verified branches are not merged into it yet,
`feat/aff-t5c-board-loops` (merge loops, T5c) and `feat/aff-t7-architect` (the architect folder, T7). Each carries its own
tests for the probes of its task (named below); this branch cannot run them, so it holds no copy. After they merge, the
probes of T5c and T7 are kept by those tests.

## New tests

| Test | Probes it keeps |
|---|---|
| `test_dashboard_formats.py::LessonsWrongTypes` (9 tests) | `fuzz_t11.py`, `fuzz_t11b.py` |
| `test_dashboard_formats.py::BaseFieldsOfEveryKind` (3) | `v3/r8.py`, `v3b/r8.py` |
| `test_dashboard_formats.py::OneBadRecordKeepsTheRest` (3) | `v3/repro1.py`, `v3/repro2.py` (card, code.json), `v3b/repro.py` |
| `test_board_formats.py::ConversationEvents` (2) with `render-board-thread.js` | `probe_conv.py`, `js/thread.js` |
| `test_board_formats.py::RawFiles` (1) | `probe_t5b.py` |
| `test_board_formats.py::BoardsOfSize` (2) | `t5/perf.py` (timing, bound 30 s), `probe/probe.js` (merge into out of scope) |
| `test_deep_input.py::DeepInput` (1) | `fz4/deep.py` |
| `test_show_schema.py::SchemaAndShowAgree` (2) | `fz3/nulls.py`, the schema.py vs show.py agreement of decided 24 |
| `test_show_schema.py::FilesThatAreNotSpecs` (2) | `fz3/edge.py` |
| `test_schema.py::Keywords::test_a_boolean_is_not_the_number_it_equals_in_python` | `probe/p1.py` (last lines) |
| `board.test.js` (2 tests) | `nulldate/run.js` |

## Probes and repros, by folder

### T1, the validator
- `v1/probe.py`: A and B (then, nested if: the rule is named) covered by `test_schema.py::Keywords::test_a_rejection_in_then_names_the_rule` and `::test_a_nested_rule_keeps_its_own_name`; B2 (per-type dispatch with additionalProperties false) covered by `OneBadRecordPerKind` in `test_dashboard_formats.py`; C and C2 (relative path, `.`) covered by `Paths::test_a_relative_path_from_inside_the_folder_finds_its_schema` and `::test_dot_checks_the_current_folder`; D (U+2028) covered by `Lines::test_a_unicode_line_separator_inside_a_string_does_not_split_a_record`; E (folder with no schema file) covered by `Paths::test_a_folder_with_no_file_that_has_a_schema_is_an_error`; F (`not: true`) covered by `Keywords::test_not_with_a_non_object_schema_is_a_schema_error_not_a_traceback`.
- `probe/p1.py`: the if/then/else and sum-type cases are covered by `Keywords` (`test_if_then_else`, `test_all_of_any_of_not`, `test_r4_*`); boolean against number is new (above); an unsupported keyword nested in an unused property is covered by `SchemaAudit::test_an_unsupported_keyword_in_every_place_a_schema_nests`. See "Found while harvesting" for `const` with a list.

### T2, the conversation
- `t2/gen.py`: a generator of the schemas, not a probe.
- Verifier findings (fixtures still named answers.jsonl; usage lines omit `--text`) covered by `test_show_schema.py::DesignBetterFixtures` and `test_dashboard_formats.py::Usage::test_the_usage_line_for_accepted_shows_the_users_words`.

### T3, the code-better scripts
- `v3/ex.py`, `t5/fixture.py`: compare the fixtures with the spec page, which is not in this repo (`.architect/`). Not a test.
- `v3/r8.py`, `v3b/r8.py`: new (`BaseFieldsOfEveryKind`).
- `v3/race.py`: covered by `test_dashboard_formats.py::Dashboard::test_a_line_written_after_the_read_is_not_shown_unchecked`.
- `v3/repro1.py`, `v3/repro2.py`, `v3b/repro.py`: tasks and decisions that are invalid stay listed (covered by `Dashboard::test_a_folder_with_one_bad_task_still_shows_every_other_task`, `::test_a_broken_code_json_does_not_empty_the_task_list`, `::test_a_waiting_decision_with_a_bad_task_pointer_stays_so_the_user_can_answer_it`); the all-statuses task list, the pretty-printed card with a bad role and the code.json with a bad mode are new (`OneBadRecordKeepsTheRest`); a task with `requirements` as text and `mode` as a number covered by `WrongTypes::test_an_invalid_record_shows_without_the_fields_that_failed`.
- `t3c-repro/a`, `t3c-repro/b`, `t3c-at.js`: a task with a list id, a decision with a list `answer.event`, a decision with a numeric `at` that stopped the page: covered by `WrongTypes::test_no_wrong_type_breaks_check_load_or_the_page` (every field, every wrong value, drawn in node).
- `v4/fuzz.py`: the same property test, which `WrongTypes::test_no_wrong_type_breaks_check_load_or_the_page` is (it uses `wrong_types.variants`); the `RAW_LINES` of the probe are in `wrong_types.py`.

### T4, T4b, T4c, the code-better text
- `t4/mine.py`, `t4/audit_good.py`, `t4/convert_cases.py`, `t4/replays_jsonl.py`, `t4/theirs.py`, `t4/pytest.txt`, `t4/validate.txt`: the builder's drafts and one-off converters of the eval cases. Not probes.
- `t4b/replays.py` (every eval replay's `.code` JSON passes `schema.py check`): covered by `test_skill_text.py::CodeBetterTextTest::test_code_better_eval_files_under_code_pass_the_schema_check`.
- Verifier findings (checks that read only Markdown notes; an architect spec pointing to a code-better decision; coordinate rules): covered by `test_code_better_eval_note_checks_count_code_json_working_files`, `test_code_better_an_architect_spec_never_points_to_a_code_better_decision`, `test_code_better_a_solo_mode_can_record_a_question_and_the_spec_always_exists`.
- `t4c-sim/tasks-bad.jsonl`: a coordinate task that is done, a blocked task: covered by `StatusRules::test_a_coordinate_task_cannot_be_done_and_another_mode_cannot_be_merged` and `::test_a_blocked_task_names_its_reason_and_the_task_it_waits_on`.
- `vt4/`: a scratch repository for a verifier run. Not a test.

### T5, T5b, T5c, the research board scripts
- `t5/race.py`: covered by `test_board_formats.py::Invalid::test_what_is_shown_is_the_text_that_was_validated`.
- `t5/conv.py`: covered by `Invalid::test_the_conversation_is_checked_for_errors_too`.
- `t5/perf.py`: new (`BoardsOfSize::test_a_large_valid_board_loads_in_seconds_and_its_watch_tick_does_too`, scaled to 150 questions, 750 claims and 300 sources, with a bound of 30 s against about 0.3 s measured, so only a scan that went quadratic fails). `probe_t5c/timing.py`, `scale.py`, `probe.py perf`, `probe2.py perf`: timings of the merge-loop hook; covered after the merge of T5c by its `test_board_formats.py` test of 2,000 merged questions (`5d2f842`). Not on this base.
- `probe/probe1.py`: A (an invalid brief with status stopped still stops the watch) covered by `Invalid::test_an_invalid_brief_is_kept_marked_and_its_status_still_stops_the_watch`; B (an invalid question kept) covered by `Invalid::test_an_invalid_record_stays_on_the_board_marked_and_listed`; C (same-size same-mtime rewrite seen) is a statement about the scan cache (reproduced: the second load does not list the changed file): the scan reads each file once per tick (`Invalid::test_a_tick_scans_once_and_board_json_reuses_a_scan_until_a_file_changes`); a rewrite within one mtime tick is not asserted (see below).
- `probe/probe3.py`, `probe/probe.js`, `probe/probe2.js`, `probe/probe4.js`: a question merged into a missing one, into itself, in a cycle, into an out-of-scope one, with odd types: covered by `MergeCycles` (self merge, mutual merge drawn with its claims), `Stripped::test_a_kept_invalid_claim_with_a_list_question_does_not_crash_the_page` and `WrongTypes`; merged into an out-of-scope question is new (`BoardsOfSize::test_a_question_merged_into_an_out_of_scope_one_is_drawn_with_its_claims`).
- `probe_conv.py`, `js/thread.js`, `js/conv-payloads.json`, `js/sanity.json`: new (`ConversationEvents`: every kind of event, each field each wrong value, the thread built from the real `pageConversation`). The existing `WrongTypes` drew only three kinds and with a stand-in thread.
- `probe_t5b.py`: new (`RawFiles`: NaN, Infinity, 100,000-deep nesting, arrays and bad types in each kind of file; the served JSON; the page).
- `probe_t5c/probe.py`, `probe_t5c/probe_small.py`, `probe_t5c/claims.py`, `probe.py`, `probe2.py`, `probe3.py`, `scale.py`, `probe/` merge-loop cases (loops of 2, 3, 10, self, tail, malformed targets, dup ids): the hook is in `feat/aff-t5c-board-loops` only; its tests `MergeCycles` there (self, loop, tail, stray file with a question id, chain that ends, 2,000 merges, exact claims) keep them. Not on this base.
- `probe/` data folders (`arch-folder`, `bad-regex`, `board`, `oldboard`, `nested-if-then-enum`, `pointer-later-line`, `points-to-no-type`, `required-string`, `same-folder-pointer`, `sch`, `utf8-cut`, `x-check-unknown-unreached`, `x-files-string`, `b.json`, `c.json`): inputs of the T1 round probes. Their cases are the ones listed under T1 and `test_schema.py::SchemaAudit`, `::Retry` (utf8-cut: `Retry::test_a_first_read_that_is_not_utf8_is_retried_like_a_parse_failure`), `::Pointers` (pointer-later-line, same-folder-pointer, points-to-no-type: `Pointers::test_r6_a_pointer_into_the_same_file`, `SchemaAudit::test_a_pointer_without_its_file_and_type_is_refused`), `SchemaAudit::test_a_pattern_that_is_not_a_regex_is_refused`, `::test_required_must_be_a_list_of_strings`, `::test_x_files_must_be_a_list_of_strings`, `::test_a_check_that_names_no_registered_hook_is_refused_on_load` (x-check-unknown-unreached).
- `t5c-old/`, `t5c-js.txt`, `t5c-py.txt`: a copy of the base and the output of a run. Not probes.

### T6, T6b, the research-better text and eval boards
- `t6/convert.py`, `t6-tst.py`: the converter of the planted boards and the builder's draft of `test_skill_text.py`. Not probes.
- Verifier findings (pretty-printed record read by `board_lib`, `proposed_admitted` after a merge, template lines, `none` as a missing value, challenge owners): covered by `test_skill_text.py::ResearchBetterText` (`test_eval_board_lib_reads_a_pretty_printed_json_file`, `test_eval_board_lib_none_treats_the_string_none_as_missing`, `test_null_date_is_accepted_and_planted_in_the_missing_field_board`, `test_planted_challenge_questions_are_not_owned_by_the_answerer`, `test_every_planted_eval_board_passes_the_schema_check`).
- `nulldate/run.js`: new (`board.test.js`).
- `replay_notes.py`, `reasons.py`, `reasons2.py`, `schema_after.py`, `r-old.txt`, `r-new.txt`, `rn-old.txt`, `rn-new.txt`, `reasons-old.txt`, `reasons-new.txt`, `vc-old.txt`, `vc-new.txt`: grade every replay on two branches and compare the failed graders. A differential run of the evals' own graders, where the change was meant to differ in some cases: the repo's `evals/tests/test_research_replays.py` and `validate_cases` already run each replay and compare it to its expected outcome. Not a test.

### T7, the architect folder (branch `feat/aff-t7-architect`)
- `t7/fuzz.py`, `t7/nulls.py`, `t7/edge.py`, `t7/edge2.py`, `t7/specs.py`, `t7/survey.py`, `t7c/accnull.py`, `t7c/deep_arch.py`, `t7c/missing.py`, `t7c/only.py`, `t7c/gen.py`, `t7d/never.py`, `t7b-*.py`, `t7b-*.sh`, `t7b-*.json`, `t7b-rerun.py`, `t7b-fixtures.py`: covered by `tests/test_architect_formats.py` on that branch: `WrongTypes::test_no_wrong_type_breaks_check_load_or_the_page`, `RawLines`, `EveryAcceptedExampleRenders`, `NullIsAbsent` (every optional field null, through `diagram.py`), `DiagramCli::test_a_design_nested_very_deep_is_an_error_not_a_traceback`, `DiagramCli::test_whatever_raises_while_checking_or_rendering_is_one_line_and_exit_1`, `RequiredFiles`, `SpecsNeedRecords`, `GeneratedSpecs`, `LoadNeverRaises` (the source file that goes away), `MovedChecks::test_schema_check_alone_rejects_each_broken_design_and_architect_check_agrees`. Not on this base.
- `t7d/surr.py` (a lone surrogate, JSON escape `\ud800`, in a field schema.py accepts, which then breaks `architect.py`): no test yet. Open finding on T7: schema.py passes it and architect.py fails, so the two disagree. It is in code under test, and in a branch not on this base.
- `t7/convert_replays.py`, `t7/convert.py`, `t7/gen_schemas.py`, `t7/fix_old_tests.py`, `t7/new_head.py`, `t7/new_rest.py`, `t7/old_head.py`, `t7/old_rest.py`, `t7/rest_view.txt`, `t7/specs.py`, `t7/o.txt`, `t7/*.json`, `t7/out-*`, `t7/*-v.txt`, `t7b-*` data and outputs, `t7c/` JSON and outputs, `t7d/` outputs, `out-*.txt`, `t7b-base-diagram.py` (the old diagram.py): converters, generators and outputs. Not probes.

### T8, show-better
- `fz/fuzz.py`, `fz/classify.py`, `fz3/repro.py`, `fz4/same.py`, `baseline.py`, `t8/diff.py`, `old_show.py`, `old_show/`, `oldshow/`: old against new `show.py check` and render. The change was meant to differ (the schema now refuses what show.py once accepted), so the old behaviour is not the reference: not tests. What each found is kept as a property of the new code: no check or render raises (`test_show_schema.py::WrongTypes::test_every_leaf_of_every_valid_spec_set_to_a_wrong_value_gives_an_answer_and_no_exception`), and the accepted shapes that crashed the renderer are refused (`ChildrenAndRenderCrashes::test_the_values_the_renderer_could_not_draw_are_refused`).
- `fz/misc.py`, `fz/real.py`, `fz/specs.txt`, `fz/out_*.txt`, `fz/crash*.json`, `fz/d/`: nulls on optional fields (covered by `Nulls`, `NULLABLE`/`NOT_NULLABLE`) and a run over real specs on disk, which are not in the repo. Not a test.
- `fz3/fuzz3.py`: covered by the leaf property test above, plus one new `SchemaAndShowAgree` test.
- `fz3/nulls.py`: new (`SchemaAndShowAgree::test_a_null_is_judged_the_same_by_the_schema_file_check_and_by_show_py`).
- `fz3/depth.py`, `fz3/tree.py`, `fz3/tree2.py`: covered by `Nesting` (tree 5 to 50,000 deep, command line) and `ChildrenAndRenderCrashes` (`test_a_leaf_with_an_empty_children_list_and_a_value_renders`, `test_a_node_without_a_non_empty_children_list_needs_a_value`).
- `fz3/edge.py`: new (`FilesThatAreNotSpecs`).
- `fz4/deep.py`: new (`test_deep_input.py::DeepInput`: 950 and 50,000 levels, list and object, in a show spec, a show conversation, the dashboard, the board, through every command that reads them).
- `v3b/repro.js` (a task with `requirements` as text or `mode` as a number throws in the dashboard page): covered by `test_dashboard_formats.py::WrongTypes::test_no_wrong_type_breaks_check_load_or_the_page`, which draws every payload through `render-payloads.js` (`drawTasks`, `drawAgents`), and by `::test_an_invalid_record_shows_without_the_fields_that_failed` on the Python side.
- `fz3/e/`, `fz3/d/`, `fz4/w/`, `fz3/out*.txt`: inputs and outputs written by those scripts. Not probes.
- `t8/n.txt`, `t8/o.txt`, `t8/old/`, `t8/r/`, `t8tree/`: outputs and a copy of the tree. Not probes.

### T11, T11b, lessons
- `fuzz_t11.py`, `fuzz_t11b.py`, `t11b-payloads.json`: new (`LessonsWrongTypes`: each field each wrong value, missing fields, a dangling task, an extra field, a repeated id, raw lines, NaN, 50,000-deep list and object, bad UTF-8; `load`, `check` exit code, and the page drawing over 100 payloads). The tests assert the expected outcome of each case from the spec (R16: every invalid line is an error on `lessons.jsonl`, and `check` exits 1), not the oracle of the scripts, which missed valid string values.
- Existing: `test_lessons.py` and `test_dashboard_formats.py::Dashboard::test_an_invalid_lessons_file_is_listed_by_load_and_by_check`.

### Merge fix
- The verifier's check (the duplicate `realEsc`) is `node --test tests/*.test.js`, which cannot load a file that declares it twice. Covered. `merge/`, `merged/`, `base/`, `old/`, `pre/`, `old_test_*.py`, `names_*.txt`, `pt*.js`, `union.txt`, `py.txt`, `node.txt`, `ut*.txt`: copies of trees and test lists, used to compare test names before and after a merge. Not probes.

## Scratchpad files judged not to be probes

Briefs and notes: `builder-t1.md` to `builder-t11b.md`, `builder-t10.md`, `verifier-t*.md` (copies of the logs read here), `final-pass-notes.md`, `audit/`, `spec*.txt`, `specpage.txt`, `spec-page.txt`. Spec-page generators and editors (the formats page and its schemas): `formats/`, `archjson.py`, `atomic.py`, `conform.py`, `examples.py`, `flatten.py`, `purpose.py`, `request.py`, `spec.py`, `status_ast.py`, `extract.js`, `extract-t3.js`, `gen_schema.py`, `gen-schemas-t3.py`, `new_funcs.py`, `apply.py`, `cmp.py`, `post_audit*.py`. Copies of the validator and its tests at one commit: `base-schema.py`, `schema_t3.py`, `t3schema.py`, `t5schema.py`, `t_a.py`, `t_b.py`, `base-v.txt`, `new-v.txt`, `prof`, `p.prof`, `p0.json`, `bd/`, `board-copy/`, `lint/`, `__pycache__/`. Copies of repo tests and of the copies-check step of the workflow, at one commit: `pt.js`, `pt_*.js`, `old_test_page.py`, `old_test_skill_text.py`, `t7c-copies.sh`, `t7b-copies.sh`. Outputs: `t4b-checks.txt`, `t4c-checks.txt`, `t7b-unit.txt`, `t7d-checks.txt`, `out-*.txt`.

## Python versions

Run on 3.15 (`python3`) and 3.10 (`uv run --no-project --python 3.10`, CI's oldest). On 3.10 only the two `DeepInput` show-pending cases fail (below).

The deep-input tests bite on different versions. `test_deep_input.py::DeepInput`, `test_show_schema.py::Nesting` and the 50,000-deep cases in `test_schema.py` only bite on Python 3.13 and older: 3.15's `json` parses 50,000 levels without recursing, so there they pass whatever the code does. `test_show_schema.py::FilesThatAreNotSpecs` has a case for each: "a tree 1200 deep" is past what 3.10's `json` reads, so on 3.10 it ends at the read and never reaches `show.check`, but on 3.15 it does, and it fails if `show.check` does not catch the recursion; "a tree 300 deep" is read by both, so it reaches `show.check` on 3.10 and fails there. Shown by replacing the body of `show.check` with `return check_spec(spec)` in a copy: the test fails on 3.15 (1200 case) and on 3.10 (300 case), and passes on the real code.

## Found while harvesting

- `show.py pending` raises RecursionError on a `conversation.jsonl` line nested 50,000 deep, on Python 3.10: `page.py` `events()` calls `json.loads` and does not catch it. `test_deep_input.py::DeepInput::test_no_command_prints_a_traceback_for_a_deeply_nested_file` fails on 3.10 for the two 50,000-deep cases (list and object) because of it, and is left as it is until the code is fixed in another task.

- `schema.py` compares a list or object `const` and `enum` with Python equality, so `{"const": [true]}` accepts `[1]` (`probe/p1.py`: `validate_instance([1], {"const": [True]}, {})` gives no error). A scalar `true` against `1` is refused (tested). No schema uses a list `const`, so no input is affected today. Code under test, so unchanged here.
- A rewrite of a file that keeps its size and mtime (`probe/probe1.py` C) is not seen by the board's scan cache. Not asserted by any test, and not known to happen in use (it needs a rewrite of the same length within one mtime tick). Code under test, so unchanged here.
