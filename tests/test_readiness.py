"""Behavioral regressions for request isolation, quotas and server responsiveness."""
import asyncio
from contextlib import ExitStack
import json
import logging
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

import httpx
from fastapi.testclient import TestClient
from starlette.requests import Request

import access_control
import app
import database
import network
import providers
from models import CanonicalPaper
from config_loader import bounded_env_int, load_local_config

VIP = "TEST_ONLY_VIP_CODE"
PERSONAL_KEY = "a" * 32


class RequestSafetyTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        root = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.stack.enter_context(patch.object(database, "DB_PATH", str(Path(root, "test.db"))))
        self.stack.enter_context(patch.object(app, "DOWNLOAD_DIR", root))
        self.stack.enter_context(patch.object(app, "is_local_instance", return_value=False))
        self.stack.enter_context(patch.object(app, "db_check_ip_ban", return_value=(False, 0)))
        self.stack.enter_context(patch.object(app, "db_record_auth_attempt", return_value=(False, 5, 0)))
        self.stack.enter_context(patch.dict(os.environ, {"APP_PASSWORD": VIP, "ELSEVIER_API_KEY": "SERVER_KEY"}))
        self.stack.enter_context(patch.object(app, "APP_PASSWORDS", {VIP}))
        self.tasks = {}
        self.stack.enter_context(patch.object(app, "TASKS", self.tasks))
        self.stack.enter_context(patch.object(network, "TASKS", self.tasks))
        self.thread = self.stack.enter_context(patch.object(app.threading, "Thread"))
        self.quota = self.stack.enter_context(patch.object(app, "check_guest_search_quota", return_value=(False, 45)))
        self.stack.enter_context(patch.object(app, "get_guest_remaining_quota", return_value=50))
        database.init_db()
        self.client = TestClient(app.app, base_url="https://testserver")
        self.addCleanup(self.client.close)

    def test_invalid_requests_never_consume_quota_or_start_threads(self):
        invalid = [
            {"query": " "}, {"query": "ab"}, {"query": "x" * 2001},
            {"limit": "0"}, {"limit": "-5"}, {"limit": "1000000"},
            {"db_source": "invalid"}, {"db_source": "elsevier"},
            {"mode": "invalid"}, {"search_scope": "invalid"},
            {"doc_type_filter": "invalid"}, {"year_from": "bad"},
            {"year_from": "2026", "year_to": "2020"},
            {"elsevier_api_key": "invalid\nheader"},
        ]
        for fields in invalid:
            with self.subTest(fields=fields):
                r = self.client.post("/api/search", data={"query": "naproxen", **fields})
                self.assertIn(r.status_code, (400, 403, 422))
        self.quota.assert_not_called()
        self.thread.assert_not_called()

    def test_personal_key_is_only_in_worker_memory(self):
        r = self.client.post("/api/search", data={"query": "naproxen", "password": VIP, "db_source": "elsevier", "elsevier_api_key": PERSONAL_KEY})
        self.assertEqual(r.status_code, 200, r.text)
        task_id = r.json()["task_id"]
        self.assertEqual(self.thread.call_args.kwargs["kwargs"]["elsevier_api_key"], PERSONAL_KEY)
        self.assertNotIn(PERSONAL_KEY, r.text)
        self.assertNotIn(PERSONAL_KEY, json.dumps(self.tasks))
        self.assertNotIn(PERSONAL_KEY, json.dumps(database.db_get_task(task_id)))
        self.assertEqual(os.environ["ELSEVIER_API_KEY"], "SERVER_KEY")

    def test_guest_key_allows_scopus_without_tier_upgrade(self):
        r = self.client.post("/api/search", data={"query": "naproxen", "db_source": "elsevier", "elsevier_api_key": PERSONAL_KEY})
        self.assertEqual(r.status_code, 200, r.text)
        self.quota.assert_called_once()
        worker = self.thread.call_args.kwargs["kwargs"]
        self.assertTrue(worker["is_guest"])
        self.assertEqual(worker["elsevier_api_key"], PERSONAL_KEY)
        self.assertNotIn(PERSONAL_KEY, json.dumps(self.tasks))

    def test_guest_custom_key_is_forwarded_for_comprehensive_search(self):
        r = self.client.post("/api/search", data={"query": "naproxen", "elsevier_api_key": PERSONAL_KEY})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.thread.call_args.kwargs["kwargs"]["elsevier_api_key"], PERSONAL_KEY)

    def test_comprehensive_time_mode_survives_guest_result_quota(self):
        r = self.client.post("/api/search", data={"query": "climate", "limit": "999999"})
        self.assertEqual(r.status_code, 200)
        worker = self.thread.call_args.kwargs["kwargs"]
        self.assertEqual(worker["limit"], 50)
        self.assertTrue(worker["comprehensive_search"])
        self.assertTrue(worker["is_guest"])

    def test_access_code_personal_key_uses_normal_quota_and_queue(self):
        with patch.object(app, "OTHER_PASSWORDS", {"TEST_ACCESS_CODE"}):
            r = self.client.post("/api/search", data={"query": "climate", "password": "TEST_ACCESS_CODE", "db_source": "elsevier", "elsevier_api_key": PERSONAL_KEY})
        self.assertEqual(r.status_code, 200, r.text)
        worker = self.thread.call_args.kwargs["kwargs"]
        self.assertTrue(worker["is_guest"])
        self.assertTrue(worker["is_other"])
        self.assertEqual(worker["elsevier_api_key"], PERSONAL_KEY)
        self.assertTrue(self.quota.call_args.kwargs["is_other"])

    def test_repeated_search_resumes_existing_task_without_charging_again(self):
        first = self.client.post("/api/search", data={"query": "naproxen"})
        second = self.client.post("/api/search", data={"query": "naproxen"})
        self.assertEqual(second.json()["task_id"], first.json()["task_id"])
        self.assertTrue(second.json()["resumed"])
        self.quota.assert_called_once()
        self.thread.assert_called_once()

    def test_logged_in_cookie_can_authorize_personal_key_search_after_reload(self):
        login = self.client.post("/api/login", json={"password": VIP})
        self.assertEqual(login.status_code, 200)
        r = self.client.post("/api/search", data={"query": "naproxen", "db_source": "elsevier", "elsevier_api_key": PERSONAL_KEY})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(self.thread.call_args.kwargs["kwargs"]["is_guest"])
        self.assertEqual(self.thread.call_args.kwargs["kwargs"]["elsevier_api_key"], PERSONAL_KEY)

    def test_cross_origin_login_is_denied(self):
        r = self.client.post("/api/login", json={"password": VIP}, headers={"Origin": "https://unrelated.example"})
        self.assertEqual(r.status_code, 403)

    def test_logout_clears_cookie_and_removes_vip_access(self):
        login = self.client.post("/api/login", json={"password": VIP})
        self.assertEqual(login.status_code, 200)
        self.assertTrue(self.client.get("/api/guest-quota").json()["is_vip"])
        response = self.client.post("/api/logout")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Max-Age=0", response.headers["set-cookie"])
        self.assertFalse(self.client.get("/api/guest-quota").json()["is_vip"])
        denied = self.client.post("/api/search", data={"query": "naproxen", "db_source": "elsevier"})
        self.assertEqual(denied.status_code, 403)


