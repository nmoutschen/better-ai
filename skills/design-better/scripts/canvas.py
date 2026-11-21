#!/usr/bin/env python3
"""Show one or more versions of a screen on one page, at the same screen sizes, and collect the user's feedback.

Usage:
  python3 canvas.py show VERSION... --out FILE [--title T] [--question Q] [--width WxH ...] [--open]
                        [--serve [--port N]]
  python3 canvas.py wait DIR [--timeout S]
  python3 canvas.py reply DIR TEXT [--to ID]
  python3 canvas.py status DIR seen|asked|working|done|accepted ID...
  python3 canvas.py pending DIR

VERSION is LABEL=SOURCE or SOURCE. SOURCE is an HTML file, embedded into the page, or an http(s) address, loaded
when the page is viewed. Without a LABEL, versions are labelled A, B, C in order.

The page fills one window: the versions sit side by side at one screen size at a time, each scaled to fit and
scrolling inside its own frame, with a conversation with the agent on the right. With two or more versions, the page
also offers to switch between them in the same place, which shows small changes at one spot better than looking from
one to the other; with four or more, it opens that way, since side by side they are too small to read. The page styles only its own controls: each version keeps the styles it brings.

On the page, the user clicks any part of a version to comment on it, gives each version a thumbs up or down when
there are three or more, writes to the agent, and decides with Decide. `show --serve` serves the page on 127.0.0.1
and keeps running. Each action is a JSON-RPC call from the page (comment, delete, note, verdict, decide, accept,
reopen); the script appends it to conversation.jsonl next to the page and prints it to stdout as one JSON line, so a
harness that streams a command's output delivers it to the agent as it arrives. Running `show` again with the same
--out, without --serve and --open, updates the served page: the open page loads the new versions once the user is not typing.

`wait` blocks until the served page receives actions the agent has not seen, prints them and exits, for harnesses
that only notify when a command ends. Once a `wait` has connected, the page tells the user whenever none has been
connected for a few seconds, since what they send then reaches the agent only when it next looks. `reply` shows the agent's reply in the page's conversation, `status` marks each
item seen, asked, working, done or accepted, and `pending` lists what is not finished. Without a server, Copy all
copies the feedback as text for the user to paste in the chat. Comments work on versions embedded from files only.

canvas.html, page.css, canvas.css, page.js and canvas.js, next to this script, are the page; the script fills in the
versions. page.py, also next to it, holds the conversation with the agent.
"""

import argparse
import html
import http.server
import json
import mimetypes
import re
import sys
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # page.py, the conversation every page that talks to the agent shares, sits here too
import page  # noqa: E402

TEMPLATE = (HERE / "canvas.html").read_text(encoding="utf-8")
# page.css is the look shared with research-better's board; canvas.css adds what only the canvas shows.
CSS = (HERE / "page.css").read_text(encoding="utf-8") + (HERE / "canvas.css").read_text(encoding="utf-8")
# page.js is the conversation shared with the other pages that talk to the agent; canvas.js is this page alone.
JS = (HERE / "page.js").read_text(encoding="utf-8") + (HERE / "canvas.js").read_text(encoding="utf-8")

DEFAULT_WIDTHS = ("1280x800", "375x700")
SIZE = re.compile(r"^(\d{3,4})(?:x(\d{3,4}))?$")
URL = re.compile(r"^https?://", re.I)
# A relative href or src: not absolute, not a fragment, not a data: or mailto: link.
RELATIVE_REF = re.compile(r"""(?:href|src)\s*=\s*["'](?![a-z][a-z0-9+.-]*:|//|#)[^"']+["']""", re.I)
HEAD = re.compile(r"<head[^>]*>", re.I)
# The file:// base given to a version with relative links, as it appears inside the escaped srcdoc of the page.
FILE_BASE = re.compile(r'(base href=&quot;)(file://[^&"]+?)/(&quot;)')

LOG, SEEN, ADDRESS = "conversation.jsonl", ".conversation-seen", ".server"
METHODS = ("comment", "delete", "note", "verdict", "decide", "accept", "reopen")  # what the page may send
ITEMS = ("comment", "note", "decide")  # what the agent tracks with status


def icon(path: str) -> str:
    return f'<svg viewBox="0 0 24 24" aria-hidden="true">{path}</svg>'


