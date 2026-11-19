import importlib
import unittest

SERVICES = ["billing", "search", "mail", "auth", "exports"]


class ServicesTest(unittest.TestCase):
    def test_handle_returns_service_and_id(self):
        for name in SERVICES:
            module = importlib.import_module(f"services.{name}")
            self.assertEqual(module.handle({"id": 7}), {"service": name, "id": 7})


if __name__ == "__main__":
    unittest.main()
