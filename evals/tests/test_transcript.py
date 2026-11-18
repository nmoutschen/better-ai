"""Tests for skill_evals/transcript.py: stream-json events to Inspect messages, statistics and redaction."""

import json

from inspect_ai.model import ChatMessageAssistant, ChatMessageTool, ChatMessageUser

from skill_evals.transcript import REDACTED, parse_stream, redact

LEAKED_TOKEN = "sk-ant-oat01-" + "x" * 20


def stream(*events: dict) -> str:
    """Join events as Claude Code prints them, one JSON object per line."""
    return "\n".join(json.dumps(event) for event in events)


INIT = {"type": "system", "subtype": "init", "model": "claude-test", "claude_code_version": "2.1.327", "skills": ["x"]}
TEXT = {
    "type": "assistant",
    "message": {"id": "m1", "model": "claude-test", "content": [{"type": "text", "text": "Hi"}]},
}
CALL = {
    "type": "assistant",
    "message": {"id": "m1", "content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}}]},
}
FAILED = {
    "type": "user",
    "message": {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "t1",
                "is_error": True,
                "content": [{"type": "text", "text": "Exit code 2\nno"}],
            }
        ],
    },
}
RESULT = {
    "type": "result",
    "subtype": "success",
    "is_error": False,
    "result": "Done.",
    "duration_ms": 4200,
    "num_turns": 2,
    "total_cost_usd": 0.25,
    "usage": {
        "input_tokens": 10,
        "output_tokens": 20,
        "cache_read_input_tokens": 30,
        "cache_creation_input_tokens": 40,
    },
}


def test_events_become_messages() -> None:
    """Blocks of one API message merge into one assistant message; results keep their error flag."""
    run = parse_stream(stream(INIT, TEXT, CALL, FAILED, RESULT))
    assistant, tool = run.messages
    assert isinstance(assistant, ChatMessageAssistant) and assistant.text == "Hi"
    assert [(call.id, call.function, call.arguments) for call in assistant.tool_calls or []] == [
        ("t1", "Bash", {"command": "ls"})
    ]
    assert isinstance(tool, ChatMessageTool) and tool.function == "Bash" and tool.error is not None
    assert tool.text == "Exit code 2\nno"
    assert run.reply == "Done." and run.model == "claude-test" and run.error is None


def test_statistics() -> None:
    """Usage, cost, duration and turns come from the result event; the init event adds the version."""
    stats = parse_stream(stream(INIT, RESULT)).stats
    assert stats["usage"] == {
        "input_tokens": 10,
        "output_tokens": 20,
        "cache_creation_input_tokens": 40,
        "cache_read_input_tokens": 30,
    }
    assert (stats["total_cost_usd"], stats["duration_ms"], stats["num_turns"]) == (0.25, 4200, 2)
    assert stats["init"]["claude_code_version"] == "2.1.327"


def test_user_text_and_noise() -> None:
    """Plain user text, such as an expanded skill, becomes a user message; non-JSON lines are skipped."""
    skill = {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "Skill body"}]}}
    run = parse_stream("warning: not json\n" + stream(skill, RESULT))
    assert isinstance(run.messages[0], ChatMessageUser) and run.messages[0].text == "Skill body"


def test_errors() -> None:
    """A missing result event, or one marked as an error, sets the run's error."""
    assert parse_stream(stream(INIT, TEXT)).error == "Claude Code printed no result event"
    failed = {**RESULT, "is_error": True, "subtype": "success", "result": "API Error: 429"}
    assert "429" in (parse_stream(stream(failed)).error or "")


def test_redaction() -> None:
    """Token-shaped strings and given secrets never survive parsing."""
    leak = {**RESULT, "result": f"token {LEAKED_TOKEN} and secret-value"}
    run = parse_stream(stream(leak), secrets=("secret-value",))
    assert LEAKED_TOKEN not in run.reply and "secret-value" not in run.reply and run.reply.count(REDACTED) == 2
    assert redact("sk-ant-api03-abc_DEF-1") == REDACTED
