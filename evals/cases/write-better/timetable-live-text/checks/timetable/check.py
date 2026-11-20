"""timetable/ holds one text file (Markdown, text, HTML or SVG) whose readable text has every time, place and name.

HTML and SVG count by the text they show: scripts, styles, comments and tag attributes (such as an image's alt text) are
removed first, so a timetable drawn on a canvas, put in an image, or drawn as SVG paths fails.
"""
import html
import pathlib
import re

FACTS = {
    "08:30": r"\b0?8[:.]30",
    "09:00": r"\b0?9[:.]00|\b9\s*a\.?m",
    "09:30": r"\b0?9[:.]30",
    "12:00": r"\b12[:.]00|\bnoon|\b12\s*p\.?m",
    "13:00": r"\b13[:.]00|\b1[:.]00\s*p|\b1\s*p\.?m",
    "15:00": r"\b15[:.]00|\b3[:.]00\s*p|\b3\s*p\.?m",
    "15:30": r"\b15[:.]30|\b3[:.]30",
    "Old Boathouse": r"Old\s+Boat\s*house",
    "Mill Bridge": r"Mill\s+Bridge",
    "Willow Bank": r"Willow\s+Bank",
    "Weir car park": r"\bWeir\b",
    "St Brigid's Hall": r"Brigid",
    "Nkechi": r"Nkechi",
    "Rafael": r"Rafael",
    "Hana": r"\bHana\b",
    "Dev": r"\bDev\b",
    "Lucía": r"Luc[ií]a",
    "Grace": r"\bGrace\b",
    "Tomasz": r"Tomasz",
}


def readable_text(path):
    text = path.read_text(errors="replace")
    if path.suffix.lower() in (".html", ".htm", ".svg"):
        text = re.sub(r"<(script|style)\b.*?</\1\s*>", " ", text, flags=re.I | re.S)
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
        text = re.sub(r"<[^>]*>", " ", text)
        text = html.unescape(text)
    return text


folder = pathlib.Path("timetable")
assert folder.is_dir(), "no timetable/ folder"
files = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in (".md", ".markdown", ".txt", ".html", ".htm", ".svg")]
assert files, "no text file in timetable/"
missing_by_file = {}
for path in files:
    text = readable_text(path)
    missing = [name for name, pattern in FACTS.items() if not re.search(pattern, text, re.I)]
    if not missing:
        break
    missing_by_file[str(path)] = missing
else:
    raise AssertionError(f"no file holds every time, place and name as text: {missing_by_file}")
