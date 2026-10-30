"""API-level similarity boundaries and source-completion reporting."""
import threading
import time
import unittest
from unittest.mock import Mock, patch

import requests
from fastapi.testclient import TestClient
import app


def response(payload=None):
    return Mock(status_code=200, json=Mock(return_value=payload or {}),
                text='<feed xmlns="http://www.w3.org/2005/Atom"/>')


class TitleSearchThresholdTests(unittest.TestCase):
    def query(self, get):
        with patch.object(app.requests, "get", side_effect=get), patch.object(app, "search_verified_registry", return_value=[]), patch.object(app, "db_check_ip_ban", return_value=(False, 0)), patch.object(app, "db_check_rate_limit", return_value=(False, 99)):
            with TestClient(app.app, base_url="https://testserver") as client:
                result = client.post("/api/find-doi", data={"title": "Climate research", "limit": "10"})
                self.assertEqual(result.status_code, 200)
                return result.json()

    def test_fifty_percent_is_included_and_lower_scores_are_excluded(self):
        def get(url, **kwargs):
            return response({"message": {"items": [{"title": [title], "DOI": f"10.1000/{i}"} for i, title in enumerate(["Below", "Boundary", "Above"]) ]}}) if "api.crossref" in url else response()
        with patch.object(app, "calculate_accurate_title_similarity", side_effect=lambda query, title: {"Below": 49.99, "Boundary": 50.0, "Above": 80.0}[title]):
            result = self.query(get)
        self.assertEqual([r["similarity"] for r in result["results"]], [80.0, 50.0])
        self.assertEqual(result["count"], 2)
        self.assertTrue(result["scan_complete"])
        self.assertEqual(result["min_similarity"], 50.0)
        self.assertEqual(len(result["source_statuses"]), 8)

    def test_weak_first_response_does_not_end_search_before_later_match(self):
        weak_seen = threading.Event()
        def get(url, **kwargs):
            if "api.crossref" in url:
                weak_seen.set()
                return response({"message": {"items": [{"title": ["Weak"], "DOI": "10.1000/weak"}]}})
            if "api.openalex" in url:
                self.assertTrue(weak_seen.wait(1))
                time.sleep(0.02)
                return response({"results": [{"id": "late", "title": "Later match", "doi": "https://doi.org/10.1000/later"}]})
            return response()
        with patch.object(app, "calculate_accurate_title_similarity", side_effect=lambda query, title: 75 if title == "Later match" else 20):
            result = self.query(get)
        self.assertEqual([r["doi"] for r in result["results"]], ["10.1000/later"])
        self.assertTrue(result["scan_complete"])

    def test_low_similarity_triggers_an_alternative_crossref_query(self):
        seen = []
        def get(url, **kwargs):
            if "api.crossref" in url:
                seen.append(url)
                title = "Alternative match" if "query.bibliographic=" in url else "Weak title"
                return response({"message": {"items": [{"title": [title], "DOI": "10.1000/alternative" if title == "Alternative match" else "10.1000/weak"}]}})
            return response()
        with patch.object(app, "calculate_accurate_title_similarity", side_effect=lambda query, title: 70 if title == "Alternative match" else 10):
            result = self.query(get)
        self.assertEqual(len(seen), 2)
        self.assertEqual(result["results"][0]["title"], "Alternative match")

    def test_no_match_is_reported_only_after_sources_complete(self):
        result = self.query(lambda *args, **kwargs: response())
        self.assertEqual(result["results"], [])
        self.assertEqual(result["outcome"], "no_match")
        self.assertTrue(all(s == "completed" for s in result["source_statuses"].values()))

    def test_source_failure_is_not_described_as_a_complete_no_match(self):
        def get(url, **kwargs):
            if "api.openalex" in url:
                raise requests.Timeout("test source timeout")
            return response()
        result = self.query(get)
        self.assertFalse(result["scan_complete"])
        self.assertEqual(result["outcome"], "incomplete_scan")
        self.assertEqual(result["source_statuses"]["openalex"], "unavailable")

    def test_overall_timeout_reports_incomplete_source_scan(self):
        release, finished = threading.Event(), threading.Event()
        def get(url, **kwargs):
            if "api.openalex" in url:
                release.wait(1)
                finished.set()
                return response({"results": [{"id": str(i), "title": "Climate research"} for i in range(5)]})
            return response()
        try:
            with patch.object(app, "TITLE_SEARCH_MAX_SECONDS", 0.03):
                result = self.query(get)
            self.assertFalse(result["scan_complete"])
            self.assertEqual(result["source_statuses"]["openalex"], "timed_out")
            self.assertEqual(result["outcome"], "incomplete_scan")
        finally:
            release.set()
            self.assertTrue(finished.wait(1))