class UserGuideDownloadTests(unittest.TestCase):
    def test_both_guides_are_public_pdf_attachments(self):
        with TestClient(app.app) as client:
            for language in ("ar", "en"):
                with self.subTest(language=language):
                    response = client.get("/api/user-guide/" + language)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.headers["content-type"], "application/pdf")
                    self.assertEqual(response.headers["content-language"], language)
                    self.assertIn("attachment", response.headers["content-disposition"])
                    self.assertIn("_" + language.upper() + ".pdf", response.headers["content-disposition"])
                    self.assertTrue(response.content.startswith(b"%PDF-"))
                    self.assertGreater(len(response.content), 10000)
                    head = client.head("/api/user-guide/" + language)
                    self.assertEqual(head.status_code, 200)
                    self.assertEqual(head.content, b"")

    def test_unsupported_language_is_not_used_as_a_file_path(self):
        client = TestClient(app.app)
        self.addCleanup(client.close)
        for language in ("fr", "config.txt", "..%2F..%2Fconfig.txt"):
            self.assertEqual(client.get("/api/user-guide/" + language).status_code, 404)


class NetworkIsolationTests(unittest.TestCase):
    def test_provider_uses_request_key_without_changing_environment(self):
        response = Mock(status_code=200)
        response.json.return_value = {"search-results": {"entry": []}}
        with patch.dict(os.environ, {"ELSEVIER_API_KEY": "SERVER_KEY"}), patch.object(providers, "safe_get", return_value=response) as get:
            for key in ("a" * 32, "b" * 32):
                providers.fetch_elsevier_batch("naproxen", {}, "keyword", "", "", False, 5, api_key=key)
                self.assertEqual(get.call_args.kwargs["headers"]["X-ELS-APIKey"], key)
                self.assertNotIn(key, get.call_args.kwargs["circuit_key"])
            self.assertEqual(os.environ["ELSEVIER_API_KEY"], "SERVER_KEY")

    def test_personal_key_failure_does_not_trip_platform_or_other_key_circuit(self):
        failed = Mock(status_code=401, headers={})
        success = Mock(status_code=200, headers={})
        with patch.dict(network.CIRCUIT_STATES, {}, clear=True), patch.object(network.HTTP, "get", side_effect=[failed, success]) as get, patch.object(network.time, "sleep"):
            network.safe_get("elsevier", "https://api.elsevier.com/content/search/scopus", circuit_key="elsevier:test-user-a", timeout=1)
            network.safe_get("elsevier", "https://api.elsevier.com/content/search/scopus", circuit_key="elsevier:test-user-b", timeout=1)
            self.assertTrue(network.is_engine_in_cooldown("elsevier:test-user-a"))
            self.assertFalse(network.is_engine_in_cooldown("elsevier:test-user-b"))
            self.assertFalse(network.is_engine_in_cooldown("elsevier"))
            self.assertEqual(get.call_count, 2)
            self.assertNotIn("circuit_key", get.call_args.kwargs)

    def test_expired_search_does_not_wait_for_premium_priority(self):
        with patch.dict(network.TASKS, {"expired-test": {"_search_deadline": time.monotonic() - 1}}), patch.object(network.HTTP, "get") as get:
            self.assertIsNone(network.safe_get("crossref", "https://api.crossref.org/works", "expired-test", True))
            get.assert_not_called()

    def test_expired_search_stops_waiting_for_provider_lock(self):
        lock = threading.Lock()
        lock.acquire()
        timer = threading.Timer(0.05, lambda: network.TASKS.update({"lock-test": {"_search_deadline": time.monotonic() - 1}}))
        with patch.dict(network.ENGINE_LOCKS, {"test-provider": lock}), patch.dict(network.TASKS, {}, clear=True), patch.object(network.HTTP, "get") as get:
            timer.start()
            try:
                self.assertIsNone(network.safe_get("test-provider", "https://example.org", "lock-test"))
                get.assert_not_called()
            finally:
                timer.join()
                lock.release()


