"""Regression checks for core search/security behavior (no network required)."""
import pathlib
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]

class HardeningRegressionTests(unittest.TestCase):
    def test_platform_scopus_key_is_never_exposed_to_public_clients(self):
        import app
        from fastapi.testclient import TestClient
        with patch.dict("os.environ", {"ELSEVIER_API_KEY": "PRIVATE_PLATFORM_KEY"}):
            with TestClient(app.app) as client:
                response = client.get("/api/settings")
        self.assertNotIn("PRIVATE_PLATFORM_KEY", response.text)
        self.assertEqual(response.json()["elsevier_api_key"], "***")

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

    def test_unicode_content_disposition_is_safe_for_http_headers(self):
        import urllib.parse
        import app
        from starlette.responses import Response, FileResponse
        import tempfile

        filename = "Academic_Report_الذكاء_الاصطناعي_2026.pdf"
        value = app.build_content_disposition("attachment", filename)

        # Starlette/ASGI response headers must be encodable as latin-1.
        self.assertTrue(value.isascii())
        value.encode("latin-1")
        self.assertIn('filename="', value)
        self.assertIn("filename*=UTF-8''" + urllib.parse.quote(filename, safe=""), value)

        # An explicit safe header must override FileResponse's automatic filename header.
        with tempfile.NamedTemporaryFile(suffix=".pdf") as temp:
            temp.write(b"%PDF-1.4")
            temp.flush()
            response = FileResponse(
                temp.name,
                filename=filename,
                headers={"Content-Disposition": value},
            )
            self.assertEqual(response.headers["content-disposition"], value)

    def test_bibtex_download_uses_unicode_safe_content_disposition(self):
        source = (ROOT / "app.py").read_text("utf-8")
        self.assertIn('build_content_disposition("attachment", safe_name)', source)

    def test_no_insecure_fallback_passwords(self):
        text = (ROOT / "app.py").read_text("utf-8")
        self.assertIn('APP_PASSWORDS = set()', text)
        self.assertIn('OTHER_PASSWORDS = set()', text)
        self.assertNotIn('passwords = {"123"}', text)

if __name__ == "__main__":
    unittest.main()
