"""lab-results.md changed and keeps every result, limit, condition, instruction and contact detail."""
import re

text = open("lab-results.md").read()
planted = open(__file__.replace("check.py", "planted.md")).read()
assert text.strip() != planted.strip(), "unchanged"
patterns = (
    r"5\s*(th\s*)?(of\s*)?Nov(ember)?|Nov(ember)?\s*5", r"6[.,]2", r"4[.,]1", r"\b3(?:[.,]0)?\b", r"1[.,]4", r"1[.,]6",
    r"\b6\s*(%|per\s*cent|(in|out of)\s*(every\s*)?100)",
    r"\b10\s*(%|per\s*cent|(in|out of)\s*(every\s*)?100)|\b1\s*(in|out of)\s*(every\s*)?10\b",
    r"(12|twelve)[ -]weeks?", r"statin", r"(10|ten)[ -]hours?", r"water", r"active|activity|exercise",
    r"01632\s*960\s*418", r"\b0?8[:.]00|8\s*am", r"18[:.]00|6\s*pm", r"nurse", r"Sato", r"Adeyemi",
)
missing = [p for p in patterns if not re.search(p, text, re.I)]
assert not missing, missing
