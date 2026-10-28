# Regression checks for the search-result failure UI and backend diagnostics.
# Run: python -m unittest discover -s tests -p "test_*.py"
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class SearchFailureRegressionTests(unittest.TestCase):
    def test_failed_task_is_not_rendered_as_complete(self):
        js = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
        self.assertIn('if (data.status === "completed") {', js)
        self.assertNotIn('data.status === "completed" || data.progress >= 100', js)
        self.assertIn('data.status === "error" || data.status === "failed"', js)

    def test_provider_errors_are_recorded_and_logged(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("provider_diagnostics", source)
        self.assertIn('log.exception("Engine %s batch error in task %s"', source)
        self.assertIn("Search task %s timed out waiting for providers", source)
        self.assertIn("returned no qualifying papers", source)

if __name__ == "__main__":
    unittest.main()
