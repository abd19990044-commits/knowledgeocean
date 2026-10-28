"""Regression checks for core search/security behavior (no network required)."""
import pathlib
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]

class HardeningRegressionTests(unittest.TestCase):
    def test_scopus_vip_only(self):
        text = (ROOT / "app.py").read_text("utf-8")
        self.assertIn('if db_source == "elsevier" and not is_vip:', text)
        self.assertIn("if is_guest and 'elsevier' in active:", text)

    def test_author_search_not_filtered_by_title(self):
        source = (ROOT / "app.py").read_text("utf-8")
        self.assertIn('if mode != "author" and not matches_target_query', source)

    def test_access_controls(self):
        source = (ROOT / "app.py").read_text("utf-8")
        self.assertIn("require_owner(request, user_hash", source)
        self.assertIn('require_owner(request, task.get("user_hash"', source)
        self.assertIn("candidate_hashes = [authorized_hash]", source)

    def test_signed_session(self):
        import access_control
        from starlette.responses import Response
        from starlette.requests import Request
        with patch.object(access_control, "_SECRET", b"a-static-key-only-for-the-test-suite"):
            response = Response()
            access_control.issue_session(response, "0123456789abcdef", secure=True)
            self.assertIn("httponly", response.headers["set-cookie"].lower())
            token = response.headers["set-cookie"].split(";", 1)[0]
            request = Request({"type": "http", "method": "GET", "headers": [(b"cookie", token.encode())]})
            self.assertEqual(access_control.session_owner(request), "0123456789abcdef")
            forged = token[:-1] + ("a" if token[-1] != "a" else "b")
            bad = Request({"type": "http", "method": "GET", "headers": [(b"cookie", forged.encode())]})
            self.assertIsNone(access_control.session_owner(bad))

    def test_no_insecure_fallback_passwords(self):
        text = (ROOT / "app.py").read_text("utf-8")
        self.assertIn('APP_PASSWORDS = set()', text)
        self.assertIn('OTHER_PASSWORDS = set()', text)
        self.assertNotIn('passwords = {"123"}', text)

if __name__ == "__main__":
    unittest.main()
