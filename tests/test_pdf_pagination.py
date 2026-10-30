from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import app


class PDFPaginationTests(unittest.TestCase):
    def test_each_detailed_record_starts_on_a_new_page_in_all_report_modes(self):
        records = [
            {'title': f'Environmental measurement study {i}', 'year': '2025',
             'authors': ['Research Author'], 'doi': f'10.1000/pagination{i}',
             'abstract': 'Measurements were compared with reference samples. ' * 120}
            for i in range(3)
        ]
        original = app.AcademicPDF
        starts = []

        class TrackedPDF(original):
            def header(self):
                super().header()
                self.content_top = self.get_y()

            def cell(self, w=None, h=None, text='', *args, **kwargs):
                if text.startswith('ITEM '):
                    starts.append((self.page_no(), self.get_y(), self.content_top))
                return super().cell(w, h, text, *args, **kwargs)

        with tempfile.TemporaryDirectory() as root, patch.object(app, 'AcademicPDF', TrackedPDF):
            for guest in (True, False):
                for abstracts in (True, False):
                    for other in (True, False):
                        with self.subTest(guest=guest, abstracts=abstracts, other=other):
                            starts.clear()
                            path = Path(root, 'report.pdf')
                            app.generate_documents('Environmental measurements', records, str(path),
                                                   is_guest=guest, include_abstracts=abstracts,
                                                   is_other=other)
                            self.assertTrue(path.read_bytes().startswith(b'%PDF-'))
                            self.assertEqual(len(starts), len(records))
                            self.assertEqual(len({page for page, _, _ in starts}), len(records))
                            self.assertTrue(all(abs(y - top) < 0.01 for _, y, top in starts))


if __name__ == '__main__':
    unittest.main()
