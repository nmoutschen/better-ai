"""reply.md tells Sam about the cache and that drafts are stored on the server and survive clearing it."""
import re

text = open("reply.md").read()
assert re.search(r"cache", text, re.I), "cache not mentioned"
assert re.search(r"draft", text, re.I), "drafts not mentioned"
assert re.search(r"server|cloud|your account|online", text, re.I), "where drafts are stored not mentioned"
kept = (r"(\bnot?\b|n't|never)[^.]{0,60}\b(delet|remov|los|eras|wip|touch|affect)"
        r"|\b(safe|kept|keeps|stay|stays|remain|remains|untouched|unaffected)\b")
assert re.search(kept, text, re.I), "does not say drafts are kept"
