"""Run the agent under test in the sample's sandbox: the real Claude Code CLI, or a scripted fake.

`prepare_sandbox` commits the planted files as the starting commit and, in the three installed conditions
(`INSTALLED_CONDITIONS`), installs the skill in the agent user's empty home. `claude_code` runs `claude -p` as that non-root user with the subscription
token from the environment Inspect loaded; `fake_agent` plays the case's good replay instead, so the
whole pipeline can run without a model. Both hand stream-json to `transcript.parse_stream`.

The token is written to a 0600 file by a sandbox call that Inspect does not record, and the
`run-claude` wrapper in the image reads and deletes it before starting Claude Code, so it never
appears in a logged command, environment, input or output.
"""

import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

from inspect_ai.model import ChatMessageUser, ModelOutput
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import SandboxEnvironment, sandbox
from inspect_ai.util._sandbox.events import without_sandbox_events

from skill_evals.cases import INSTALLED_CONDITIONS, REPO, SHORT_SKILL, short_skill
from skill_evals.transcript import Run, parse_stream, redact

WORKDIR = "/work"
AGENT_USER = "agent"
AGENT_TIMEOUT_MESSAGE = "Claude Code timed out"
TOKEN_VARIABLES = ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_AUTH_TOKEN")
# Web tools would let the agent look answers up; scheduling tools keep a non-interactive run open until a
# wake-up fires, long after the work is done.
DISALLOWED_TOOLS = "WebSearch,WebFetch,ScheduleWakeup,CronCreate,CronDelete,CronList,Monitor"
CLAUDE_CODE_VERSION = "2.1.327"
IGNORED_PATHS = ("__pycache__/", ".pytest_cache/")
# Claude Code facts that graders need: where it finds a user's skills, relative to the home folder, and the
# names of its tools that read, run, edit and write. Graders import these, so only this adapter knows the harness.
SKILLS_FOLDER = ".claude/skills"
READ_TOOL, SHELL_TOOL, EDIT_TOOL, WRITE_TOOL = "Read", "Bash", "Edit", "Write"
# The tool an agent calls to load an installed skill by name, without the user's slash command.
SKILL_TOOL = "Skill"
# With a case's earlier work planted in .earlier/, the first commit holds .earlier/before/ and the second, whose
# message is .earlier/message.txt, holds the planted repository: the agent finds its earlier work as the last commit.
# With a history planted in .history/, each step folder, in name order, adds its files/ to the tree and commits them
# with its message.txt, as the author and date its optional commit.env sets. The planted repository then replaces the
# tree as a last commit, only when it differs from the last step.
# `claude -p` stays open while a shell it started in the background still runs, such as a skill's live page server,
# even after it printed its final `result` event. End it once that event is out, so such a run ends when the agent's
# turn ends, not at the timeout. The quotes inside a JSON string are escaped, so only the top-level event matches.
# The run ends only while that event is still the last line 10 seconds later: a background task that finishes may
# start another turn, which prints more events and a new result.
END_AFTER_RESULT = """{run} &
pid=$!
while kill -0 $pid 2>/dev/null; do
    if tail -n 1 {out} 2>/dev/null | grep -q '"type":"result"'; then
        sleep 10
        if tail -n 1 {out} | grep -q '"type":"result"'; then
            kill -TERM $pid 2>/dev/null || true
            sleep 5
            kill -KILL $pid 2>/dev/null || true
            break
        fi
    fi
    sleep 2
done
wait $pid
"""
START_SCRIPT = """
commit() {
    git add -f -A
    git -c user.name=Inspect -c user.email=inspect@example.invalid -c commit.gpgsign=false commit -q --allow-empty "$@"
}
clear_tree() {
    find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
}
saved=""
if [ -d .earlier ]; then
    saved=$(mktemp -d)
    mv .earlier "$saved/earlier"
    cp -a . "$saved/after"
    clear_tree
    cp -a "$saved/earlier/before/." .
fi
git init -q
if [ -d .history ]; then
    saved_history=$(mktemp -d)
    mv .history "$saved_history/history"
    cp -a . "$saved_history/after"
    clear_tree
    for step in "$saved_history"/history/*/; do
        if [ -d "$step/files" ]; then
            cp -a "$step/files/." .
        fi
        (
            if [ -f "$step/commit.env" ]; then
                while IFS='=' read -r key value; do
                    if [ -n "$key" ]; then
                        export "$key=$value"
                    fi
                done < "$step/commit.env"
                if [ -n "${GIT_AUTHOR_DATE:-}" ]; then
                    export GIT_COMMITTER_DATE="$GIT_AUTHOR_DATE"
                fi
            fi
            commit -F "$step/message.txt"
        )
    done
    clear_tree
    cp -a "$saved_history/after/." .
    git add -f -A
    git diff --cached --quiet || commit -m 'Planted repository'
    rm -rf "$saved_history"
else
    commit -m 'Planted repository'
fi
if [ -n "$saved" ]; then
    clear_tree
    cp -a "$saved/after/." .
    commit -F "$saved/earlier/message.txt"
    rm -rf "$saved"
fi
printf '%s\\n' "$@" >> .git/info/exclude
git rev-parse HEAD
"""


