"""Result-count budgets and five-minute matching inactivity, without waiting."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import app
from models import CanonicalPaper


class Clock:
    def __init__(self):
        # Exact test seconds avoid rounding changes across runner uptimes.
        self.now = 1_000_000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class SearchBudgetTests(unittest.TestCase):
    def test_numeric_counts_get_ten_seconds_each(self):
        for count, seconds in ((1, 10), (5, 50), (10, 100), (25, 250), (50, 500), (100, 1000), (250, 2500)):
            with self.subTest(count=count):
                budget = app.SearchBudget(count, clock=Clock())
                self.assertEqual(budget.total_seconds, seconds)

    def test_comprehensive_total_is_three_hours(self):
        clock = Clock()
        budget = app.SearchBudget(10 ** 12, comprehensive=True, clock=clock)
        self.assertEqual(budget.total_seconds, 10800)
        clock.advance(10799)
        budget.record_match()
        self.assertIsNone(budget.stop_reason())
        clock.advance(1)
        self.assertEqual(budget.stop_reason(), "time_budget")

    def test_both_modes_stop_at_five_minutes_without_matches(self):
        for comprehensive in (False, True):
            clock = Clock()
            budget = app.SearchBudget(50, comprehensive=comprehensive, clock=clock)
            clock.advance(299)
            self.assertIsNone(budget.stop_reason())
            clock.advance(1)
            self.assertEqual(budget.stop_reason(), "no_new_matches")

    def test_new_match_restarts_inactivity_without_extending_total_deadline(self):
        clock = Clock()
        budget = app.SearchBudget(50, clock=clock)
        clock.advance(250)
        budget.record_match()
        clock.advance(200)
        self.assertIsNone(budget.stop_reason())
        self.assertAlmostEqual(budget.remaining(), 50)
        clock.advance(50)
        self.assertEqual(budget.stop_reason(), "time_budget")

    def test_small_request_ends_before_five_minute_inactivity(self):
        clock = Clock()
        budget = app.SearchBudget(5, clock=clock)
        clock.advance(50)
        self.assertEqual(budget.stop_reason(), "time_budget")


class PipelineBudgetTests(unittest.TestCase):
    def run_pipeline(self, *, limit, step, same_record=False, empty=False, comprehensive=False):
        clock, calls = Clock(), []
        real_budget = app.SearchBudget

        def fetch(query, state, *args):
            clock.advance(step)
            calls.append(1)
            if empty:
                return []
            index = 1 if same_record else len(calls)
            return [CanonicalPaper(title=f"Climate research {index}", doi=f"10.1000/climate{index}", authors=["Test Author"], year="2025", journal="Test Journal", raw_type="journal-article", sources=["crossref"])]

        with tempfile.TemporaryDirectory() as root, patch.object(app, "DOWNLOAD_DIR", root), patch.object(app, "FETCH_BATCH_MAP", {"crossref": fetch}), patch.object(app, "SearchBudget", side_effect=lambda target_limit, comprehensive: real_budget(target_limit, comprehensive, clock)), patch.object(app, "db_set_task"), patch.object(app, "generate_documents", side_effect=lambda q, p, path, *a, **kw: Path(path).write_bytes(b"%PDF-test")):
            try:
                app.process_pipeline("climate", db_source="crossref", limit=limit, uh="test-owner", task_id="budget-pipeline-test", is_guest=True, comprehensive_search=comprehensive)
                return dict(app.TASKS["budget-pipeline-test"]), len(calls)
            finally:
                app.TASKS.pop("budget-pipeline-test", None)

    def test_more_than_four_rounds_can_complete_requested_count(self):
        task, calls = self.run_pipeline(limit=7, step=1)
        self.assertEqual(calls, 7)
        self.assertEqual(task["status"], "completed")
        self.assertEqual(len(task["papers"]), 7)
        self.assertEqual(task["search_budget_seconds"], 70)
        self.assertEqual(task["finish_reason"], "target_reached")
        self.assertIn("Author, T.", task["papers"][0]["apa"])
        self.assertIn("Test Journal", task["papers"][0]["apa_html"])
        self.assertNotIn("<b", task["papers"][0]["apa_html"])

    def test_comprehensive_budget_does_not_bypass_result_quota(self):
        task, calls = self.run_pipeline(limit=3, step=1, comprehensive=True)
        self.assertEqual(calls, 3)
        self.assertEqual(len(task["papers"]), 3)
        self.assertEqual(task["search_budget_seconds"], 10800)

    def test_duplicates_do_not_restart_five_minute_inactivity(self):
        task, calls = self.run_pipeline(limit=50, step=100, same_record=True)
        self.assertEqual(calls, 4)
        self.assertEqual(task["status"], "completed")
        self.assertEqual(len(task["papers"]), 1)
        self.assertEqual(task["finish_reason"], "no_new_matches")

    def test_empty_rounds_continue_until_inactivity_budget(self):
        task, calls = self.run_pipeline(limit=50, step=100, empty=True)
        self.assertEqual(calls, 3)
        self.assertEqual(task["status"], "error")
        self.assertEqual(task["finish_reason"], "no_new_matches")

    def test_late_record_cannot_restart_expired_inactivity(self):
        task, calls = self.run_pipeline(limit=50, step=301)
        self.assertEqual(calls, 1)
        self.assertEqual(task["status"], "error")
        self.assertEqual(task["finish_reason"], "no_new_matches")

    def test_numeric_total_budget_preserves_partial_results(self):
        task, calls = self.run_pipeline(limit=50, step=100)
        self.assertEqual(calls, 5)
        self.assertEqual(task["status"], "completed")
        self.assertEqual(len(task["papers"]), 4)
        self.assertEqual(task["finish_reason"], "time_budget")


if __name__ == "__main__":
    unittest.main()
