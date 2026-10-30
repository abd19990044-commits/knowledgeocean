"""Run the shipped HTM DOI result templates through the React prop contract."""
from pathlib import Path
import subprocess
import unittest


class FrontendRenderTests(unittest.TestCase):
    def test_doi_results_and_errors_keep_app_mounted_in_both_languages(self):
        result = subprocess.run(
            ["node", str(Path(__file__).with_name("doi_render_regression.cjs"))],
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
