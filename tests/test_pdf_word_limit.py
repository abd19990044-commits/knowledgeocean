from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import app
import report_builder as reports


class PDFWordLimitTests(unittest.TestCase):
    def test_exact_limit_is_allowed_and_next_word_is_rejected(self):
        pdf = object.__new__(app.AcademicPDF)
        pdf.word_count = 0
        pdf._count_words('word ' * 500_000)
        self.assertEqual(pdf.word_count, 500_000)
        with self.assertRaises(reports.PDFWordLimitExceeded):
            pdf._count_words('extra')

    def test_counter_covers_cells_and_paragraphs(self):
        pdf = object.__new__(app.AcademicPDF)
        pdf.word_count = 0
        with patch.object(app.FPDF, 'cell'), patch.object(app.FPDF, 'multi_cell'):
            pdf.cell(0, 5, 'Document heading')
            pdf.multi_cell(0, 5, 'Full abstract paragraph')
        self.assertEqual(pdf.word_count, 5)

    def test_oversized_source_is_retained_in_one_text_file_without_division(self):
        rendered = []
        def render(query, papers, path, **kwargs):
            words = sum(reports.count_words(row['abstract']) for row in papers)
            if words > 4000:
                raise reports.PDFWordLimitExceeded()
            rendered.extend(row['abstract'] for row in papers)
            Path(path).write_bytes(b'%PDF-1.4\n%%EOF')
            return words + 100
        abstract = ' '.join(f'word{i}' for i in range(10001))
        with tempfile.TemporaryDirectory() as root, patch.object(reports, 'MAX_PDF_WORDS', 5000), patch.object(app, 'generate_documents', side_effect=render):
            outputs = reports._render({'kind':'report', 'query':'Water', 'papers':[{'title':'A long study','abstract':abstract}], 'path':str(Path(root,'test.pdf')), 'options':{'include_abstracts':True}})
            self.assertEqual(len(outputs), 1)
            self.assertEqual(outputs[0]['file_type'], 'txt')
            self.assertTrue(outputs[0]['oversized_record'])
            self.assertEqual(sum(item['records'] for item in outputs), 1)
            import json
            self.assertEqual(json.loads(Path(outputs[0]['path']).read_text())['abstract'], abstract)
            self.assertEqual(rendered, [])
            self.assertTrue(all(Path(item['path']).is_file() for item in outputs))

    def test_batches_split_only_between_whole_records(self):
        rendered = []
        def render(query, papers, path, **kwargs):
            rendered.append(papers)
            Path(path).write_bytes(b'%PDF-1.4\n%%EOF')
            return sum(reports.count_words(p['abstract']) for p in papers) + 100
        rows = [{'title':f'Record {i}', 'doi':f'10.1000/{i}', 'abstract':'word ' * 1000} for i in range(4)]
        with tempfile.TemporaryDirectory() as root, patch.object(reports, 'MAX_PDF_WORDS', 5000), patch.object(app, 'generate_documents', side_effect=render):
            outputs = reports._render({'kind':'report','query':'Water','papers':rows,'path':str(Path(root,'test.pdf')),'options':{'include_abstracts':True}})
            self.assertTrue(all(p['word_count'] <= 5000 for p in outputs))
            flattened = [row for batch in rendered for row in batch]
            self.assertEqual(flattened, rows)
            self.assertEqual(len(flattened), len({row['doi'] for row in flattened}))


if __name__ == '__main__':
    unittest.main()
