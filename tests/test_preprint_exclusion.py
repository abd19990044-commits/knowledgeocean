# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch, MagicMock
from models import CanonicalPaper, is_preprint_record, classify_document_type
import providers
import app

class TestPreprintExclusion(unittest.TestCase):
    def test_preprint_priority_over_review_or_book_type(self):
        # A bioRxiv paper whose title contains 'systematic review' must strictly be a preprint, NOT a peer-reviewed review
        p_biorxiv_rev = CanonicalPaper(
            doi="10.1101/2021.01.01.123456",
            title="A Systematic Review and Meta-Analysis of COVID-19 Treatments",
            journal="bioRxiv",
            publisher="Cold Spring Harbor Laboratory",
            raw_type="preprint"
        )
        self.assertTrue(p_biorxiv_rev.is_preprint)
        self.assertFalse(p_biorxiv_rev.is_peer_reviewed)
        self.assertEqual(p_biorxiv_rev.doc_type, "preprint")
        self.assertEqual(p_biorxiv_rev.doc_partition, "preprint")

        # An arXiv paper must strictly be preprint
        p_arxiv_rev = CanonicalPaper(
            arxiv_id="2308.10620",
            title="A Comprehensive Review of Large Language Models",
            journal="arXiv",
            raw_type="review"
        )
        self.assertTrue(p_arxiv_rev.is_preprint)
        self.assertFalse(p_arxiv_rev.is_peer_reviewed)
        self.assertEqual(p_arxiv_rev.doc_type, "preprint")

    def test_openalex_preprint_record_detection(self):
        # OpenAlex preprint from RePEc / Research Papers in Economics
        self.assertTrue(is_preprint_record(
            journal="RePEc: Research Papers in Economics",
            publisher="Federal Reserve Bank of St. Louis",
            raw_type="preprint"
        ))

        # OpenAlex preprint with posted-content
        self.assertTrue(is_preprint_record(
            doi="10.1101/gr.162339.113",
            title="Analysis of off-target effects of CRISPR",
            journal="Genome Research",
            publisher="Cold Spring Harbor Laboratory",
            raw_type="posted-content"
        ))

    def test_openalex_batch_excludes_preprints_when_toggle_off(self):
        mock_openalex_response = {
            "results": [
                {
                    "display_name": "Peer-Reviewed CRISPR Paper",
                    "doi": "https://doi.org/10.1016/j.cell.2020.01.001",
                    "type": "article",
                    "publication_year": 2020,
                    "primary_location": {
                        "source": {"display_name": "Cell", "host_organization_name": "Elsevier BV"}
                    }
                },
                {
                    "display_name": "Preprint CRISPR Working Paper",
                    "doi": "https://doi.org/10.1101/2020.02.02.999999",
                    "type": "preprint",
                    "publication_year": 2020,
                    "primary_location": {
                        "source": {"display_name": "bioRxiv", "host_organization_name": "Cold Spring Harbor Laboratory"}
                    }
                }
            ]
        }

        with patch("providers.safe_get") as mock_get:
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.json.return_value = mock_openalex_response
            mock_get.return_value = mock_res

            # When include_preprint is False
            state_no_preprint = {'offset': 0, 'page': 1, 'cursor': '*', 'exhausted': False, 'include_preprint': False}
            papers = providers.fetch_openalex_batch("crispr", state_no_preprint, "keyword", "", "test_task", False, 10)

            self.assertEqual(len(papers), 1)
            self.assertEqual(papers[0].title, "Peer-Reviewed CRISPR Paper")
            self.assertFalse(papers[0].is_preprint)

            # When include_preprint is True
            state_with_preprint = {'offset': 0, 'page': 1, 'cursor': '*', 'exhausted': False, 'include_preprint': True}
            papers_all = providers.fetch_openalex_batch("crispr", state_with_preprint, "keyword", "", "test_task", False, 10)

            self.assertEqual(len(papers_all), 2)
            self.assertTrue(any(p.is_preprint for p in papers_all))

    def test_europepmc_query_and_exclusion_when_toggle_off(self):
        with patch("providers.safe_get") as mock_get:
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.json.return_value = {
                "resultList": {
                    "result": [
                        {"title": "Peer Article", "doi": "10.1038/nature1", "source": "MED", "pubYear": "2021"},
                        {"title": "Preprint Article", "doi": "10.1101/ppr1", "source": "PPR", "pubYear": "2021"}
                    ]
                }
            }
            mock_get.return_value = mock_res

            state_no_ppr = {'offset': 0, 'cursor': '*', 'exhausted': False, 'include_preprint': False}
            papers = providers.fetch_europepmc_batch("crispr", state_no_ppr, "keyword", "", "test_task", False, 10)

            # Check that query passed to Europe PMC has AND NOT (SRC:PPR)
            called_params = mock_get.call_args[1].get("params", {})
            self.assertIn("NOT (SRC:PPR)", called_params.get("query", ""))

            # Check that PPR result is excluded from output
            self.assertEqual(len(papers), 1)
            self.assertEqual(papers[0].title, "Peer Article")

    def test_crossref_exclusion_when_toggle_off(self):
        with patch("providers.safe_get") as mock_get:
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.json.return_value = {
                "message": {
                    "items": [
                        {"title": ["Peer Paper"], "DOI": "10.1016/j.cell.1", "type": "journal-article", "publisher": "Elsevier"},
                        {"title": ["Posted Content Preprint"], "DOI": "10.21203/rs.3.rs-1", "type": "posted-content", "publisher": "Research Square"}
                    ]
                }
            }
            mock_get.return_value = mock_res

            state_no_ppr = {'offset': 0, 'exhausted': False, 'include_preprint': False}
            papers = providers.fetch_crossref_batch("cancer", state_no_ppr, "keyword", "", "test_task", False, 10)

            self.assertEqual(len(papers), 1)
            self.assertEqual(papers[0].title, "Peer Paper")

    def test_final_papers_filtered_in_search_results(self):
        # Verify that if any preprint record is in paper_data when is_include_preprint=False, it is filtered out
        papers_list = [
            {"title": "Published 1", "doi": "10.1038/s1", "is_preprint": False, "publisher": "Springer Nature"},
            {"title": "Preprint from OpenAlex", "doi": "10.1101/2021", "is_preprint": True, "publisher": "Cold Spring Harbor Laboratory"},
            {"title": "Working Paper", "doi": "10.2139/ssrn.1", "is_preprint": True, "publisher": "SSRN"}
        ]

        is_include_preprint = False
        peer = [
            p for p in papers_list
            if not (p.get('is_preprint') or is_preprint_record(doi=p.get('doi'), journal=p.get('journal'), title=p.get('title'), publisher=p.get('publisher')))
        ]
        self.assertEqual(len(peer), 1)
        self.assertEqual(peer[0]["title"], "Published 1")

if __name__ == '__main__':
    unittest.main()