class ConfigurationTests(unittest.TestCase):
    def test_invalid_environment_budget_uses_default_and_clamps(self):
        for value, expected in (("bad", 90), ("", 90), ("1", 30), ("9999", 150)):
            with patch.dict(os.environ, {"SEARCH_MAX_SECONDS": value}):
                self.assertEqual(bounded_env_int("SEARCH_MAX_SECONDS", 90, 30, 150), expected)

    def test_config_does_not_enable_local_mode_or_log_secret_values(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {}, clear=True):
            config = Path(root, "config.txt")
            config.write_text("KO_SESSION_SECRET=never-log-this-value\nUNPAYWALL_EMAIL=test@example.org\n")
            with self.assertLogs("AcademicAPI", logging.INFO) as logs:
                load_local_config(str(config))
            self.assertNotIn("LOCAL_INSTANCE", os.environ)
            self.assertNotIn("never-log-this-value", "\n".join(logs.output))

    def test_non_ascii_session_cookies_are_rejected_without_server_errors(self):
        for token in (b"\xff.signature", b"payload.\xff"):
            request = Request({"type": "http", "headers": [(b"cookie", b"ko_owner_session=" + token)]})
            self.assertIsNone(access_control.session_owner(request))


class PipelineTests(unittest.TestCase):
    def test_scope_filter_is_applied_before_target_count(self):
        book = CanonicalPaper(title="Naproxen textbook", doi="10.1000/book", raw_type="book", authors=["Jane Author"], year="2024", sources=["crossref"])
        article = CanonicalPaper(title="Naproxen analytical study", doi="10.1000/article", raw_type="journal-article", authors=["Jane Author"], year="2025", journal="Analytical Journal", sources=["crossref"])

        def fetch(query, state, *args):
            state["exhausted"] = True
            return [book, article]

        with tempfile.TemporaryDirectory() as root, patch.object(app, "DOWNLOAD_DIR", root), patch.object(app, "FETCH_BATCH_MAP", {"crossref": fetch}), patch.object(app, "db_set_task"), patch.object(app, "generate_documents", side_effect=lambda q, p, path, *a, **kw: Path(path).write_bytes(b"%PDF-test")), patch.object(app, "refund_guest_search_quota"):
            try:
                app.process_pipeline("naproxen", db_source="crossref", limit=1, uh="test-owner", task_id="test-filter", is_guest=True, search_scope="papers")
                task = app.TASKS["test-filter"]
                self.assertEqual(task["status"], "completed", task.get("error"))
                self.assertEqual([p["doi"] for p in task["papers"]], ["10.1000/article"])
            finally:
                app.TASKS.pop("test-filter", None)

    def test_failed_export_refunds_entire_reservation_once(self):
        article = CanonicalPaper(title="Naproxen analytical study", doi="10.1000/article", raw_type="journal-article", authors=["Jane Author"], year="2025", sources=["crossref"])

        def fetch(query, state, *args):
            state["exhausted"] = True
            return [article]

        with tempfile.TemporaryDirectory() as root, patch.object(app, "DOWNLOAD_DIR", root), patch.object(app, "FETCH_BATCH_MAP", {"crossref": fetch}), patch.object(app, "db_set_task"), patch.object(app, "generate_documents", side_effect=OSError("Test export failure")), patch.object(app, "refund_guest_search_quota") as refund:
            try:
                app.process_pipeline("naproxen", db_source="crossref", limit=5, uh="test-owner", task_id="test-export", is_guest=True, guest_ip="test-ip", guest_fp="test-fp")
                self.assertEqual(app.TASKS["test-export"]["status"], "error")
                self.assertEqual(sum(call.args[2] for call in refund.call_args_list), 5)
            finally:
                app.TASKS.pop("test-export", None)

    def test_full_queue_refunds_unstarted_search(self):
        with patch.object(app, "GUEST_QUEUE", list(range(100))), patch.object(app, "_set_task"), patch.object(app, "refund_guest_search_quota") as refund:
            app.managed_pipeline_wrapper("naproxen", "keyword", "all", 5, "", "test-owner", "test-queue", False, None, None, False, True, include_abstracts=True, guest_ip="test-ip", guest_fp="test-fp")
            refund.assert_called_once_with("test-ip", "test-fp", 10, is_other=False, guest_token="")


class ResponsivenessTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_stays_responsive_during_doi_network_request(self):
        started, release = threading.Event(), threading.Event()
        response = Mock(status_code=404)

        def slow_get(*args, **kwargs):
            started.set()
            release.wait(3)
            return response

        with patch.object(app.requests, "get", side_effect=slow_get), patch.object(app, "db_check_ip_ban", return_value=(False, 0)), patch.object(app, "db_check_rate_limit", return_value=(False, 99)):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app.app), base_url="https://testserver") as client:
                lookup = asyncio.create_task(client.get("/api/doi-lookup", params={"doi": "10.1000/test"}))
                try:
                    self.assertTrue(await asyncio.to_thread(started.wait, 1))
                    begin = time.monotonic()
                    health = await asyncio.wait_for(client.get("/health"), 0.5)
                    self.assertEqual(health.status_code, 200)
                    self.assertLess(time.monotonic() - begin, 0.5)
                finally:
                    release.set()
                    await lookup


if __name__ == "__main__":
    unittest.main()
