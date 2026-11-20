"""Count the lint issues an agent added to the Python files it changed, in every case, to show code quality.

This scorer observes and does not grade: its value is a count, never part of a case's pass or fail. It runs
`new_lint_issues.py` on a copy of the submitted tree with a fixed rule set that ignores the repository's own
configuration, so every case and condition is counted the same way: pyflakes (F), bugbear (B) and the
statement and syntax errors of pycodestyle (E4, E7, E9). Runs that change no Python file get no score.
"""

import re
from pathlib import Path

from inspect_ai.scorer import Score, Scorer, Target, mean, scorer
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox

from skill_evals.agent import WORKDIR
from skill_evals.grading.files import Checkout, GradingError
from skill_evals.transcript import redact

SCRIPT = Path(__file__).with_name("new_lint_issues.py")
RULES = "E4,E7,E9,F,B"
COUNT = re.compile(r"(\d+) new issue\(s\)")
NO_CHANGE = "no Python file changed"


@scorer(metrics=[mean()])
def lint_issues_added() -> Scorer:
    """Count the lint issues the agent added; no score when it changed no Python file."""

    async def score(state: TaskState, target: Target) -> Score | None:
        repo = Checkout(sandbox(), state.store.get("start_commit"), WORKDIR)
        command = f'python "$GRADE_FILES/{SCRIPT.name}" --isolated --select {RULES}'
        try:
            result = await repo.snapshot_run(command, hidden={SCRIPT.name: SCRIPT.read_text()})
        except GradingError as error:
            # An observation never fails a sample that was graded already.
            return Score.unscored(reason="scoring_failed", explanation=redact(error.detail[-500:]))
        lines = (result.stdout.strip().splitlines() if result else []) or [""]
        if lines[-1] == NO_CHANGE:
            return None
        match = COUNT.fullmatch(lines[-1])
        if match is None:
            detail = redact((result.stderr if result else "; ".join(repo.notes))[-500:])
            return Score.unscored(reason="scoring_failed", explanation=detail)
        return Score(value=int(match[1]), explanation=redact("\n".join(lines[-20:])))

    return score
