"""Generic eval mechanics. Knows nothing about any particular skill.

Users invoke these skills by name, so the question is the effect: how does the output change on
each dimension of "better"? There is no single score and there are no gold answers. Each dimension
is compared between the skill and a baseline, so a gain on one cannot hide a loss on another.
"""

import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from statistics import mean, stdev
from urllib.parse import urlparse

from deepeval.metrics import JevEval
from deepeval.metrics.jev_eval.questions import Choice, Score
from deepeval.models.system_one.typesafe_model import TypeSafeModel
from deepeval.test_case import LLMTestCase, SingleTurnParams


REPO = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO / "skills"
LEVELS = ["Not met", "Partly met", "Fully met"]
MAX_STEP_RESULT_CHARS = 1500  # Keeps long search results within the judge's context.
READ_ONLY_TOOLS = "Read,Glob,Grep"  # Limited to the empty project unless a run grants more.
METRICS = (
    "words",
    "length_ratio",
    "seconds",
    "output_tokens",
    "searches",
    "domains",
    "new_search_terms",
    "terms_from_results",
    "later_searches",
)


# What a suite declares ----------------------------------------------------------------


@dataclass(frozen=True)
class Matches:
    """A regex that must match (or, with expect=False, must not match)."""

    dimension: str
    pattern: str
    expect: bool = True


@dataclass(frozen=True)
class Judged:
    """A question the judge scores while seeing the task and the output.

    Set sees_task=False if the task could supply the answer, such as what a reader can learn.
    """

    dimension: str
    question: str
    sees_task: bool = True
    first_sentences: int | None = None  # Show only the opening. Requires sees_task=False.
    first_searches: bool = False  # Show only the searches sent before any result. Likewise.


@dataclass(frozen=True)
class OnTrajectory:
    """A question the judge scores while seeing every step the agent took, in order.

    Set searches_only=True to hide the agent's messages and answer, which can make a run that
    stopped early look thorough.
    """

    dimension: str
    question: str
    searches_only: bool = False


@dataclass(frozen=True)
class ReaderAnswers:
    """A question answered from the output alone, as a reader would have to.

    """

    dimension: str
    question: str
    options: dict[str, str]
    correct: str


@dataclass(frozen=True)
class Bound:
    """A limit on a measured value, such as words or distinct source domains."""

    dimension: str
    metric: str
    low: float | None = None
    high: float | None = None


Check = Matches | Judged | OnTrajectory | ReaderAnswers | Bound


@dataclass(frozen=True)
class Damage:
    """A negative test: known damage to a real run must lower one dimension's score.

    Damaging real runs needs no hand-written right answer.
    """

    dimension: str
    name: str
    apply: Callable[["Trace"], "Trace"]


@dataclass(frozen=True)
class Effect:
    """One task, in one of two forms.

    - previous_reply: the skill is invoked alone, on the agent's previous reply.
    - text: the skill is invoked with this as its argument. The baseline sends the prompt, or
      asks for a rewrite if there is none.
    """

    id: str
    checks: tuple[Check, ...]
    prompt: str = ""
    tools: tuple[str, ...] = ()
    damages: tuple[Damage, ...] = ()
    holdout: bool = False  # Excluded while iterating on a skill. See Settings.holdout.
    # With previous_reply, the prompt is what the baseline arm types as its second turn.
    previous_reply: str | None = None
    text: str | None = None

    @property
    def task(self) -> str:
        """The task as the judge sees it."""
        if self.text is not None and self.prompt:
            return self.prompt
        document = self.previous_reply if self.previous_reply is not None else self.text
        if document is None:
            return self.prompt
        return (
            "The user asked the agent to rewrite this document so that they can read it "
            f"themselves.\n\nDocument:\n{document}"
        )


@dataclass(frozen=True)
class SkillEval:
    skill: str
    effects: tuple[Effect, ...]
    shared_checks: tuple[Check, ...] = ()  # Applied to every effect in this suite.
    shared_damages: tuple[Damage, ...] = ()  # Applied to effects scoring that dimension.
    report_only: tuple[str, ...] = ()  # Dimensions too unreliable to fail a test.