# Icons for the controls that depend on the screen sizes and versions; the others sit in canvas.html.
ICONS = {
    "Desktop": icon('<rect x="2" y="4" width="20" height="13" rx="1"/><path d="M8 21h8M12 17v4"/>'),
    "Tablet": icon('<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M11 18h2"/>'),
    "Mobile": icon('<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>'),
    "side": icon('<rect x="3" y="4" width="8" height="16"/><rect x="13" y="4" width="8" height="16"/>'),
    "switch": icon('<rect x="5" y="4" width="14" height="16"/><path d="M9 12h6M13 9l3 3-3 3"/>'),
    "up": icon('<path d="M7 10v11H3V10zM7 10l4-8a3 3 0 0 1 3 3v4h6a2 2 0 0 1 2 2.3l-1.4 8A2 2 0 0 1 18.6 21H7"/>'),
    "down": icon('<path d="M17 14V3h4v11zM17 14l-4 8a3 3 0 0 1-3-3v-4H4a2 2 0 0 1-2-2.3l1.4-8A2 2 0 0 1 5.4 3H17"/>'),
}


# ---------- The page ----------


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def parse_version(arg: str, index: int) -> tuple:
    """LABEL=SOURCE or SOURCE. The part before '=' is a label only if it does not look like a path or an address."""
    label, sep, rest = arg.partition("=")
    if sep and rest and "/" not in label and ":" not in label and not label.lower().endswith((".html", ".htm")):
        return label.strip(), rest.strip()
    return chr(ord("A") + index), arg.strip()


def parse_size(text: str) -> tuple:
    m = SIZE.match(text.strip().lower())
    if not m:
        sys.exit(f"error: --width {text!r} is not WIDTH or WIDTHxHEIGHT in pixels, such as 375 or 375x700")
    w = int(m.group(1))
    return w, int(m.group(2)) if m.group(2) else (800 if w >= 768 else 700)


def frame_source(source: str, warnings: list) -> str:
    """The iframe attribute that loads one version: src for an address, srcdoc for a file."""
    if URL.match(source):
        warnings.append(f"{source} is loaded when the page is viewed: it shows only while that address answers.")
        return f'src="{esc(source)}"'
    path = Path(source).expanduser()
    if not path.is_file():
        sys.exit(f"error: {source} is not a file or an http(s) address")
    doc = path.read_text(encoding="utf-8", errors="replace")
    if RELATIVE_REF.search(doc):
        warnings.append(f"{source} links files by relative path: the page shows them only on this machine.")
        base = f'<base href="{esc(path.resolve().parent.as_uri())}/">'
        m = HEAD.search(doc)
        doc = doc[: m.end()] + base + doc[m.end() :] if m else base + doc
    return f'srcdoc="{esc(doc)}"'


def screen_name(w: int, h: int) -> str:
    return "Desktop" if w >= 1024 else "Tablet" if w >= 600 else "Mobile"


def icon_button(attrs: str, icon_html: str, text: str) -> str:
    return f'<button type="button" class="ico" {attrs}>{icon_html}<span>{esc(text)}</span></button>'


def figure(i: int, label: str, attr: str, w: int, h: int, verdicts: bool, full: bool) -> str:
    """One version at one screen size, with its label and buttons. Full size shows it alone, so it needs another."""
    buttons = (
        "".join(
            f'<button type="button" class="vbtn" data-v="{i}" data-verdict="{v}" aria-pressed="false" '
            f'aria-label="{name}: {esc(label)}">{ICONS[v]}</button>'
            for v, name in (("up", "Good"), ("down", "Not good"))
        )
        if verdicts
        else ""
    )
    return (
        f'<figure data-i="{i}"><div class="label"><b title="{esc(label)}">{esc(label)}</b><span class="acts">{buttons}'
        # Keyboard users comment on a whole version with this button; it shows only when focused.
        f'<button type="button" class="vcomment" data-v="{i}">Comment on {esc(label)}</button>'
        + ('<button type="button" class="full">Full size</button>' if full else "")
        + "</span></div>"
        f'<div class="stage"><div class="screen"><iframe data-i="{i}" title="{esc(label)}, {w} × {h} px" '
        f'width="{w}" height="{h}" {attr}></iframe></div></div></figure>'
    )


