"""Skill evals: run Claude Code on planted cases in a Docker sandbox and grade what it did.

`cases` turns case folders into Inspect samples, `agent` runs the real Claude Code CLI (or a scripted
fake for plumbing runs), `transcript` turns its stream-json output into Inspect messages, and
`grading` scores the result with deterministic file checks and an LLM judge.
"""