@dataclass(frozen=True)
class Settings:
    model: str = "claude-sonnet-5-5"
    judge_model: str = "clef-flash"
    ollama_host: str = "http://localhost:11434"
    samples: int = 3  # Agent runs per arm, per effect.
    holdout: bool = False  # Include held-out cases. Leave off while iterating on a skill.
    min_difference: float = 0.1  # Smaller differences between arms are never reported.

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            ollama_host=os.environ.get("OLLAMA_HOST", cls.ollama_host),
            samples=int(os.environ.get("EVAL_SAMPLES", cls.samples)),
            holdout=os.environ.get("EVAL_HOLDOUT") == "1",
        )


# Running the agent --------------------------------------------------------------------


class FailedRun(Exception):
    """The agent did not produce a usable output. This is not a low score for the output."""


class JudgeError(Exception):
    """The judge failed to answer. This is not a low score for the output."""


@dataclass
class Trace:
    """Everything observed from one agent run."""

    output: str
    source: str = ""  # The text being rewritten, if any.
    session_id: str = ""
    seconds: float = 0.0
    output_tokens: int = 0
    skills_called: list[str] = field(default_factory=list)
    steps: list[dict] = field(default_factory=list)  # DeepEval spans, in the order they ran.
    searches: list[str] = field(default_factory=list)
    first_searches: list[str] = field(default_factory=list)  # Sent before any tool result.

    @property
    def metrics(self) -> dict[str, float]:
        return {
            "words": len(self.output.split()),
            "length_ratio": len(self.output.split()) / max(len(self.source.split()), 1),
            "seconds": self.seconds,
            "output_tokens": self.output_tokens,
            "searches": len(self.searches),
            "domains": _count_domains(self.output),
            "new_search_terms": _count_new_terms(self.first_searches, self.searches),
            "terms_from_results": _count_terms_from_results(self.steps),
            "later_searches": _count_later_searches(self.steps, self.first_searches),
        }

    def span_tree(self, task: str, searches_only: bool = False) -> dict:
        """The run in the nested span format that JevEval reads as a trajectory."""
        return {
            "name": "agent",
            "type": "agent",
            "input": task,
            "output": "" if searches_only else self.output,
            "children": [
                span for span in self.steps if not searches_only or span["name"] != "message"
            ],
        }


def _count_domains(text: str) -> int:
    urls = re.findall(r"https?://[^\s)\]>\"']+", text)
    return len({urlparse(url).netloc.removeprefix("www.").lower() for url in urls})


def _count_new_terms(first: list[str], all_searches: list[str]) -> int:
    def terms(queries: list[str]) -> set[str]:
        return {word for query in queries for word in re.findall(r"\w{4,}", query.lower())}

    return len(terms(all_searches) - terms(first))


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w{4,}", text.lower()))


def _count_terms_from_results(steps: list[dict]) -> int:
    """Words in later searches that the first search lacked and an earlier result contained."""
    searches = [span for span in steps if _is_search(span)]
    if not searches:
        return 0
    first = _words(searches[0]["input"].get("query", ""))
    seen, learned = set(), set()
    for span in searches:
        learned |= (_words(span["input"].get("query", "")) & seen) - first
        seen |= _words(span.get("output", ""))
    return len(learned)


def _count_later_searches(steps: list[dict], first: list[str]) -> int:
    """Searches sent after the first results came back."""
    return max(sum(1 for span in steps if _is_search(span)) - len(first), 0)


def _result_text(content) -> str:
    if isinstance(content, list):
        content = " ".join(part.get("text", "") for part in content if isinstance(part, dict))
    return str(content)[:MAX_STEP_RESULT_CHARS]


