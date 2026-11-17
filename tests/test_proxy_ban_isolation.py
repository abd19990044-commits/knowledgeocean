"""Regression tests for visitor-isolated bans behind a shared hosting proxy."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

import app


PROXY = ("10.20.30.40", 5555)
ENV = {
    "APP_PASSWORD": "VIPCODE",
    "OTHER_PASSWORD": "OTHERCODE",
    "SPACE_ID": "test/space",
    "TRUSTED_PROXY_IPS": "",
}


def make_proxy_client():
    async def asgi(scope, receive, send):
        if scope.get("type") == "http":
            scope = dict(scope)
            scope["client"] = PROXY
        await app.app(scope, receive, send)

    return TestClient(asgi, base_url="https://testserver")


class ProxyBanIsolationTests(unittest.TestCase):
    def setUp(self):
        with app._LOGIN_FAILS_LOCK:
            app._LOGIN_FAILS.clear()

    def test_five_wrong_codes_ban_only_that_visitor(self):
        with patch.dict(os.environ, ENV):
            visitor_a = {"X-Guest-Token": "visitor-A-" + os.urandom(8).hex()}
            visitor_b = {"X-Guest-Token": "visitor-B-" + os.urandom(8).hex()}
            visitor_c = {"X-Guest-Token": "visitor-C-" + os.urandom(8).hex()}
            with make_proxy_client() as client:
                for number in range(5):
                    response = client.post(
                        "/api/login",
                        json={"password": f"wrong-{number}"},
                        headers=visitor_a,
                    )
                self.assertEqual(response.status_code, 403)
                self.assertTrue(response.json()["banned"])

                # The blocked visitor remains blocked, while another visitor on the same
                # platform proxy can authenticate successfully.
                blocked = client.post("/api/login", json={"password": "VIPCODE"}, headers=visitor_a)
                self.assertEqual(blocked.status_code, 403)
                allowed = client.post("/api/login", json={"password": "VIPCODE"}, headers=visitor_b)
                self.assertEqual(allowed.status_code, 200)

                quota = client.get("/api/guest-quota", headers=visitor_c)
                self.assertEqual(quota.status_code, 200)
                self.assertTrue(quota.json()["ok"])
                self.assertFalse(quota.json().get("banned", False))

    def test_forwarded_for_cannot_change_a_shared_proxy_identity(self):
        with patch.dict(os.environ, ENV):
            token = "xff-test-" + os.urandom(8).hex()
            headers = {"X-Guest-Token": token, "User-Agent": "KO Regression Browser"}
            with make_proxy_client() as client:
                for number in range(5):
                    response = client.post(
                        "/api/login",
                        json={"password": f"wrong-{number}"},
                        headers={**headers, "X-Forwarded-For": f"8.8.8.{number}"},
                    )
                self.assertEqual(response.status_code, 403)
                self.assertTrue(response.json()["banned"])

    def test_public_client_ip_is_not_rewritten(self):
        request = SimpleNamespace(
            client=SimpleNamespace(host="8.8.4.4"),
            headers={},
        )
        with patch("app.is_local_instance", return_value=False):
            ip, _ = app.get_fingerprint(request)
        self.assertEqual(ip, "8.8.4.4")

    def test_global_throttle_blocks_token_rotation_but_not_valid_codes(self):
        with patch.dict(os.environ, ENV):
            with make_proxy_client() as client:
                last = None
                for number in range(app.LOGIN_GLOBAL_FAIL_LIMIT):
                    last = client.post(
                        "/api/login",
                        json={"password": f"invalid-{number}"},
                        headers={"X-Guest-Token": f"rotating-{number}-{os.urandom(4).hex()}"},
                    )
                self.assertEqual(last.status_code, 401)

                throttled = client.post(
                    "/api/login",
                    json={"password": "another-invalid"},
                    headers={"X-Guest-Token": "rotated-after-limit-" + os.urandom(4).hex()},
                )
                self.assertEqual(throttled.status_code, 429)
                self.assertIn("Retry-After", throttled.headers)

                # A valid credential is checked before the global failed-attempt throttle.
                valid = client.post(
                    "/api/login",
                    json={"password": "VIPCODE"},
                    headers={"X-Guest-Token": "legitimate-" + os.urandom(4).hex()},
                )
                self.assertEqual(valid.status_code, 200)

    def test_every_password_failure_path_uses_the_global_guard(self):
        source = (os.path.dirname(app.__file__) + "/app.py")
        with open(source, "r", encoding="utf-8") as handle:
            content = handle.read()
        self.assertEqual(content.count("db_record_auth_attempt(ip, success=False)"), 4)
        self.assertEqual(content.count("wait = register_login_failure()"), 4)


if __name__ == "__main__":
    unittest.main()
