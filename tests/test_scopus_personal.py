"""Personal Scopus access and conservative quota handling, without real API calls."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import requests
import app
import network
import providers
from models import CanonicalPaper

KEY = "test_personal_key_1234567890"


def response(status=200, payload=None, headers=None):
    item = requests.Response()
    item.status_code = status
    item.headers.update(headers or {})
    item._content = json.dumps(payload or {"search-results": {"entry": []}}).encode()
    return item


class PersonalScopusTests(unittest.TestCase):
    def test_vip_uses_platform_environment_key_without_personal_key(self):
        result = response(payload={"search-results": {"entry": [{"dc:title": "Graphene research", "prism:doi": "10.1000/graphene"}], "opensearch:totalResults": "1"}})
        with patch.dict(os.environ, {"ELSEVIER_API_KEY": KEY}), patch.object(providers, "get_engine_circuit_status", return_value=None), patch.object(providers, "safe_get", return_value=result) as get:
            state = {}
            papers = providers.fetch_elsevier_batch("graphene", state, "keyword", "", "", False, 5)
            self.assertEqual(len(papers), 1)
            self.assertEqual(papers[0].doi, "10.1000/graphene")
            self.assertEqual(get.call_args.kwargs["headers"]["X-ELS-APIKey"], KEY)
            self.assertEqual(get.call_args.kwargs["params"]["view"], "STANDARD")
            self.assertNotIn(KEY, json.dumps(state))

    def test_vip_can_use_loaded_platform_key(self):
        result = response(payload={"search-results": {"entry": [{"dc:title": "Climate research"}]}})
        with patch.dict(os.environ, {"ELSEVIER_API_KEY": ""}), patch.object(providers, "ELSEVIER_API_KEY", KEY), patch.object(providers, "get_engine_circuit_status", return_value=None), patch.object(providers, "safe_get", return_value=result) as get:
            self.assertEqual(len(providers.fetch_elsevier_batch("climate", {}, "keyword", "", "", False, 5)), 1)
            self.assertEqual(get.call_args.kwargs["headers"]["X-ELS-APIKey"], KEY)

    def test_vip_missing_platform_key_stops_with_actionable_notice(self):
        with patch.dict(os.environ, {"ELSEVIER_API_KEY": ""}), patch.object(providers, "ELSEVIER_API_KEY", ""), patch.object(providers, "safe_get") as get:
            state = {}
            self.assertEqual(providers.fetch_elsevier_batch("graphene", state, "keyword", "", "", False, 5), [])
            self.assertTrue(state["exhausted"])
            self.assertEqual(state["provider_status"], "not_configured")
            self.assertIn("No platform Elsevier key", state["warning"])
            get.assert_not_called()

    def test_vip_pipeline_collects_scopus_records_with_platform_key(self):
        result = response(payload={"search-results": {"entry": [{"dc:title": "Graphene research", "dc:creator": "Smith, J.", "prism:doi": "10.1000/graphene", "prism:coverDate": "2025-01-01"}], "opensearch:totalResults": "1"}})
        with tempfile.TemporaryDirectory() as root:
            pdf = Path(root, "report.pdf")
            pdf.write_bytes(b"%PDF-test")
            builder = Mock()
            builder.finish.return_value = ([str(pdf)], [])
            with patch.dict(os.environ, {"ELSEVIER_API_KEY": KEY}), patch.object(providers, "get_engine_circuit_status", return_value=None), patch.object(providers, "safe_get", return_value=result) as get, patch.object(app, "FETCH_BATCH_MAP", {"elsevier": providers.fetch_elsevier_batch}), patch.object(app, "DOWNLOAD_DIR", root), patch.object(app, "db_set_task"), patch.object(app, "ReportBuilder", return_value=builder):
                try:
                    app.process_pipeline("graphene", db_source="elsevier", limit=1, is_guest=False, uh="test-owner", task_id="vip-scopus-test")
                    task = app.TASKS["vip-scopus-test"]
                    self.assertEqual(task["status"], "completed", task.get("error"))
                    self.assertEqual(len(task["papers"]), 1)
                    self.assertEqual(task["papers"][0]["sources"], ["elsevier"])
                    self.assertEqual(get.call_count, 1)
                    self.assertFalse(get.call_args.args[3])
                    self.assertNotIn(KEY, json.dumps(task))
                finally:
                    app.TASKS.pop("vip-scopus-test", None)

    def test_vip_pipeline_reports_missing_key_without_repeating_collection(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"ELSEVIER_API_KEY": ""}), patch.object(providers, "ELSEVIER_API_KEY", ""), patch.object(providers, "safe_get") as get, patch.object(app, "FETCH_BATCH_MAP", {"elsevier": providers.fetch_elsevier_batch}), patch.object(app, "DOWNLOAD_DIR", root), patch.object(app, "db_set_task"):
            try:
                app.process_pipeline("graphene", db_source="elsevier", limit=5, is_guest=False, uh="test-owner", task_id="vip-scopus-missing-test")
                task = app.TASKS["vip-scopus-missing-test"]
                self.assertEqual(task["status"], "error")
                self.assertIn("No platform Elsevier key", task["error"])
                self.assertEqual(task["provider_diagnostics"]["elsevier"]["status"], "not_configured")
                self.assertEqual(task["provider_diagnostics"]["elsevier"]["returned"], 0)
                get.assert_not_called()
            finally:
                app.TASKS.pop("vip-scopus-missing-test", None)

    def test_guest_never_falls_back_to_platform_secret(self):
        with patch.dict(os.environ, {"ELSEVIER_API_KEY": "PLATFORM_PRIVATE_KEY"}), patch.object(providers, "safe_get") as get:
            self.assertEqual(providers.fetch_elsevier_batch("climate", {}, "keyword", "", "", True, 25), [])
            get.assert_not_called()

    def test_personal_key_uses_standard_view_and_at_most_25_records(self):
        entries = [{"dc:title": f"Climate research {i}", "dc:creator": "Smith, J.", "prism:doi": f"10.1000/climate{i}"} for i in range(25)]
        result = response(payload={"search-results": {"entry": entries, "opensearch:totalResults": "200"}})
        with patch.object(providers, "get_engine_circuit_status", return_value=None), patch.object(providers, "safe_get", return_value=result) as get:
            state = {}
            papers = providers.fetch_elsevier_batch("climate", state, "keyword", "", "", True, 250, api_key=KEY)
            self.assertEqual(len(papers), 25)
            self.assertEqual(papers[0].authors, ["Smith, J."])
            self.assertEqual(papers[0].publisher, "")
            self.assertEqual(get.call_args.kwargs["params"], {"query": "TITLE-ABS-KEY(climate)", "view": "STANDARD", "field": providers.SCOPUS_CITATION_FIELDS, "count": 25, "start": 0})
            self.assertNotIn("description", get.call_args.kwargs["params"]["field"])
            self.assertNotIn("cursor", get.call_args.kwargs["params"])
            self.assertNotIn("X-ELS-Insttoken", get.call_args.kwargs["headers"])
            self.assertEqual(get.call_args.kwargs["headers"]["X-ELS-APIKey"], KEY)
            self.assertEqual(state["offset"], 25)
            self.assertNotIn(KEY, json.dumps(state))
            providers.fetch_elsevier_batch("climate", state, "keyword", "", "", True, 250, api_key=KEY)
            self.assertEqual(get.call_args.kwargs["params"]["start"], 25)

    def test_rejected_personal_key_never_uses_platform_key(self):
        with patch.dict(os.environ, {"ELSEVIER_API_KEY": "PLATFORM_PRIVATE_KEY"}), patch.object(providers, "get_engine_circuit_status", return_value=None), patch.object(providers, "safe_get", return_value=response(403)) as get:
            state = {}
            self.assertEqual(providers.fetch_elsevier_batch("education", state, "keyword", "", "", True, 5, api_key=KEY), [])
            self.assertEqual(state["provider_status"], "access_denied")
            self.assertIn("entitlements", state["warning"])
            self.assertNotIn(KEY, state["warning"])
            self.assertEqual(get.call_count, 1)
            self.assertEqual(get.call_args.kwargs["headers"]["X-ELS-APIKey"], KEY)

    def test_free_platform_and_personal_keys_use_same_minimal_request(self):
        calls = []
        with patch.dict(os.environ, {"ELSEVIER_API_KEY": KEY}), patch.object(providers, "get_engine_circuit_status", return_value=None), patch.object(providers, "safe_get", return_value=response()) as get:
            for guest, key in ((False, None), (True, KEY), (False, KEY)):
                providers.fetch_elsevier_batch("energy", {}, "keyword", "", "", guest, 250, api_key=key)
                calls.append(get.call_args.kwargs)
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(calls[1], calls[2])
        self.assertEqual(calls[0]["params"]["field"], "identifier,eid,title,creator,doi,coverDate,publicationName")

    def test_authentication_error_is_not_reported_as_missing_entitlements(self):
        result = response(401, {"service-error": {"status": {"statusCode": "AUTHENTICATION_ERROR", "statusText": "sensitive " + KEY}}})
        with patch.object(providers, "get_engine_circuit_status", return_value=None), patch.object(providers, "safe_get", return_value=result) as get:
            state = {}
            self.assertEqual(providers.fetch_elsevier_batch("energy", state, "keyword", "", "", True, 5, api_key=KEY), [])
            self.assertEqual(state["provider_status"], "authentication_failed")
            self.assertIn("HTTP 401; AUTHENTICATION_ERROR", state["warning"])
            self.assertNotIn(KEY, json.dumps(state))
            self.assertEqual(get.call_count, 1)

    def test_forbidden_free_search_retains_safe_error_code(self):
        result = response(403, {"error-response": {"error-code": "AUTHORIZATION_ERROR", "error-message": KEY}})
        with patch.object(providers, "get_engine_circuit_status", return_value=None), patch.object(providers, "safe_get", return_value=result):
            state = {}
            providers.fetch_elsevier_batch("energy", state, "keyword", "", "", True, 5, api_key=KEY)
            self.assertEqual(state["provider_status"], "access_denied")
            self.assertIn("HTTP 403; AUTHORIZATION_ERROR", state["warning"])
            self.assertIn("key may be valid", state["warning"])
            self.assertNotIn(KEY, json.dumps(state))

    def test_error_details_are_allowlisted_and_not_echoed(self):
        result = response(400, {"error-response": {"error-code": KEY, "error-message": KEY}}, {"X-ELS-Status": KEY})
        with patch.object(providers, "get_engine_circuit_status", return_value=None), patch.object(providers, "safe_get", return_value=result):
            state = {}
            providers.fetch_elsevier_batch("energy", state, "keyword", "", "", True, 5, api_key=KEY)
            self.assertEqual(state["provider_status"], "invalid_query")
            self.assertIn("HTTP 400", state["warning"])
            self.assertNotIn(KEY, json.dumps(state))

    def test_authentication_cooldown_is_distinct_from_forbidden(self):
        with patch.object(providers, "get_engine_circuit_status", return_value={"reason": "HTTP 401 Auth/Forbidden"}), patch.object(providers, "safe_get") as get:
            state = {}
            providers.fetch_elsevier_batch("energy", state, "keyword", "", "", True, 5, api_key=KEY)
            self.assertEqual(state["provider_status"], "authentication_failed")
            get.assert_not_called()

    def test_missing_search_payload_is_not_a_successful_empty_search(self):
        with patch.object(providers, "get_engine_circuit_status", return_value=None), patch.object(providers, "safe_get", return_value=response(200, {"unexpected": "response"})):
            state = {}
            providers.fetch_elsevier_batch("energy", state, "keyword", "", "", True, 5, api_key=KEY)
            self.assertEqual(state["provider_status"], "unavailable")

    def test_basic_single_record_object_is_supported(self):
        result = response(payload={"search-results": {"entry": {"dc:title": "Digital archives", "prism:doi": "10.1000/archive"}, "opensearch:totalResults": "1"}})
        with patch.object(providers, "get_engine_circuit_status", return_value=None), patch.object(providers, "safe_get", return_value=result):
            state = {}
            papers = providers.fetch_elsevier_batch("archives", state, "keyword", "", "", True, 5, api_key=KEY)
            self.assertEqual(len(papers), 1)
            self.assertTrue(state["exhausted"])

    def test_successful_last_quota_request_keeps_records_and_stops_pagination(self):
        result = response(payload={"search-results": {"entry": [{"dc:title": "Energy storage", "prism:doi": "10.1000/energy"}]}}, headers={"X-RateLimit-Remaining": "0"})
        with patch.object(providers, "get_engine_circuit_status", return_value=None), patch.object(providers, "safe_get", return_value=result):
            state = {}
            self.assertEqual(len(providers.fetch_elsevier_batch("energy", state, "keyword", "", "", True, 1, api_key=KEY)), 1)
            self.assertTrue(state["exhausted"])
            self.assertEqual(state["provider_status"], "quota_exceeded")

    def test_guest_comprehensive_pipeline_passes_own_key_without_upgrade(self):
        seen = []
        def fetch(query, state, mode, affiliation, task_id, is_guest, batch_size, *, api_key=None):
            seen.append((is_guest, api_key))
            state["exhausted"] = True
            return [CanonicalPaper(title="Climate research", doi="10.1000/climate", authors=["Test Author"], year="2025", sources=["elsevier"])]
        with tempfile.TemporaryDirectory() as root, patch.object(app, "DOWNLOAD_DIR", root), patch.object(app, "FETCH_BATCH_MAP", {"elsevier": fetch}), patch.object(app, "db_set_task"), patch.object(app, "generate_documents", side_effect=lambda q, p, path, *a, **kw: Path(path).write_bytes(b"%PDF-test")):
            try:
                app.process_pipeline("climate", db_source="all", limit=1, is_guest=True, uh="test-owner", task_id="own-key-test", elsevier_api_key=KEY)
                self.assertEqual(seen, [(True, KEY)])
                self.assertEqual(app.TASKS["own-key-test"]["status"], "completed")
                self.assertNotIn(KEY, json.dumps(app.TASKS["own-key-test"]))
            finally:
                app.TASKS.pop("own-key-test", None)


class ScopusQuotaTests(unittest.TestCase):
    def test_published_guides_use_requested_terminology_and_general_examples(self):
        root = Path(__file__).resolve().parents[1]
        content = json.loads((root / "scripts" / "user_guides.json").read_text())
        for language in ("ar", "en"):
            text = json.dumps(content[language], ensure_ascii=False).lower()
            self.assertNotIn("vip", text)
            self.assertNotIn("naproxen", text)
            self.assertNotIn("نابروكس", text)
            self.assertNotIn("الرمز الثانوي", text)
            self.assertGreaterEqual(len(content[language]), 6)
        self.assertIn("رمز الوصول", json.dumps(content["ar"], ensure_ascii=False))
        self.assertIn("Access Code", json.dumps(content["en"]))

    def test_zero_remaining_quota_stops_calls_until_reported_reset(self):
        scope = "elsevier:" + hashlib.sha256(KEY.encode()).hexdigest()
        reset = time.time() + 7200
        result = response(headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(reset)})
        with patch.dict(network.CIRCUIT_STATES, {}, clear=True), patch.object(network.HTTP, "get", return_value=result) as get, patch.object(network.time, "sleep"):
            self.assertIs(network.safe_get("elsevier", "https://api.elsevier.com/content/search/scopus", circuit_key=scope, quota_aware=True), result)
            self.assertIsNone(network.safe_get("elsevier", "https://api.elsevier.com/content/search/scopus", circuit_key=scope, quota_aware=True))
            self.assertEqual(get.call_count, 1)
            self.assertGreaterEqual(network.get_engine_circuit_status(scope)["cooldown_until"], reset - 1)
            self.assertFalse(network.is_engine_in_cooldown("elsevier:another-key"))
            self.assertNotIn("quota_aware", get.call_args.kwargs)

    def test_retry_after_http_date_is_respected_without_blocking_sleep(self):
        from email.utils import formatdate
        now = time.time()
        result = response(429, headers={"Retry-After": formatdate(now + 180, usegmt=True)})
        with patch.dict(network.CIRCUIT_STATES, {}, clear=True), patch.object(network.HTTP, "get", return_value=result), patch.object(network.time, "sleep") as sleep:
            network.safe_get("elsevier", "https://api.elsevier.com/content/search/scopus", circuit_key="elsevier:date-test", quota_aware=True)
            self.assertGreater(network.get_engine_circuit_status("elsevier:date-test")["cooldown_until"], now + 170)
            sleep.assert_called_once_with(2.0)

    def test_scopus_transport_does_not_retry_and_has_conservative_spacing(self):
        self.assertEqual(network.HTTP.get_adapter("https://api.elsevier.com/content/search/scopus").max_retries.total, 0)
        self.assertGreaterEqual(network.ENGINE_DELAYS["elsevier"], 2.0)


if __name__ == "__main__":
    unittest.main()