def render(versions: list, sizes: list, title: str, question: str) -> tuple:
    """Fill canvas.html with what depends on the versions and screen sizes."""
    warnings = []
    loaded = [(label, frame_source(source, warnings)) for label, source in versions]
    labels = [label for label, _ in loaded]
    # With two versions, a verdict says nothing Decide does not; verdicts help only to sort three or more.
    verdicts = len(loaded) > 2
    rows = "".join(
        f'<section data-size="{k}" aria-label="Screen {w} × {h} px"{" hidden" if k else ""}>'
        f'<div class="row" style="--n:{len(loaded)}">'
        + "".join(figure(i, label, attr, w, h, verdicts, len(loaded) > 1) for i, (label, attr) in enumerate(loaded))
        + "</div></section>"
        for k, (w, h) in enumerate(sizes)
    )
    names = [screen_name(w, h) for w, h in sizes]
    if len(set(names)) < len(names):
        names = [f"{w} × {h}" for w, h in sizes]
    screens = views = tabs = ""
    if len(sizes) > 1:
        screens = (
            '<div class="seg cycle" role="group" aria-label="Screen">'
            + "".join(
                icon_button(
                    f'data-size="{k}" aria-pressed="{str(k == 0).lower()}" title="{esc(n)}, {w} × {h} px" '
                    f'aria-label="{esc(n)}, {w} × {h} px"',
                    ICONS.get(n, ""),
                    n,
                )
                for k, ((w, h), n) in enumerate(zip(sizes, names, strict=True))
            )
            + "</div>"
        )
    if len(labels) > 1:
        views = (
            '<div class="seg cycle" role="group" aria-label="View">'
            + icon_button(
                'data-view="side" aria-pressed="true" title="Side by side" aria-label="Side by side"',
                ICONS["side"],
                "Side by side",
            )
            + icon_button(
                'data-view="switch" aria-pressed="false" title="Switch in place (Space)" aria-label="Switch in place"',
                ICONS["switch"],
                "Switch",
            )
            + "</div>"
        )
        # In switch view, the version shown is picked from tabs inside the viewer, so the toolbar keeps its layout.
        tabs = (
            '<div class="seg pick" role="group" aria-label="Version shown" hidden>'
            + "".join(
                f'<button type="button" data-pick="{i}" aria-pressed="false">{esc(label)}</button>'
                for i, label in enumerate(labels)
            )
            + "</div>"
        )
    fill = {
        "{{CSS}}": CSS,
        "{{JS}}": JS,
        "{{TITLE}}": esc(title),
        "{{QUESTION}}": f'<p class="question">{esc(question)}</p>' if question else "",
        "{{QUESTION_TEXT}}": esc(question),
        "{{LABELS}}": esc(json.dumps(labels)),
        "{{SCREENS}}": screens,
        "{{VIEWS}}": views,
        "{{TABS}}": tabs,
        "{{ROWS}}": rows,
    }
    # One pass, so a placeholder inside a title or a version is not filled in.
    markup = re.sub(r"\{\{[A-Z_]+\}\}", lambda m: fill.get(m.group(0), m.group(0)), TEMPLATE)
    return markup, warnings


# ---------- The conversation: conversation.jsonl, one JSON event per line, next to the page ----------


def conversation(folder: Path) -> page.Conversation:
    return page.Conversation(
        folder,
        LOG,
        SEEN,
        ADDRESS,
        ITEMS,
        "agent",
        "show VERSION... --out FILE --serve",
        schemas=HERE.parent / "schemas",
        events="canvas-events.schema.json",
    )


# ---------- show --serve ----------


def serve(path: Path, port: int, open_browser: bool) -> None:
    """Serve the page from disk, so a rewrite shows on reload, and record each action the page sends."""
    conv = conversation(path.parent)
    # A version with relative links carries a file:// base, which a page served over http may not load. The served
    # page points that base at /files/<n>/ instead, and the server reads only inside that folder.
    folders: list = []

    def served_page() -> bytes:
        def swap(m):
            uri = urllib.parse.unquote(html.unescape(m.group(2)))
            root = Path(urllib.request.url2pathname(urllib.parse.urlparse(uri).path)).resolve()
            if root not in folders:
                folders.append(root)
            return f"{m.group(1)}/files/{folders.index(root)}/{m.group(3)}"

        return FILE_BASE.sub(swap, path.read_text(encoding="utf-8")).encode("utf-8")

    class Handler(page.Handler):
        conversation = conv
        methods = METHODS

        def version_file(self) -> None:
            """A file a version links by relative path, read only from inside that version's own folder."""
            parts = urllib.parse.unquote(self.path.split("?", 1)[0]).split("/", 3)  # "", "files", index, path
            if len(parts) < 4 or not parts[2].isdigit() or int(parts[2]) >= len(folders):
                return self.send_error(404)
            root = folders[int(parts[2])]
            target = (root / parts[3]).resolve()
            if not target.is_relative_to(root) or not target.is_file():
                return self.send_error(404)
            self.send(200, target.read_bytes(), mimetypes.guess_type(target.name)[0] or "application/octet-stream")

        def do_GET(self):
            if not self.local():
                return self.send_error(403)
            if self.conversation_get():
                return None
            if self.path in ("/", "/index.html"):
                return self.send(200, served_page(), "text/html; charset=utf-8")
            if self.path.startswith("/files/"):
                return self.version_file()
            if self.path == "/rev":
                return self.send(200, str(path.stat().st_mtime_ns).encode(), "text/plain")
            self.send_error(404)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    conv.address.write_text(url, encoding="utf-8")
    conv.seen.write_text(str(len(conv.lines())), encoding="utf-8")
    print(f"Serving {path} at {url}. Each action the user takes is printed here as one JSON line.", flush=True)
    if open_browser and not webbrowser.open(url):
        print(
            "Could not open a browser on this machine. If the user's browser runs on another machine, "
            "this address does not reach it.",
            flush=True,
        )
    page.stop_like_ctrl_c()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        conv.address.unlink(missing_ok=True)