def _parse_trace(stream: str) -> Trace:
    trace = Trace(output="")
    tool_spans: dict[str, dict] = {}
    tool_result_seen = False
    for line in stream.splitlines():
        event = json.loads(line)
        if event.get("type") == "system" and event.get("subtype") == "init":
            trace.session_id = event.get("session_id", "")
        elif event.get("type") == "user":
            tool_result_seen = True
            content = event["message"]["content"]
            for block in content if isinstance(content, list) else []:
                span = tool_spans.get(block.get("tool_use_id"))
                if block.get("type") == "tool_result" and span:
                    span["output"] = _result_text(block.get("content"))
        elif event.get("type") == "assistant":
            for block in event["message"]["content"]:
                if block.get("type") == "text":
                    trace.steps.append({"name": "message", "type": "llm", "output": block["text"]})
                elif block.get("type") == "tool_use":
                    span = {"name": block["name"], "type": "tool", "input": block["input"]}
                    trace.steps.append(span)
                    tool_spans[block["id"]] = span
                    if block["name"] == "Skill":
                        trace.skills_called.append(block["input"].get("skill", ""))
                    elif block["name"] == "WebSearch":
                        query = block["input"].get("query", "")
                        trace.searches.append(query)
                        if not tool_result_seen:
                            trace.first_searches.append(query)
        elif event.get("type") == "result":
            if event.get("is_error"):
                raise RuntimeError(f"Agent run failed: {event.get('result')}")
            trace.output = event.get("result") or ""
            trace.seconds = event.get("duration_ms", 0) / 1000
            trace.output_tokens = event.get("usage", {}).get("output_tokens", 0)
    return trace


def _run_claude(prompt: str, args: list[str], settings: Settings, cwd: str) -> Trace:
    command = [
        "claude",
        "--print",
        "--model", settings.model,
        "--output-format", "stream-json",
        "--verbose",
        "--strict-mcp-config",
        *args,
    ]
    for attempts_left in (1, 0):  # One crash should not discard every sample of an effect.
        response = subprocess.run(
            command, input=prompt, capture_output=True, text=True, timeout=900, cwd=cwd
        )
        if response.returncode == 0:
            return _parse_trace(response.stdout)
    # With stream-json, the reason can be in either stream.
    detail = (response.stderr.strip() or response.stdout.strip())[-1000:]
    raise FailedRun(f"The agent exited with status {response.returncode}: {detail}")


def _usable(trace: Trace) -> Trace:
    if not trace.output.strip():
        raise FailedRun("The agent returned no output.")
    if re.search(r"<invoke\b|<parameter name=", trace.output):
        raise FailedRun(f"The output is a stray tool call: {trace.output[:200]}")
    return trace


def run_followup(effect: Effect, skill: str | None, settings: Settings) -> Trace:
    """Reproduce a follow-up in one conversation, with an identical first reply in both arms.

    With a skill, the second turn is /skill-name, as a user types it. Without one, no skills are
    installed and the second turn is the effect's prompt. The second turn needs the session to
    persist, so each run leaves a session file under ~/.claude/projects.
    """
    # The seeded first turn is visible to the agent, so tell it not to dispute its own reply.
    context = (
        "You wrote your previous reply earlier in this session. Its claims about the work are "
        "accurate, even though you cannot see that work now."
    )
    args = [
        "--setting-sources", "project",
        "--tools", READ_ONLY_TOOLS,
        "--append-system-prompt", context,
    ]
    with tempfile.TemporaryDirectory() as project:
        if skill:
            shutil.copytree(SKILLS_DIR / skill, Path(project) / ".claude" / "skills" / skill)
        first = _run_claude(
            f"Reply with exactly this text and nothing else:\n\n{effect.previous_reply}",
            args,
            settings,
            project,
        )
        opening = effect.previous_reply[:60]
        assert opening in first.output, f"The first reply was not reproduced: {first.output[:120]}"
        trace = _run_claude(
            f"/{skill}" if skill else effect.prompt,
            [*args, "--resume", first.session_id],
            settings,
            project,
        )
    trace.source = effect.previous_reply
    return _usable(trace)


def run_on_text(effect: Effect, skill: str | None, settings: Settings) -> Trace:
    """Invoke the skill with an argument, as a user types it."""
    baseline = effect.prompt or f"Rewrite this for me:\n\n{effect.text}"
    tools = ",".join(effect.tools) or READ_ONLY_TOOLS
    allowed = ["--allowedTools", tools] if effect.tools else []
    with tempfile.TemporaryDirectory() as project:
        if skill:
            shutil.copytree(SKILLS_DIR / skill, Path(project) / ".claude" / "skills" / skill)
        trace = _run_claude(
            f"/{skill} {effect.text}" if skill else baseline,
            ["--no-session-persistence", "--setting-sources", "project", "--tools", tools, *allowed],
            settings,
            project,
        )
    if not effect.prompt:
        trace.source = effect.text
    return _usable(trace)


