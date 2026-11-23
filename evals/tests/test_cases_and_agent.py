"""Tests for skill_evals/cases.py and the parts of skill_evals/agent.py that need no sandbox or model."""

import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from conftest import git, plant_dir, write_case, write_tree
from inspect_ai.model import ChatMessageAssistant

from skill_evals import agent, cases
from skill_evals.transcript import Run


def test_condition_prompts() -> None:
    """no-skill is the request, skill the slash command, one-sentence the request plus the rule's sentence."""
    assert cases.condition_prompt("Fix it.", "no-skill", "code-better") == "Fix it."
    assert cases.condition_prompt("Fix it.", "skill", "code-better") == "/code-better Fix it."
    assert cases.condition_prompt("Fix it.", "skill-installed", "write-better") == "Fix it."
    assert cases.condition_prompt("Fix it.", "one-sentence", "code-better", "Ask first.") == "Fix it.\n\nAsk first."
    with pytest.raises(ValueError):
        cases.condition_prompt("Fix it.", "one-sentence", "code-better")


def test_parse_conditions() -> None:
    """Conditions come as one name, a comma list or a list; unknown names fail."""
    assert cases.parse_conditions("no-skill,skill, one-sentence") == ["no-skill", "skill", "one-sentence"]
    assert cases.parse_conditions(["skill"]) == ["skill"]
    with pytest.raises(ValueError):
        cases.parse_conditions("unknown-condition")


def test_samples_per_case_and_condition() -> None:
    """One sample per case and condition; one-sentence only for rules with a sentence; the fake run only when asked."""
    sentences = cases.source_sentences("code-better")
    all_cases = cases.load_cases("code-better")
    found = cases.samples("code-better", ["no-skill", "one-sentence"])
    assert len(found) == len(all_cases) + sum(case["source"][0] in sentences for case in all_cases)
    sample = cases.samples("code-better", ["skill"], case_ids=["clinic-matching"], scripted=True)[0]
    assert sample.id == "clinic-matching-skill" and str(sample.input).startswith("/code-better ")
    assert sample.metadata and sample.metadata["condition"] == "skill"
    assert sample.metadata["scripted_run"]["actions"] is not None
    assert "scripted_run" not in (
        cases.samples("code-better", ["no-skill"], rule="bounded-repair-loop")[0].metadata or {}
    )


def test_unknown_case_id_or_skill_fails() -> None:
    """A case id or skill that matches no case folder is an error that names it; a skill name is a plain folder name."""
    with pytest.raises(ValueError, match="invoice-half-upp"):
        cases.samples("code-better", ["no-skill"], None, ["invoice-half-up", "invoice-half-upp"])
    with pytest.raises(ValueError, match="nonexistent-skill"):
        cases.case_dirs("nonexistent-skill")
    with pytest.raises(ValueError, match="Invalid skill name"):
        cases.case_dirs("../skills")


VALID_CASE = "id: a-case\nrule: some-behaviour\nsituation: S.\nrequest: R.\ngraders:\n  - type: notes_only\n"


def test_case_yaml_keys_are_checked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid case loads; an unknown top-level key, a grader field or type with no implementation, or an id that is not the folder fails."""
    folder = write_case(tmp_path, VALID_CASE)
    (folder / "repo" / "__pycache__").mkdir()
    (folder / "repo" / "__pycache__" / "main.cpython-312.pyc").write_bytes(b"x")
    loaded = cases.load_case(folder)
    assert loaded["id"] == "a-case"
    assert list(loaded["files"]) == ["main.py"], "a Python cache left in a planted repo is not part of the case"
    with pytest.raises(ValueError, match="a-case.*read"):
        cases.load_case(write_case(tmp_path / "1", VALID_CASE + "read: [SKILL.md]\n"))
    with pytest.raises(ValueError, match="a-case.*paterns"):
        cases.load_case(write_case(tmp_path / "2", VALID_CASE + "  - type: ran_command\n    paterns: x\n"))
    nested = VALID_CASE + "  - type: any_of\n    graders:\n      - type: file_contains\n        pth: main.py\n"
    with pytest.raises(ValueError, match="a-case.*pth"):
        cases.load_case(write_case(tmp_path / "3", nested))
    with pytest.raises(ValueError, match="a-case.*other-name"):
        cases.load_case(write_case(tmp_path / "4", VALID_CASE.replace("id: a-case", "id: other-name")))
    monkeypatch.setitem(cases.GRADER_FIELDS, "bogus", ())
    with pytest.raises(ValueError, match="a-case.*bogus.*no implementation"):
        cases.load_case(write_case(tmp_path / "5", VALID_CASE + "  - type: bogus\n"))


def test_token_errors_never_show_the_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Either variable works; the error for a missing one names the variables only."""
    for name in agent.TOKEN_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError, match="CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_AUTH_TOKEN"):
        agent.subscription_token()
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sk-ant-oat01-abc")
    assert agent.subscription_token() == "sk-ant-oat01-abc" and agent.secrets() == ("sk-ant-oat01-abc",)


