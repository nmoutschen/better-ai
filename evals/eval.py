"""Inspect task for skill evals: one sample per case and condition, run by Claude Code and graded per rule.

    uv run inspect eval eval.py -T skill=code-better   # no-skill, skill and short-skill
    uv run inspect eval eval.py -T skill=code-better -T agent=fake   # plumbing, no model calls

Conditions: `no-skill` sends the request as is, `skill` installs the skill and prefixes `/<skill>`,
`one-sentence` appends the sentence for the case's first source from `one_sentence.yaml`,
`short-skill` installs a skill of the same name holding all those sentences and invokes it like `skill`,
`skill-installed` installs the skill and sends the request as is.
The default runs no-skill, skill and short-skill, plus skill-installed for a behavioural skill; one-sentence is a diagnostic for rules where the skill trails. The agent is the real Claude Code CLI (`agent=claude_code`, model from
`-T model=`) or a scripted fake (`agent=fake`) that plays each case's good replay. The judge model is
`-T judge_model=` (default: a different model from the agent; `none` skips judges). Inspect's own
`--model` is unused: the CLI calls the API itself, so the task sets the `none` model.
"""

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset

from skill_evals.agent import agent_metadata, claude_code, fake_agent, prepare_sandbox
from skill_evals.cases import check_skill, default_conditions, parse_conditions, samples
from skill_evals.grading.judge import NO_JUDGE
from skill_evals.grading.lint import lint_issues_added
from skill_evals.grading.loaded import skill_loaded
from skill_evals.grading.reads import skill_reads
from skill_evals.grading.scorer import grade_cases, grader_keys
from skill_evals.sandbox import COMPOSE

AGENTS = ("claude_code", "fake")


def default_judge(agent: str, model: str) -> str:
    """Judge with a different model from the agent's; no judge for the fake agent."""
    if agent == "fake":
        return NO_JUDGE
    return "sonnet" if "opus" in model else "opus"


@task
def skill_eval(
    skill: str,
    condition: str | list[str] | None = None,
    rule: str | None = None,
    cases: str | list[str] | None = None,
    agent: str = "claude_code",
    model: str = "sonnet",
    judge_model: str | None = None,
    timeout: int = 1800,
) -> Task:
    """Build the eval for one skill: `condition` is a condition or a list, by default the skill kind's; `rule` and `cases` filter."""
    if agent not in AGENTS:
        raise ValueError(f"Agents are {', '.join(AGENTS)}")
    conditions = parse_conditions(condition or default_conditions(check_skill(skill)))
    # Inspect parses unquoted CLI values as YAML, so a rule such as 1.5 arrives as a float.
    rule = None if rule is None else str(rule)
    case_ids = (
        [case_id.strip() for case_id in (cases.split(",") if isinstance(cases, str) else cases)] if cases else None
    )
    dataset = samples(check_skill(skill), conditions, rule, case_ids, scripted=agent == "fake")
    if not dataset:
        raise ValueError(f"No cases for {skill!r} with rule {rule!r}, cases {cases!r}, conditions {conditions}")
    judge_model = judge_model or default_judge(agent, model)
    keys = sorted({key for sample in dataset for key in grader_keys(sample.metadata["graders"])})
    solver = fake_agent() if agent == "fake" else claude_code(model, timeout)
    return Task(
        dataset=MemoryDataset(dataset, name=skill),
        setup=prepare_sandbox(skill),
        solver=solver,
        # The rule's score first; skill_reads and lint_issues_added are independent, so they are separate
        # scorers (Inspect's advice). lint_issues_added only observes: it is never part of a pass or fail.
        scorer=[grade_cases(keys, judge_model), skill_reads(), skill_loaded(), lint_issues_added()],
        sandbox=("docker", COMPOSE),
        model="none/none",
        metadata={"skill": skill, "conditions": conditions, "rule": rule, "judge_model": judge_model}
        | agent_metadata(agent, model, skill),
    )