def run_arm_once(suite: SkillEval, effect: Effect, with_skill: bool, settings: Settings) -> Trace:
    skill = suite.skill if with_skill else None
    if effect.previous_reply is not None:
        return run_followup(effect, skill, settings)
    return run_on_text(effect, skill, settings)


# Damaging a run, for negative tests ---------------------------------------------------


def add_text(text: str) -> Callable[[Trace], Trace]:
    return lambda trace: replace(trace, output=f"{trace.output}\n\n{text}")


def add_opening(text: str) -> Callable[[Trace], Trace]:
    return lambda trace: replace(trace, output=f"{text}\n\n{trace.output}")


def replace_output(text: str) -> Callable[[Trace], Trace]:
    return lambda trace: replace(trace, output=text)


def flatten_text(trace: Trace) -> Trace:
    """Remove every heading mark, list mark, and line break."""
    lines = (re.sub(r"^\s*(#+|[-*]|\d+\.|\|)\s*", "", line) for line in trace.output.splitlines())
    return replace(trace, output=" ".join(line for line in lines if line))


def reverse_sentences(trace: Trace) -> Trace:
    """Put the sentences in reverse order, which breaks the links between them."""
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(trace.output.split()))
    return replace(trace, output=" ".join(reversed(sentences)))


def _is_search(span: dict) -> bool:
    return span.get("name") == "WebSearch"


def lead_first_search(query: str) -> Callable[[Trace], Trace]:
    """Make the first search assume an answer."""

    def apply(trace: Trace) -> Trace:
        steps = [dict(span) for span in trace.steps]
        first = next((span for span in steps if _is_search(span)), None)
        if first:
            first["input"] = {"query": query}
        return replace(trace, steps=steps, first_searches=[query, *trace.first_searches[1:]])

    return apply


def repeat_first_search(trace: Trace) -> Trace:
    """Make every later search rephrase nothing and learn nothing."""
    searches = [span for span in trace.steps if _is_search(span)]
    if not searches:
        return trace
    return replace(
        trace,
        steps=[{**span, **searches[0]} if _is_search(span) else span for span in trace.steps],
    )


def stop_after_first_search(trace: Trace) -> Trace:
    """Keep only the steps up to the first search result."""
    searches = [index for index, span in enumerate(trace.steps) if _is_search(span)]
    return replace(trace, steps=trace.steps[: searches[0] + 1]) if searches else trace


def skip_reading_sources(trace: Trace) -> Trace:
    """Remove every page the agent opened, leaving only search snippets."""
    return replace(trace, steps=[span for span in trace.steps if span.get("name") != "WebFetch"])


# Scoring ------------------------------------------------------------------------------


def _judge_model(settings: Settings) -> TypeSafeModel:
    # Ollama serves the TypeSafe System One API, so the judge runs locally and needs no real key.
    return TypeSafeModel(
        model=settings.judge_model,
        api_key="ollama",
        base_url=settings.ollama_host,
        cost_per_input_token=0.0,
        timeout=180.0,
    )


def _measure(metric: JevEval, test_case: LLMTestCase) -> float:
    try:
        return metric.measure(test_case, _show_indicator=False)
    except Exception as exc:
        raise JudgeError(f"{type(exc).__name__}: {exc}") from exc


def _opening(output: str, sentences: int) -> str:
    """The first sentences of the text itself, skipping headings."""
    body = " ".join(line for line in output.splitlines() if not line.startswith("#"))
    return " ".join(re.split(r"(?<=[.!?])\s+", body.strip())[:sentences])