def test_record_run() -> None:
    """The prompt comes first, then the converted messages; the reply is the output."""
    state = type("State", (), {"metadata": {}})()
    run = Run(messages=[ChatMessageAssistant(content="Hi")], reply="Done.", model="m", stats={"num_turns": 1})
    agent.record_run(state, run, "Fix it")  # type: ignore[arg-type]
    assert [message.text for message in state.messages] == ["Fix it", "Hi"]
    assert state.output.completion == "Done." and state.metadata["claude_code"] == {"model": "m", "num_turns": 1}


def test_image_pins_the_same_claude_code_version() -> None:
    """The Dockerfile and the run metadata name the same Claude Code version."""
    assert agent.dockerfile_version() == agent.CLAUDE_CODE_VERSION


def test_image_pins_the_ruff_of_the_lock_file() -> None:
    """The sandbox's ruff is the one case replays use locally, and the image tag names both versions."""
    import re
    import tomllib

    sandbox_dir = agent.Path(agent.__file__).with_name("sandbox")
    pinned = re.search(r"^ARG RUFF_VERSION=(\S+)$", (sandbox_dir / "Dockerfile").read_text(), re.M)
    locked = tomllib.loads((cases.EVALS / "uv.lock").read_text())["package"]
    ruff = next(package["version"] for package in locked if package["name"] == "ruff")
    assert pinned and pinned[1] == ruff
    assert f"claude-{agent.CLAUDE_CODE_VERSION}-ruff-{ruff}" in (sandbox_dir / "compose.yaml").read_text()


def test_short_skill_holds_every_sentence_under_the_real_frontmatter() -> None:
    """The short skill keeps the real name and description, and its body is every rule sentence."""
    text = cases.short_skill("code-better")
    assert text.startswith("---\nname: code-better\n")
    for sentence in cases.source_sentences("code-better").values():
        assert f"- {sentence}" in text
    assert cases.condition_prompt("Fix it.", "short-skill", "code-better") == "/code-better Fix it."


def test_earlier_work_is_the_last_commit(tmp_path: Path) -> None:
    """A case with earlier/ starts with two commits: the files before that work, then the planted repository."""
    case = cases.load_case(cases.CASES / "do-better" / "refund-total-user-right")
    plant_dir(case, tmp_path)
    subprocess.run(["bash", "-ec", agent.START_SCRIPT, "bash"], cwd=tmp_path, check=True, capture_output=True)

    assert git(tmp_path, "log", "--format=%s").splitlines() == [
        "Count refunds in the monthly total",
        "Planted repository",
    ]
    sales = (cases.CASES / "do-better/refund-total-user-right/repo/sales.py").read_text()
    assert git(tmp_path, "show", "HEAD:sales.py") == sales
    assert "test_sales.py" not in git(tmp_path, "ls-tree", "--name-only", "HEAD~1")
    assert not (tmp_path / ".earlier").exists() and git(tmp_path, "status", "--porcelain") == ""


