import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sweep  # noqa: E402

ITEMS = [(kind, n) for kind in "abcdefgh" for n in range(500)]


class Sweep(unittest.TestCase):
    def sampled(self, **kw):
        with mock.patch.dict(os.environ, {"BETTER_AI_SWEEP": ""}):
            return sweep.cases(ITEMS, **kw)

    def test_a_full_sweep_returns_every_item_in_order(self):
        with mock.patch.dict(os.environ, {"BETTER_AI_SWEEP": "full"}):
            self.assertEqual(sweep.cases(ITEMS, key=lambda i: i[0]), ITEMS)

    def test_the_sample_is_the_same_on_every_run(self):
        self.assertEqual(self.sampled(key=lambda i: i[0]), self.sampled(key=lambda i: i[0]))

    def test_the_sample_is_about_a_tenth_and_covers_every_class(self):
        chosen = self.sampled(key=lambda i: i[0])
        self.assertEqual({k for k, _ in chosen}, set("abcdefgh"))
        self.assertTrue(0.05 * len(ITEMS) < len(chosen) < 0.2 * len(ITEMS), len(chosen))

    def test_a_class_of_one_item_is_kept_and_no_key_means_one_class(self):
        items = [("rare", 0), *ITEMS]
        self.assertIn(("rare", 0), self.sampled_of(items))
        self.assertTrue(self.sampled_of(ITEMS[:3], None))

    def test_several_keys_each_keep_every_class(self):
        items = [(a, b) for a in "abc" for b in "xyz" for _ in range(300)]
        chosen = self.sampled_of(items, key=[lambda i: i[0], lambda i: i[1]])
        self.assertEqual({a for a, _ in chosen}, set("abc"))
        self.assertEqual({b for _, b in chosen}, set("xyz"))

    def sampled_of(self, items, key=lambda i: i[0]):
        with mock.patch.dict(os.environ, {"BETTER_AI_SWEEP": ""}):
            return sweep.cases(items, key=key)

    def test_a_generator_is_accepted(self):
        self.assertEqual(self.sampled_of((i for i in range(3)), key=None)[0], 0)


if __name__ == "__main__":
    unittest.main()
