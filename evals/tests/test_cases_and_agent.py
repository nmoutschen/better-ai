"""Tests for skill_evals/cases.py and the parts of skill_evals/agent.py that need no sandbox or model."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from inspect_ai.model import ChatMessageAssistant

from skill_evals import agent, cases
from skill_evals.transcript import Run


def test_condition_prompts() -> None:
    """no-skill is the request, skill the slash command, one-sentence the request plus the rule's sentence."""
    assert cases.condition_prompt("Fix it.", "no-skill", "code-better") == "Fix it."
    assert cases.condition_prompt("Fix it.", "skill", "code-better") == "/code-better Fix it."
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


def test_invalid_skill_name() -> None:
    """Skill names are plain folder names."""
    with pytest.raises(ValueError):
        cases.case_dirs("../skills")


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
    for path, source in case["files"].items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_bytes(source.read_bytes())
    subprocess.run(["bash", "-ec", agent.START_SCRIPT, "bash"], cwd=tmp_path, check=True, capture_output=True)

    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True, text=True).stdout

    assert git("log", "--format=%s").splitlines() == ["Count refunds in the monthly total", "Planted repository"]
    assert git("show", "HEAD:sales.py") == (cases.CASES / "do-better/refund-total-user-right/repo/sales.py").read_text()
    assert "test_sales.py" not in git("ls-tree", "--name-only", "HEAD~1")
    assert not (tmp_path / ".earlier").exists() and git("status", "--porcelain") == ""


def write_tree(root: Path, files: dict[str, str]) -> None:
    """Write each file under root, creating folders."""
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)


def plant(case: dict, target: Path) -> None:
    """Copy a loaded case's files into target, as the sandbox receives them."""
    for path, source in case["files"].items():
        (target / path).parent.mkdir(parents=True, exist_ok=True)
        (target / path).write_bytes(source.read_bytes())


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
            "case.yaml": "id: history-case\nrule: r\nsituation: s\nrequest: r\ngraders: []\n",
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
    plant(case, work)
    subprocess.run(["bash", "-ec", agent.START_SCRIPT, "bash"], cwd=work, check=True, capture_output=True)

    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=work, check=True, capture_output=True, text=True).stdout

    expected = ["Raise the tax rate", "Start the shop"]
    assert git("log", "--format=%s").splitlines() == (["Planted repository", *expected] if final_differs else expected)
    first = git("log", "--reverse", "--format=%an|%ae|%at|%ct").splitlines()[0]
    stamp = int(datetime(2026, 3, 1, 10, tzinfo=UTC).timestamp())
    assert first == f"Ana|ana@example.invalid|{stamp}|{stamp}"
    assert sorted(git("ls-tree", "--name-only", "HEAD").split()) == sorted(final)
    assert git("show", "HEAD:tax.py") == "RATE = 0.21\n"
    assert not (work / ".history").exists() and git("status", "--porcelain") == ""


def test_history_rejects_bad_steps(tmp_path: Path) -> None:
    """A history step needs a message, sets only author and date, and a case has earlier/ or history/, not both."""
    base = {"case.yaml": "id: c\nrule: r\nsituation: s\nrequest: r\ngraders: []\n", "repo/a.py": "a = 1\n"}
    for extra, error in (
        ({"history/01/files/a.py": "a = 0\n"}, "no message.txt"),
        ({"history/01/message.txt": "m\n", "history/01/commit.env": "GIT_DIR=/tmp\n"}, "GIT_DIR"),
        ({"history/01/message.txt": "m\n", "earlier/message.txt": "m\n"}, "not both"),
    ):
        case_dir = tmp_path / error.replace(" ", "-").replace(".", "")
        write_tree(case_dir, {**base, **extra})
        with pytest.raises(ValueError, match=error):
            cases.load_case(case_dir)