@pytest.mark.parametrize("final_differs", [True, False])
def test_history_is_planted_commit_by_commit(tmp_path: Path, final_differs: bool) -> None:
    """A case with history/ starts with one commit per step, in name order, with the step's author and date.

    The planted repository is a last commit only when it differs from the last step.
    """
    case_dir, work = tmp_path / "case", tmp_path / "work"
    final = {"tax.py": "RATE = 0.21\n", "README.md": "Shop\n"}
    write_tree(
        case_dir,
        {
            "case.yaml": "id: case\nrule: r\nsituation: s\nrequest: r\ngraders: []\n",
            **{f"repo/{path}": text for path, text in final.items()},
            "history/01-start/files/tax.py": "RATE = 0.2\n",
            "history/01-start/files/old.py": "x = 1\n",
            "history/01-start/message.txt": "Start the shop\n",
            "history/01-start/commit.env": "GIT_AUTHOR_NAME=Ana\nGIT_AUTHOR_EMAIL=ana@example.invalid\n"
            "GIT_AUTHOR_DATE=2026-03-01T10:00:00+00:00\n",
            "history/02-rate/files/tax.py": "RATE = 0.21\n",
            "history/02-rate/message.txt": "Raise the tax rate\n",
        },
    )
    if not final_differs:
        write_tree(case_dir, {"history/02-rate/files/README.md": "Shop\n"})
        (case_dir / "history/01-start/files/old.py").unlink()
    case = cases.load_case(case_dir)
    work.mkdir()
    plant_dir(case, work)
    subprocess.run(["bash", "-ec", agent.START_SCRIPT, "bash"], cwd=work, check=True, capture_output=True)

    expected = ["Raise the tax rate", "Start the shop"]
    assert git(work, "log", "--format=%s").splitlines() == (
        ["Planted repository", *expected] if final_differs else expected
    )
    first = git(work, "log", "--reverse", "--format=%an|%ae|%at|%ct").splitlines()[0]
    stamp = int(datetime(2026, 3, 1, 10, tzinfo=UTC).timestamp())
    assert first == f"Ana|ana@example.invalid|{stamp}|{stamp}"
    assert sorted(git(work, "ls-tree", "--name-only", "HEAD").split()) == sorted(final)
    assert git(work, "show", "HEAD:tax.py") == "RATE = 0.21\n"
    assert not (work / ".history").exists() and git(work, "status", "--porcelain") == ""


def test_history_rejects_bad_steps(tmp_path: Path) -> None:
    """A history step needs a message, sets only author and date, and a case has earlier/ or history/, not both."""
    base = {"repo/a.py": "a = 1\n"}
    for extra, error in (
        ({"history/01/files/a.py": "a = 0\n"}, "no message.txt"),
        ({"history/01/message.txt": "m\n", "history/01/commit.env": "GIT_DIR=/tmp\n"}, "GIT_DIR"),
        ({"history/01/message.txt": "m\n", "earlier/message.txt": "m\n"}, "not both"),
    ):
        case_dir = tmp_path / error.replace(" ", "-").replace(".", "")
        case_yaml = f"id: {case_dir.name}\nrule: r\nsituation: s\nrequest: r\ngraders: []\n"
        write_tree(case_dir, {**base, **extra, "case.yaml": case_yaml})
        with pytest.raises(ValueError, match=error):
            cases.load_case(case_dir)


def test_default_conditions_follow_the_skill_kind() -> None:
    """A behavioural skill also runs skill-installed by default; a procedural one does not."""
    assert cases.skill_kind("write-better") == "behavioural"
    assert cases.skill_kind("code-better") == "procedural"
    assert cases.default_conditions("write-better") == ["no-skill", "skill", "short-skill", "skill-installed"]
    assert cases.default_conditions("code-better") == ["no-skill", "skill", "short-skill"]


def test_every_skill_declares_its_kind() -> None:
    """Every skill in the repository has metadata.kind in its frontmatter."""
    for skill_md in sorted((cases.REPO / "skills").glob("*/SKILL.md")):
        assert cases.skill_kind(skill_md.parent.name) in cases.KINDS


def test_sandbox_images_are_pinned() -> None:
    """Node and tinyproxy are pinned to exact versions, and the proxy image tag names the tinyproxy version."""
    import re

    sandbox_dir = agent.Path(agent.__file__).with_name("sandbox")
    assert re.search(r"^FROM node:22\.\d+\.\d+-bookworm-slim AS node$", (sandbox_dir / "Dockerfile").read_text(), re.M)
    proxy = (sandbox_dir / "proxy.Dockerfile").read_text()
    tinyproxy = re.search(r"apk add --no-cache tinyproxy=(\S+)", proxy)
    assert tinyproxy
    assert f"image: better-ai-evals-proxy:tinyproxy-{tinyproxy[1]}\n" in (sandbox_dir / "compose.yaml").read_text()


