"""Grade whether the agent loaded the skill by itself, in the condition that installs it without invoking it.

In `skill-installed`, the skill is installed but the request has no slash command, so the skill applies only
if the agent loads it. The `skill_loaded` scorer, separate from the rule's scorer, scores 1 when the agent, or a
sub-agent, called the harness's skill tool with the skill's name or read the skill's SKILL.md, and 0 otherwise.
It gives no score in other conditions. The report splits the condition's pass rate by it, so a failure from not
loading the skill is told apart from a failure with the skill loaded.

Which tool call loaded the skill is an exact fact, so a script decides it. The skill tool's name and the skills
folder come from the harness adapter (`agent.py`).
"""

from inspect_ai.model import ChatMessage, ChatMessageAssistant
from inspect_ai.scorer import Score, Scorer, Target, mean, scorer
from inspect_ai.solver import TaskState

from skill_evals.agent import READ_TOOL, SHELL_TOOL, SKILL_TOOL
from skill_evals.cases import SKILL_INSTALLED
from skill_evals.grading.reads import shell_paths, skill_path


def names_skill(value: object, skill: str) -> bool:
    """Return whether a tool argument names the skill, alone or with a plugin prefix such as `plugin:skill`."""
    return isinstance(value, str) and (value.strip().lstrip("/") == skill or value.endswith(f":{skill}"))


def loads_skill(function: str, arguments: dict[str, object], skill: str) -> bool:
    """Return whether one tool call loads the skill: the skill tool with its name, or a read of its SKILL.md."""
    if function == SKILL_TOOL:
        return any(names_skill(value, skill) for value in arguments.values())
    if function == READ_TOOL:
        return skill_path(skill).findall(str(arguments.get("file_path", ""))) == ["SKILL.md"]
    if function == SHELL_TOOL:
        return "SKILL.md" in shell_paths(str(arguments.get("command", "")), skill)
    return False


def loaded(messages: list[ChatMessage], skill: str) -> bool:
    """Return whether any assistant message, the agent's or a sub-agent's, loaded the skill."""
    return any(
        loads_skill(call.function, call.arguments or {}, skill)
        for message in messages
        if isinstance(message, ChatMessageAssistant)
        for call in message.tool_calls or []
    )


@scorer(metrics=[mean()])
def skill_loaded() -> Scorer:
    """Score 1 when a skill-installed run loaded the skill itself, 0 when not; no score in other conditions."""

    async def score(state: TaskState, target: Target) -> Score | None:
        if state.metadata["condition"] != SKILL_INSTALLED:
            return None
        was_loaded = loaded(state.messages, state.metadata["skill"])
        explanation = "Loaded the skill." if was_loaded else "Did not load the skill."
        return Score(value=int(was_loaded), explanation=explanation)

    return score
