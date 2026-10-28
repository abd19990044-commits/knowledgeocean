"""HTTP-level regression tests; all requests are local and do not contact scholarly APIs."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import app
from access_control import issue_session
from starlette.responses import Response


class ProductionHTTPTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app.app, base_url="https://testserver")

    def tearDown(self):
        self.client.close()

    def test_scopus_guest_and_secondary_are_forbidden(self):
        with patch.object(app, "db_check_ip_ban", return_value=(False, 0)), patch.object(app, "is_local_instance", return_value=False), patch.object(app, "get_guest_remaining_quota", return_value=50):
            unauth = self.client.post("/api/search", data={"query": "naproxen", "db_source": "elsevier"})
            self.assertEqual(unauth.status_code, 403)
        with patch.dict(os.environ, {"OTHER_PASSWORD": "SECONDARY_ONLY"}), patch.object(app, "OTHER_PASSWORDS", {"SECONDARY_ONLY"}), patch.object(app, "db_check_ip_ban", return_value=(False, 0)), patch.object(app, "is_local_instance", return_value=False), patch.object(app, "get_guest_remaining_quota", return_value=50), patch.object(app, "check_guest_search_quota", return_value=(False, 49)):
            other = self.client.post("/api/search", data={"query": "naproxen", "db_source": "elsevier", "password": "SECONDARY_ONLY"})
            self.assertEqual(other.status_code, 403)

    def test_vip_scopus_allowed_without_leaking_api_key(self):
        with patch.dict(os.environ, {"APP_PASSWORD": "TEST_VIP_123456", "ELSEVIER_API_KEY": "NOT_FOR_BROWSER"}), patch.object(app, "APP_PASSWORDS", {"TEST_VIP_123456"}), patch.object(app, "db_check_ip_ban", return_value=(False, 0)), patch.object(app, "is_local_instance", return_value=False), patch.object(app, "_set_task", return_value=None), patch.object(app.threading, "Thread") as fake_thread:
            result = self.client.post("/api/search", data={"query": "naproxen", "db_source": "elsevier", "password": "TEST_VIP_123456", "limit": "1"})
            self.assertEqual(result.status_code, 200, result.text)
            self.assertTrue(result.json().get("task_id"))
            self.assertNotIn("NOT_FOR_BROWSER", result.text)
            self.assertIn("httponly", result.headers.get("set-cookie", "").lower())
            self.assertTrue(fake_thread.called)

    def test_file_owner_is_required(self):
        with tempfile.TemporaryDirectory() as root, patch.object(app, "DOWNLOAD_DIR", root), patch.object(app, "is_local_instance", return_value=False):
            folder = Path(root, "ownerabcdef123456")
            folder.mkdir()
            (folder / "test.pdf").write_bytes(b"%PDF-1.4\nTEST")
            denied = self.client.get("/download/ownerabcdef123456/test.pdf")
            self.assertEqual(denied.status_code, 403)
            cookie_response = Response()
            issue_session(cookie_response, "ownerabcdef123456", secure=True)
            cookie_pair = cookie_response.headers["set-cookie"].split(";", 1)[0]
            key, value = cookie_pair.split("=", 1)
            self.client.cookies.set(key, value, domain="testserver", path="/")
            allowed = self.client.get("/download/ownerabcdef123456/test.pdf")
            self.assertEqual(allowed.status_code, 200)
            self.assertEqual(allowed.content, b"%PDF-1.4\nTEST")
            wrong = self.client.get("/download/otheruser12345678/test.pdf")
            self.assertEqual(wrong.status_code, 403)

    def test_cancel_route_is_not_get(self):
        self.assertEqual(self.client.get("/api/cancel/a-test-task").status_code, 405)

if __name__ == "__main__":
    unittest.main()