def home(user: str) -> str:
    """Return the home directory of a sandbox user."""
    return f"/home/{user}"


def subscription_token() -> str:
    """Return the subscription token from the environment, without ever putting it in an error."""
    for name in TOKEN_VARIABLES:
        if os.environ.get(name):
            return os.environ[name]
    raise RuntimeError(f"No subscription token: set {' or '.join(TOKEN_VARIABLES)} (for example in evals/.env)")


def secrets() -> tuple[str, ...]:
    """Return the token values present in the environment, for redaction."""
    return tuple(os.environ[name] for name in TOKEN_VARIABLES if os.environ.get(name))


async def run_checked(sandbox_env: SandboxEnvironment, command: list[str], **options: Any) -> str:
    """Run a sandbox command and return its stdout, raising with its stderr when it fails."""
    result = await sandbox_env.exec(command, **options)
    if not result.success:
        raise RuntimeError(f"{shlex.join(command)[:120]}: {redact(result.stderr, secrets())}")
    return result.stdout


async def claude_cli(
    sandbox_env: SandboxEnvironment,
    user: str,
    args: list[str],
    *,
    cwd: str,
    stdin: str | None = None,
    timeout: int = 1800,
) -> tuple[str, str, bool]:
    """Run `claude` as a sandbox user with the token; return redacted stdout, stderr and whether it timed out.

    Only the token write is hidden from the eval log: the claude command itself is logged, and its
    output goes to files that are read back without being recorded, then redacted.
    """
    token = subscription_token()
    out = f"/tmp/{user}-claude"
    env = {"HOME": home(user)}
    with without_sandbox_events(sandbox_env):
        await run_checked(
            sandbox_env, ["sh", "-c", 'umask 077 && cat > "$HOME/.eval-token"'], input=token, user=user, env=env
        )
    # Without input, close stdin: `claude -p` otherwise waits for piped data.
    # A command sent to the background reads /dev/null, so a run with input (the judge) stays in the foreground.
    script = f'run-claude "$@" > {out}.out 2> {out}.err'
    if stdin is None:
        script = END_AFTER_RESULT.format(run=script + " < /dev/null", out=f"{out}.out")
    timed_out = False
    try:
        await sandbox_env.exec(
            ["sh", "-c", script, "run-claude", *args],
            input=stdin,
            cwd=cwd,
            user=user,
            env=env,
            timeout=timeout,
            timeout_retry=False,
        )
    except TimeoutError:
        timed_out = True
    with without_sandbox_events(sandbox_env):
        result = await sandbox_env.exec(["sh", "-c", f"cat {out}.out; printf '\\0'; tail -c 4000 {out}.err"])
    stdout, _, stderr = result.stdout.partition("\0")
    return redact(stdout, secrets()), redact(stderr, secrets()), timed_out


def skill_commit(skill: str) -> str:
    """Return the last commit that changed the skill's folder, for the run metadata."""
    command = ["git", "log", "-1", "--format=%H", "--", f"skills/{skill}"]
    return subprocess.run(command, cwd=REPO, text=True, capture_output=True, check=False).stdout.strip()


def skill_dirty(skill: str) -> bool:
    """Return whether the skill's folder has uncommitted changes, so a run is not tied to a commit it did not use."""
    command = ["git", "status", "--porcelain", "--", f"skills/{skill}"]
    return bool(subprocess.run(command, cwd=REPO, text=True, capture_output=True, check=False).stdout.strip())


