# Where each property is tested

The file formats (typed JSON and JSONL, checked by `schema.py`) and the pages and scripts that read them share a set of
properties. This lists the test that keeps each one. A test is written as `file::Class`.

| Property | Where |
|---|---|
| A wrong type in any field (list, object, number, boolean, null, text) is one error, never an exception, in `check`, in `load` and on the page | `test_dashboard_formats.py::WrongTypes`, `::LessonsWrongTypes`; `test_board_formats.py::WrongTypes`, `::ConversationEvents`; `test_architect_formats.py::WrongTypes`; `test_show_schema.py::WrongTypes`. The wrong values come from `wrong_types.py`, and the page is drawn with the `render-*.js` scripts. |
| A missing optional field and a null are the same | `test_show_schema.py::Nulls`, `::SchemaAndShowAgree`; `test_architect_formats.py::NullIsAbsent`; `board.test.js` |
| A line that is not a record, NaN, Infinity, bytes that are not UTF-8 | `test_dashboard_formats.py::WrongTypes` (raw lines), `test_board_formats.py::RawFiles`, `test_architect_formats.py::RawLines` |
| Deep nesting (up to 50,000 levels) | `test_never_raise.py::DeepInput`, `::Loaders`; `test_show_schema.py::Nesting`; `test_schema.py` |
| A lone surrogate in any string or key | `test_never_raise.py::Surrogates` |
| Output that survives a strict stream, and any failure is one line with exit code 1 | `test_never_raise.py::Wrapper`, `::Injected`, `::ServedBrokenFiles` |
| A file changes between the read and the display | `test_dashboard_formats.py::Dashboard` (a line written after the read), `test_board_formats.py::Invalid` (what is shown is the text that was validated) |
| An invalid record stays listed, marked, with the rest of the folder intact | `test_dashboard_formats.py::OneBadRecordKeepsTheRest`, `::BaseFieldsOfEveryKind`; `test_board_formats.py::Stripped` |
| Questions merged into each other (self, loops, chains, out of scope) | `test_board_formats.py::MergeCycles`, `::BoardsOfSize` |
| A large folder loads in seconds | `test_board_formats.py::BoardsOfSize` |
| The schema files and the scripts that read the same file agree | `test_show_schema.py::SchemaAndShowAgree`, `::FilesThatAreNotSpecs`; `test_architect_formats.py::MovedChecks` |
| Every value a schema accepts is drawn without a crash | `test_architect_formats.py::EveryAcceptedExampleRenders`; `test_show_schema.py::ChildrenAndRenderCrashes` |
| Each schema keyword, pointer and cross-record rule | `test_schema.py` (`Keywords`, `Pointers`, `CrossRecord`, `Hooks`, `HookSafety`, `Schemas`) |
| The skill texts name the new files and tell the agent to check every write | `test_skill_text.py` |

## Adding a case

- A new wrong value goes in `wrong_types.py`; every test above that uses it picks it up.
- A new file kind needs an example record with its schema; `Examples` and `EveryAcceptedExampleRenders` then cover it. Add
  it to `KINDS` in `test_dashboard_formats.py` (or the matching table of the architect and board tests).
- A new script with a `main` is found by `test_never_raise.py` itself; it fails until the commands to run it with are listed
  there.
- A bug found by hand becomes a test of the same shape as its neighbours in the class above, written and seen failing
  before the fix.

## Python versions

Run the suite on the newest Python and on 3.10, the oldest CI runs (`uv run --no-project --python 3.10 python -I -m
unittest discover tests`). The deep-input tests only fail on 3.13 and older: newer `json` parses 50,000 levels without
recursing, so there they pass whatever the code does.
