import time
import unittest
from unittest.mock import patch

from abstracts import normalize_abstract, inverted_abstract, enrich_abstracts
from models import CanonicalPaper
from citations import generate_bibtex_entry, generate_ris_entry
import network


class Response:
    status_code = 200
    def __init__(self, data):
        self.data = data
    def json(self):
        return self.data


class AbstractImportTests(unittest.TestCase):
    def test_structured_jats_preserves_sections_symbols_and_inline_text(self):
        raw = '&lt;jats:abstract&gt;&lt;jats:sec&gt;&lt;jats:title&gt;Methods&lt;/jats:title&gt;&lt;jats:p&gt;Measured &lt;i&gt;in vitro&lt;/i&gt; at 25 &amp;deg;C using H&lt;sub&gt;2&lt;/sub&gt;O.&lt;/jats:p&gt;&lt;/jats:sec&gt;&lt;/jats:abstract&gt;'
        self.assertEqual(normalize_abstract(raw), 'Methods\n\nMeasured in vitro at 25 °C using H2O.')

    def test_placeholders_and_script_are_not_abstracts(self):
        self.assertEqual(normalize_abstract('No abstract provided in source metadata.'), '')
        self.assertEqual(normalize_abstract('Open Access Free Book (Open Library)'), '')
        self.assertEqual(normalize_abstract('<p>Results</p><script>bad()</script>'), 'Results')
        self.assertFalse(CanonicalPaper(title='Book', abstract='Open Access Free Book (Open Library)').has_substantive_abstract)

    def test_inverted_index_handles_malformed_positions(self):
        self.assertEqual(inverted_abstract({'A': [0], 'study': [1, 'x', -2], 'of': [2], 'water': [3]}), 'A study of water')

    def test_batch_import_uses_identifiers_and_never_substitutes_an_unrelated_abstract(self):
        papers = [CanonicalPaper(title=f'Study {i}', doi=f'10.1000/study{i}', sources=['crossref']) for i in range(3)]
        abstract = 'A complete abstract describing the experimental methods and independently measured results.'
        attempted = set()
        def get(source, url, *args, **kwargs):
            if source == 'europepmc':
                self.assertIn('10.1000/study0', kwargs['params']['query'])
                return Response({'resultList': {'result': [
                    {'doi': '10.1000/study0', 'abstractText': '<p>' + abstract + '</p>'},
                    {'doi': '10.1000/unrelated', 'abstractText': 'Unrelated text ' * 30},
                ]}})
            self.assertEqual(source, 'openalex')
            self.assertNotIn('study0', kwargs['params']['filter'])
            return Response({'results': [{'doi': 'https://doi.org/10.1000/study1', 'abstract_inverted_index': {word: [i] for i, word in enumerate(abstract.split())}}]})
        with patch('network.safe_get', side_effect=get) as requests:
            self.assertEqual(enrich_abstracts(papers, 'test', False, time.monotonic()+10, attempted), 2)
            self.assertEqual(requests.call_count, 2)
            self.assertEqual(enrich_abstracts(papers, 'test', False, time.monotonic()+10, attempted), 0)
        self.assertEqual(papers[0].abstract, abstract)
        self.assertEqual(papers[0].field_provenance['abstract'], 'europepmc')
        self.assertEqual(papers[1].field_provenance['abstract'], 'openalex')
        self.assertFalse(papers[2].has_substantive_abstract)

    def test_deadline_and_disabled_abstracts_do_not_generate_requests(self):
        with patch('network.safe_get') as get:
            enrich_abstracts([CanonicalPaper(title='A', doi='10.1000/a')], 'test', False, time.monotonic()-1)
            self.assertFalse(get.called)

    def test_complete_existing_abstract_is_preserved_and_export_is_untruncated(self):
        abstract = 'A detailed measurement of environmental water samples. ' * 40
        paper = CanonicalPaper(title='Water analysis', doi='10.1000/water', abstract=abstract, year='2025')
        with patch('network.safe_get') as get:
            self.assertEqual(enrich_abstracts([paper], 'test', True, time.monotonic()+5), 0)
            self.assertFalse(get.called)
        row = paper.to_dict()
        self.assertIn(abstract.strip(), generate_ris_entry(row))
        self.assertIn(abstract.strip(), generate_bibtex_entry(row))

    def test_expired_fallback_deadline_does_not_wait_for_provider_lock(self):
        with patch.object(network.HTTP, 'get') as get:
            self.assertIsNone(network.safe_get('crossref', 'https://example.test', request_deadline=time.monotonic()-1))
            self.assertFalse(get.called)

    def test_fallback_uses_no_retry_session_and_clamps_timeout(self):
        session = unittest.mock.Mock()
        session.get.return_value = Response({})
        with patch.object(network, 'is_engine_in_cooldown', return_value=False):
            network.safe_get('test-provider', 'https://example.test', timeout=10, request_deadline=time.monotonic()+0.5, http_session=session)
        self.assertLessEqual(session.get.call_args.kwargs['timeout'], 0.5)
        self.assertNotIn('request_deadline', session.get.call_args.kwargs)


if __name__ == '__main__':
    unittest.main()