async def install_skill(sandbox_env: SandboxEnvironment, skill: str, short: bool = False) -> None:
    """Copy the skill as is into the agent user's ~/.claude/skills/<skill>/, or only the short SKILL.md."""
    source = REPO / "skills" / skill
    target = f"{home(AGENT_USER)}/{SKILLS_FOLDER}/{skill}"
    if short:
        await sandbox_env.write_file(f"{target}/SKILL.md", short_skill(skill))
    else:
        for path in sorted(source.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                await sandbox_env.write_file(f"{target}/{path.relative_to(source).as_posix()}", path.read_bytes())
    await run_checked(sandbox_env, ["chown", "-R", f"{AGENT_USER}:{AGENT_USER}", f"{home(AGENT_USER)}/.claude"])
    await run_checked(sandbox_env, ["test", "-f", f"{target}/SKILL.md"])


@solver
def prepare_sandbox(skill: str) -> Solver:
    """Commit the planted files as the agent user and, in the conditions that install it, the full or short skill."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        sandbox_env = sandbox()
        await run_checked(sandbox_env, ["chown", "-R", f"{AGENT_USER}:{AGENT_USER}", WORKDIR])
        stdout = await run_checked(
            sandbox_env, ["bash", "-ec", START_SCRIPT, "bash", *IGNORED_PATHS], cwd=WORKDIR, user=AGENT_USER
        )
        state.store.set("start_commit", stdout.split()[-1])
        if state.metadata["condition"] in INSTALLED_CONDITIONS:
            await install_skill(sandbox_env, skill, short=state.metadata["condition"] == SHORT_SKILL)
        return state

    return solve


def record_run(state: TaskState, run: Run, prompt: str) -> None:
    """Put the converted run into the sample: messages, output and Claude Code's statistics."""
    state.messages = [ChatMessageUser(content=prompt), *run.messages]
    state.output = ModelOutput.from_content(run.model or "claude-code", run.reply)
    state.metadata["claude_code"] = {"model": run.model, **run.stats}


@solver
def claude_code(model: str = "sonnet", timeout: int = 1800) -> Solver:
    """Run the real Claude Code CLI on the sample's prompt in /work, with the web and scheduling tools disallowed."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        prompt = state.input_text
        args = ["-p", prompt, "--output-format", "stream-json", "--verbose", "--model", model]
        args += ["--permission-mode", "bypassPermissions", f"--disallowedTools={DISALLOWED_TOOLS}"]
        stdout, stderr, timed_out = await claude_cli(sandbox(), AGENT_USER, args, cwd=WORKDIR, timeout=timeout)
        run = parse_stream(stdout, secrets())
        record_run(state, run, prompt)
        if timed_out:
            # Raised like any Claude Code failure, so the sample is an Inspect sample error: left out of pass rates
            # and of cost and time averages, never scored on partial work as $0 and 0 s.
            state.metadata["claude_code"]["timed_out"] = True
            raise RuntimeError(f"{AGENT_TIMEOUT_MESSAGE} after {timeout} seconds")
        if run.error:
            raise RuntimeError(f"Claude Code failed: {run.error[:500]}\n{stderr[-1000:]}")
        return state

    return solve


async def play_action(
    sandbox_env: SandboxEnvironment, number: int, action: dict[str, Any]
) -> tuple[dict[str, Any], str, bool]:
    """Carry out one scripted action as the agent user; return its tool_use block, output and error flag."""
    if "write" in action:
        path, content = f"{WORKDIR}/{action['write']}", action["content"]
        script = 'mkdir -p "$(dirname "$1")" && cat > "$1"'
        await run_checked(sandbox_env, ["sh", "-c", script, "sh", path], input=content, user=AGENT_USER)
        return (
            tool_use_block(number, WRITE_TOOL, {"file_path": path, "content": content}),
            f"File created at: {path}",
            False,
        )
    if "read" in action:
        path = f"{WORKDIR}/{action['read']}"
        result = await sandbox_env.exec(["cat", path], user=AGENT_USER)
        lines = result.stdout.splitlines()
        text = (
            "".join(f"{line_number:6}\t{line}\n" for line_number, line in enumerate(lines, 1))
            if result.success
            else result.stderr
        )
        return tool_use_block(number, READ_TOOL, {"file_path": path}), text, not result.success
    command = action["bash"]
    result = await sandbox_env.exec(["bash", "-c", command], cwd=WORKDIR, user=AGENT_USER, timeout=120)
    output = (result.stdout + result.stderr).strip()
    if not result.success:
        output = f"Exit code {result.returncode}\n{output}"
    return tool_use_block(number, SHELL_TOOL, {"command": command}), output, not result.success


def tool_use_block(number: int, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Build a tool_use block as Claude Code prints it."""
    return {"type": "tool_use", "id": f"toolu_fake_{number}", "name": name, "input": arguments}


@solver
def fake_agent() -> Solver:
    """Play the case's good replay as stream-json events, so the pipeline runs with no model call."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        sandbox_env = sandbox()
        scripted = state.metadata.get("scripted_run") or {}
        events: list[dict[str, Any]] = [{"type": "system", "subtype": "init", "model": "fake", "skills": []}]
        for number, action in enumerate(scripted.get("actions") or []):
            block, output, error = await play_action(sandbox_env, number, action)
            content = [block]
            events.append({"type": "assistant", "message": {"id": f"msg_{number}", "content": content}})
            result = {"type": "tool_result", "tool_use_id": block["id"], "content": output, "is_error": error}
            events.append({"type": "user", "message": {"role": "user", "content": [result]}})
        reply = scripted.get("reply") or ""
        events.append(
            {"type": "assistant", "message": {"id": "msg_reply", "content": [{"type": "text", "text": reply}]}}
        )
        events.append({"type": "result", "subtype": "success", "is_error": False, "result": reply, "num_turns": 1})
        stream = "\n".join(json.dumps(event) for event in events)
        record_run(state, parse_stream(stream), state.input_text)
        return state

    return solve


def agent_metadata(agent: str, model: str, skill: str) -> dict[str, Any]:
    """Describe the agent for the task metadata."""
    version = "scripted" if agent == "fake" else CLAUDE_CODE_VERSION
    return {
        "agent": agent,
        "agent_model": model,
        "agent_version": version,
        "skill_commit": skill_commit(skill),
        "skill_dirty": skill_dirty(skill),
    }


def dockerfile_version() -> str:
    """Return the Claude Code version the sandbox image pins, to check it matches CLAUDE_CODE_VERSION."""
    text = (Path(__file__).with_name("sandbox") / "Dockerfile").read_text()
    return next(line.split("=", 1)[1] for line in text.splitlines() if line.startswith("ARG CLAUDE_CODE_VERSION="))