async def test_agent_timeout_is_a_sample_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A run cut off at the timeout raises, naming the timeout, instead of being scored as a finished run."""

    async def fake_cli(*args: object, **options: object) -> tuple[str, str, bool]:
        return '{"type": "assistant", "message": {"id": "m", "content": []}}', "", True

    monkeypatch.setattr(agent, "sandbox", lambda: None)
    monkeypatch.setattr(agent, "claude_cli", fake_cli)
    monkeypatch.setattr(agent, "secrets", lambda: ())
    state = type("State", (), {"metadata": {}, "input_text": "Fix it"})()
    solve = agent.claude_code(timeout=7)
    with pytest.raises(RuntimeError, match="timed out after 7 seconds"):
        await solve(state, None)  # type: ignore[arg-type]


def test_lint_cases_grade_the_lint_run_with_the_judge() -> None:
    """Each code-better lint case judges whether ruff ran after the last edit with the shared rubric plus its own sentences."""
    assert "ran_after_last_edit" not in cases.GRADER_FIELDS
    shared = " ".join((cases.CASES / "code-better/_rubrics/lint-ruff-ran-after-last-edit.md").read_text().split())
    for phrase in (
        "ruff",
        "PASS only if",
        "FAIL",
        "whether or not a ruff check follows the pop",
        "The ruff check that counts is the last one run on the agent's final code",
        "A run by a sub-agent the agent started counts.",
        "that leaves a .py file different from the agent's own code before the command",
        "the last `ruff check` run on the agent's own code (not on the planted code while its changes were set aside)",
        "any tool call or command that writes or changes a .py file in the repository, such as",
        "Edits by a sub-agent the agent started count as edits too.",
        "the file edit and file write tools",
    ):
        assert phrase in shared, phrase
    assert "different from what the last ruff check saw" not in shared
    directories = [path for path in cases.case_dirs("code-better") if path.name.startswith("lint-")]
    assert len(directories) == 7
    for directory in directories:
        graders = cases.load_case(directory)["graders"]
        types = [grader["type"] for grader in graders]
        assert "ran_after_last_edit" not in types and "command_passes" in types, directory.name
        assert "planted_unchanged" in types, directory.name
        rubrics = [grader["rubric"] for grader in graders if grader["type"] == "judge"]
        assert len(rubrics) == 1 and " ".join(rubrics[0].split()).startswith(shared), directory.name
        assert "Planted facts of this case:" in rubrics[0], directory.name


def test_agent_metadata_flags_a_dirty_skill_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The run metadata records whether the skill's folder had uncommitted changes."""
    folder = tmp_path / "skills" / "demo"
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text("one\n")
    for command in (("init", "-q"), ("add", "."), ("commit", "-qm", "x")):
        git(tmp_path, *command)
    monkeypatch.setattr(agent, "REPO", tmp_path)
    assert agent.agent_metadata("fake", "m", "demo")["skill_dirty"] is False
    (folder / "SKILL.md").write_text("two\n")
    assert agent.agent_metadata("fake", "m", "demo")["skill_dirty"] is True


def test_run_ends_after_result_event_although_a_background_shell_runs(tmp_path: Path) -> None:
    """A CLI that printed its final result but stays open, like `claude -p` with a background server, is ended."""
    fake = tmp_path / "fake-claude"
    fake.write_text(
        "#!/bin/sh\n"
        'echo \'{"type":"assistant","text":"a quoted \\"type\\":\\"result\\" does not end the run"}\'\n'
        "sleep 2\n"
        'echo \'{"type":"result","stop_reason":"end_turn"}\'\n'
        "exec sleep 600\n"
    )
    fake.chmod(0o755)
    out = tmp_path / "run.out"
    script = agent.end_after_result(f"{fake} > {out} < /dev/null", str(out), quiet=1, poll=0.2, grace=0.5)
    started = time.monotonic()
    subprocess.run(["sh", "-c", script], check=False, timeout=30)
    elapsed = time.monotonic() - started
    # Ended after the real result (printed at 2 s), not after the quoted look-alike, and not at the timeout.
    assert 2 < elapsed < 8
    assert out.read_text().splitlines()[-1] == '{"type":"result","stop_reason":"end_turn"}'


def test_run_continues_when_events_follow_a_result(tmp_path: Path) -> None:
    """A result followed by another turn, as when a background task finishes, does not end the run early."""
    fake = tmp_path / "fake-claude"
    fake.write_text(
        "#!/bin/sh\n"
        'echo \'{"type":"result","stop_reason":"end_turn"}\'\n'
        "sleep 0.2\n"
        'echo \'{"type":"assistant","text":"a background task finished"}\'\n'
        "sleep 1.9\n"
        'echo \'{"type":"result","stop_reason":"end_turn","turn":2}\'\n'
    )
    fake.chmod(0o755)
    out = tmp_path / "run.out"
    script = agent.end_after_result(f"{fake} > {out} < /dev/null", str(out), quiet=1.5, poll=0.2, grace=0.5)
    subprocess.run(["sh", "-c", script], check=False, timeout=30)
    assert out.read_text().splitlines()[-1] == '{"type":"result","stop_reason":"end_turn","turn":2}'
