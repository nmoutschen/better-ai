"""research-better's checks across records, named by `x-check` in its schemas."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..schema import Context, hook


@hook("merge-loop")
def _merge_loop(record: dict, context: Context) -> list[tuple[str, str]]:
    """A question merged into another that is merged into it, directly or through others, is in a loop: each member
    is an error on `merged_into`. A question's file is named for its id, so only the chain is read, one file a step,
    and each question's result is worked out once per load. A question merged into itself is left to
    `x-differs-from`."""
    start = record.get("id")
    at = record.get("merged_into")
    if not isinstance(start, str) or not _linkable(at):
        return []
    key = f"merge-loops:{context.directory}"
    results: dict[str, str | None] = context.cache.setdefault(key, {})
    if start not in results:
        _walk_merges(start, context, results)
    own = context.read_json(f"{start}.json")
    if isinstance(own, dict) and own.get("merged_into") == at and own.get("status") == "merged":
        message = results[start]
    else:  # a file named differently from its id: the record's own link starts the chain
        message = _stray_loop(start, at, context)
    return [("merged_into", message)] if message else []


def _linkable(at: Any) -> bool:
    return isinstance(at, str) and "/" not in at and "\\" not in at


def _next_merge(at: str, context: Context) -> Any:
    step = context.read_json(f"{at}.json")
    return step.get("merged_into") if isinstance(step, dict) and step.get("status") == "merged" else None


def _walk_merges(start: str, context: Context, results: dict[str, str | None]) -> None:
    """Follow the chain from `start` to its end, a question already worked out, or a repeat; then store the loop
    message of each member of a loop found, and None for every other question on the way."""
    path, where = [start], {start: 0}
    at = _next_merge(start, context)
    while _linkable(at) and at not in results and at not in where:
        where[at] = len(path)
        path.append(at)
        at = _next_merge(at, context)
    loop = path[where[at] :] if isinstance(at, str) and at in where else []
    for one in path:
        results[one] = None
    if len(loop) > 1:
        for i, one in enumerate(loop):
            turned = [*loop[i:], *loop[:i]]
            results[one] = f"merge loop: {' → '.join([*turned, one])}"


def _merge_reach(context: Context) -> tuple[dict[str, str | None], Callable[[str, str], bool]]:
    """The merge links of every question file in the folder, and `reaches(x, y)`: whether following the links from x
    arrives at y. Worked out once per load: the links form a forest hanging off ends and loops, and a walk of it
    numbers each node on the way down, so x reaches y when y is an ancestor of x (or, for a loop, in x's component)."""
    key = f"merge-reach:{context.directory}"
    if key not in context.cache:
        links: dict[str, str | None] = {}
        for path in sorted(context.directory.glob("*.json")):
            link = _next_merge(path.stem, context)
            links[path.stem] = link if _linkable(link) else None
        nodes = set(links) | {t for t in links.values() if t is not None}
        below: dict[str, list[str]] = {}
        for node, link in links.items():
            if link is not None:
                below.setdefault(link, []).append(node)
        tin: dict[str, int] = {}
        tout: dict[str, int] = {}
        group: dict[str, str] = {}
        on_loop: set[str] = set()
        clock = 0

        def descend(root: str, name: str) -> None:
            nonlocal clock
            stack = [(root, False)]
            while stack:
                node, done = stack.pop()
                if done:
                    tout[node] = clock
                    continue
                tin[node] = clock = clock + 1
                group[node] = name
                stack.append((node, True))
                stack.extend((n, False) for n in below.get(node, []) if n not in on_loop)

        for node in sorted(nodes):  # ends first: a node that links nowhere
            if links.get(node) is None:
                descend(node, node)
        for node in sorted(nodes):  # what is left is on a loop or hangs off one
            if node in group:
                continue
            walk, seen_at = [], {}
            at: str | None = node
            while at is not None and at not in group and at not in seen_at:
                seen_at[at] = len(walk)
                walk.append(at)
                at = links.get(at)
            if at is not None and at in seen_at:
                loop = walk[seen_at[at] :]
                on_loop.update(loop)
                for member in loop:
                    group[member] = loop[0]
                for member in loop:
                    descend(member, loop[0])
                for member in loop:
                    tin.pop(member, None)
            # a tail of nodes that hang off the loop (or off a node already placed) is placed by its descend
        context.cache[key] = (links, tin, tout, group, on_loop)
    links, tin, tout, group, on_loop = context.cache[key]

    def reaches(x: str, y: str) -> bool:
        if x == y or x not in group or y not in group:
            return False
        if y in on_loop:
            return group[x] == group[y]
        return y in tin and x in tin and tin[y] < tin[x] <= tout[y]

    return links, reaches


def _stray_loop(start: str, at: Any, context: Context) -> str | None:
    """The loop of a record whose own link is not the one its file holds: it loops if the chain from `at` comes back
    to it. The chain is only built, one file a step, when there is a loop to report."""
    if at == start:
        return None
    links, reaches = _merge_reach(context)
    if not reaches(at, start):
        return None
    chain, seen = [start], {start}
    while isinstance(at, str) and at not in seen:
        chain.append(at)
        seen.add(at)
        at = links.get(at)
    return f"merge loop: {' → '.join([*chain, start])}" if at == start else None