# ---------- Command line ----------


def show(args) -> None:
    if len(args.versions) > 26:
        sys.exit("error: at most 26 versions")
    versions = [parse_version(arg, i) for i, arg in enumerate(args.versions)]
    labels = [label for label, _ in versions]
    if len(set(labels)) != len(labels):
        sys.exit("error: two versions have the same label")
    sizes = [parse_size(s) for s in (args.width or DEFAULT_WIDTHS)]
    markup, warnings = render(versions, sizes, args.title, args.question)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markup, encoding="utf-8")
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(f"wrote {out}")
    if args.serve:
        serve(out.resolve(), args.port, args.open)
    elif args.open and (out.parent / ADDRESS).exists():
        print(
            "The page is already served: the open page loads the new versions once the user is not typing, so no tab was opened."
        )
    elif args.open and not webbrowser.open(out.resolve().as_uri()):
        print("Could not open a browser on this machine. Give the user the path instead.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Show versions of a screen on a page and collect the user's feedback.")
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("show", help="write the page, and serve it with --serve")
    s.add_argument(
        "versions", nargs="+", metavar="VERSION", help="LABEL=SOURCE or SOURCE: an HTML file or an http(s) address"
    )
    s.add_argument("--out", required=True, help="the HTML page to write")
    s.add_argument("--title", default="Versions", help="the page heading")
    s.add_argument("--question", default="", help="what the user should decide, shown under the heading")
    s.add_argument(
        "--width",
        action="append",
        metavar="WxH",
        help=f"a screen size to show every version at; repeat for more (default: {' and '.join(DEFAULT_WIDTHS)})",
    )
    s.add_argument("--open", action="store_true", help="open the page in the default browser")
    s.add_argument("--serve", action="store_true", help="serve the page on 127.0.0.1 and record the user's actions")
    s.add_argument("--port", type=int, default=0, help="port to serve on (default: any free port)")
    w = sub.add_parser("wait", help="wait for the user's next actions on the served page, print them and exit")
    w.add_argument("dir")
    w.add_argument("--timeout", type=float, default=3600, help="seconds to wait (default: 3600)")
    r = sub.add_parser("reply", help="show a reply from the agent in the served page")
    r.add_argument("dir")
    r.add_argument("text")
    r.add_argument("--to", metavar="ID", help="the id of the comment or message the reply answers")
    t = sub.add_parser(
        "status",
        help="mark items as seen, asked (waiting for the user), working or done; "
        "accepted only when the user accepted in words",
    )
    t.add_argument("dir")
    t.add_argument("state", choices=page.STATES)
    t.add_argument("ids", nargs="+", metavar="ID")
    t.add_argument("--text", help="the user's words, for accepted")
    p = sub.add_parser("pending", help="list the items that are not done or accepted")
    p.add_argument("dir")
    args = parser.parse_args()

    folder = Path(getattr(args, "dir", ".")).expanduser().resolve()
    if args.command == "show":
        show(args)
    elif args.command == "wait":
        sys.exit(conversation(folder).wait(args.timeout))
    elif args.command == "reply":
        conversation(folder).reply(args.text, args.to)
    elif args.command == "status":
        conversation(folder).set_status(args.state, args.ids, args.text)
    else:
        conversation(folder).pending()


if __name__ == "__main__":
    main()