def _score_output(dimension: str, checks: list[Judged], task: str, trace: Trace, settings: Settings) -> float:
    metric = JevEval(
        name=dimension,
        evaluation_params=(
            [SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT]
            if checks[0].sees_task
            else [SingleTurnParams.ACTUAL_OUTPUT]
        ),
        questions=[Score(question=check.question, levels=LEVELS) for check in checks],
        system_one_model=_judge_model(settings),
        async_mode=False,
    )
    # Labels matter: without them, good and bad rewrites overlapped in calibration.
    first_sentences = checks[0].first_sentences
    if checks[0].first_searches:
        # An agent that never searched started from what it already believed.
        if not trace.first_searches:
            return 0.0
        output = "\n".join(f"- {query}" for query in trace.first_searches)
    elif first_sentences:
        output = _opening(trace.output, first_sentences)
    else:
        output = trace.output
    test_case = LLMTestCase(
        input=f"Task and original document:\n{task}",
        actual_output=f"Output to evaluate:\n{output}",
    )
    return _measure(metric, test_case)


def _score_trajectory(
    dimension: str, checks: list[OnTrajectory], task: str, trace: Trace, settings: Settings
) -> float:
    # With no evaluation_params, JevEval reads the trace instead of the test case fields.
    metric = JevEval(
        name=dimension,
        questions=[Score(question=check.question, levels=LEVELS) for check in checks],
        system_one_model=_judge_model(settings),
        async_mode=False,
    )
    test_case = LLMTestCase(input=task, actual_output=trace.output)
    test_case._trace_dict = trace.span_tree(task, checks[0].searches_only)
    return _measure(metric, test_case)


def _score_reader(
    dimension: str, checks: list[ReaderAnswers], trace: Trace, settings: Settings
) -> float:
    # The reader sees only the output, so the task and the draft cannot supply the answer.
    metric = JevEval(
        name=dimension,
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT],
        questions=[
            Choice(
                question=check.question,
                options={
                    label: float(key == check.correct) for key, label in check.options.items()
                },
            )
            for check in checks
        ],
        system_one_model=_judge_model(settings),
        async_mode=False,
    )
    return _measure(metric, LLMTestCase(input="", actual_output=trace.output))


def _score_match(check: Matches, trace: Trace) -> float:
    found = re.search(check.pattern, trace.output, re.IGNORECASE | re.MULTILINE) is not None
    return float(found == check.expect)


def _score_bound(check: Bound, trace: Trace) -> float:
    value = trace.metrics[check.metric]
    if check.low is not None and value < check.low:
        return value / check.low
    if check.high is not None and value > check.high:
        return check.high / value
    return 1.0


def score(checks: tuple[Check, ...], task: str, trace: Trace, settings: Settings) -> dict[str, float]:
    """Score one output per dimension, with one JevEval for each way a dimension is judged.

    JevEval averages the questions it is given, and the weakest result sets the dimension's score.
    """
    values: dict[str, list[float]] = defaultdict(list)
    judged: dict[tuple, list[Judged]] = defaultdict(list)
    trajectory: dict[tuple, list[OnTrajectory]] = defaultdict(list)
    readers: dict[str, list[ReaderAnswers]] = defaultdict(list)
    for check in checks:
        if isinstance(check, Matches):
            values[check.dimension].append(_score_match(check, trace))
        elif isinstance(check, Bound):
            values[check.dimension].append(_score_bound(check, trace))
        elif isinstance(check, Judged):
            judged[(check.dimension, check.sees_task, check.first_sentences, check.first_searches)].append(check)
        elif isinstance(check, OnTrajectory):
            trajectory[(check.dimension, check.searches_only)].append(check)
        else:
            readers[check.dimension].append(check)

    for (dimension, *_), group in judged.items():
        values[dimension].append(_score_output(dimension, group, task, trace, settings))
    for (dimension, _), group in trajectory.items():
        values[dimension].append(_score_trajectory(dimension, group, task, trace, settings))
    for dimension, group in readers.items():
        values[dimension].append(_score_reader(dimension, group, trace, settings))
    return {dimension: min(scores) for dimension, scores in values.items()}


def compare(skill: list[float], baseline: list[float], settings: Settings) -> str:
    """Call a difference real only if it clears both a minimum size and the sampling noise."""
    if len(skill) < 2 or len(baseline) < 2:
        return "too few samples"
    difference = mean(skill) - mean(baseline)
    noise = 2 * math.sqrt(stdev(skill) ** 2 / len(skill) + stdev(baseline) ** 2 / len(baseline))
    margin = max(settings.min_difference, noise)
    if difference > margin:
        return "better"
    if difference < -margin:
        return "worse"
    return "no clear change"
