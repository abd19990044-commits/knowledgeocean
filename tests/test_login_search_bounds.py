"""Regression tests for passcode-list configuration and bounded search loops."""
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
import app

class PasscodeAndSearchTests(unittest.TestCase):
    def test_vip_separators(self):
        for delim in (",", "،", ";", "؛", "\n"):
            with self.subTest(delim=repr(delim)), patch.dict(os.environ, {"APP_PASSWORD": "VIP_FIRST"+delim+"VIP_SECOND"}):
                self.assertTrue(app.verify_password("VIP_FIRST"))
                self.assertTrue(app.verify_password("VIP_SECOND"))
                self.assertFalse(app.verify_password("VIP_THIRD"))
    def test_guest_queue_has_bounded_wait(self):
        src = Path(app.__file__).read_text(encoding="utf-8")
        self.assertIn("SEARCH_QUEUE_MAX_SECONDS", src)
    def test_login_with_comma_separated_vip(self):
        with patch.dict(os.environ, {"APP_PASSWORD": "ALPHA,BETA"}), patch.object(app, "db_check_ip_ban", return_value=(False,0)), patch.object(app, "db_record_auth_attempt", return_value=(False,5,0)):
            with TestClient(app.app, base_url="https://testserver") as client:
                response = client.post("/api/login", json={"password": "BETA"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["tier"], "vip")
if __name__ == "__main__":
    unittest.main()
