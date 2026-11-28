"""Run the TLA+ models of the conversation thread (tests/formal/conversation/) with TLC.

TLA2TOOLS names tla2tools.jar and TLA_JAVA the java to run it (default `java`). Without TLA2TOOLS each test is
skipped as "not proven": the models are then not checked, and the skip says so. The slow configs run only when
BETTER_AI_SLOW_TLA is set.
"""

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

MODELS = Path(__file__).resolve().parent / "formal" / "conversation"
TLA2TOOLS = os.environ.get("TLA2TOOLS")
JAVA = os.environ.get("TLA_JAVA") or "java"
SLOW = bool(os.environ.get("BETTER_AI_SLOW_TLA"))

# config -> (module, invariant its trace must name, or None when the model must pass, slow)
CONFIGS = {
    "as-built-item": ("conversation", "NoLostWrite", False),
    "as-built-agent": ("conversation", "NoDeadThread", False),
    "without-stale-guard-lost": ("conversation", "NoLostWrite", False),
    "without-stale-guard-close": ("conversation", "CloseSticks", False),
    "without-close-any-time": ("conversation", "NoDeadThread", False),
    "fix-item": ("conversation", None, False),
    "fix-agent": ("conversation", None, False),
    "fix-item-larger": ("conversation", None, True),
    "fix-agent-larger": ("conversation", None, True),
    "thread-question": ("thread", None, False),
    "thread-without-stale-guard": ("thread", "NoLostWrite", False),
    "thread-user": ("thread", None, True),
    "thread-report": ("thread", None, True),
}


def run_tlc(config, module):
    with tempfile.TemporaryDirectory() as meta:
        proc = subprocess.run(
            [JAVA, "-cp", TLA2TOOLS, "tlc2.TLC", "-deadlock", "-workers", "auto", "-metadir", meta]
            + ["-config", f"{config}.cfg", f"{module}.tla"],
            cwd=MODELS,
            capture_output=True,
            text=True,
        )
    return proc.stdout + proc.stderr


class FormalConversationTest(unittest.TestCase):
    pass


def make_test(config, module, invariant, slow):
    def test(self):
        if not TLA2TOOLS:
            self.skipTest("not proven: TLA2TOOLS is not set, so TLC did not check this model")
        if not Path(TLA2TOOLS).is_file() or not (Path(JAVA).is_file() or shutil.which(JAVA)):
            self.fail(f"TLA2TOOLS or TLA_JAVA does not name a file: {TLA2TOOLS!r}, {JAVA!r}")
        if slow and not SLOW:
            self.skipTest("not proven: slow model; set BETTER_AI_SLOW_TLA=1 to run it")
        out = run_tlc(config, module)
        violated = re.findall(r"^Error: Invariant (\w+) is violated\.$", out, re.M)
        if invariant is None:
            self.assertIn("Model checking completed. No error has been found.", out, out[-2000:])
        else:
            self.assertEqual(violated[:1], [invariant], out[-2000:])

    test.__name__ = "test_" + config.replace("-", "_")
    return test


for _config, (_module, _invariant, _slow) in CONFIGS.items():
    _test = make_test(_config, _module, _invariant, _slow)
    setattr(FormalConversationTest, _test.__name__, _test)


class ConfigsTest(unittest.TestCase):
    def test_every_config_file_is_listed(self):
        self.assertEqual({p.stem for p in MODELS.glob("*.cfg")}, set(CONFIGS))


if __name__ == "__main__":
    unittest.main()
