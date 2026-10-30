import csv
import json
import os
from pathlib import Path
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch

import app
import report_builder as reports
from models import CanonicalPaper


def papers(count):
    return [CanonicalPaper(title=f'Water analysis record {i:04d}', doi=f'10.1000/record{i}', year='2025', authors=['Research Author'], journal='Test Journal', sources=['crossref']) for i in range(count)]


class ReportBuilderTests(unittest.TestCase):
    def test_large_index_is_partitioned_without_losing_records(self):
        received = []
        def render(job):
            received.append(job)
            Path(job['path']).write_text('test PDF')
            return job['path']
        with tempfile.TemporaryDirectory() as root, ThreadPoolExecutor(2) as pool, patch.object(reports, '_submit', side_effect=lambda job, **kw: pool.submit(render, job)):
            builder = reports.ReportBuilder(root, 'Water analysis', 'test', include_abstracts=True)
            records = papers(1001)
            builder.prepare(records)
            try:
                files, manifest = builder.finish(records)
                self.assertTrue(all(Path(path).is_file() for path in files))
                for kind, size in (('report', 100), ('index', 250)):
                    jobs = [job for job in received if job['kind'] == kind]
                    self.assertTrue(all(len(job['papers']) <= size for job in jobs))
                    ids = [row['doi'] for job in jobs for row in job['papers']]
                    self.assertEqual(len(ids), 1001)
                    self.assertEqual(len(set(ids)), 1001)
                    self.assertEqual(sum(part['records'] for part in manifest if part['kind'] == kind), 1001)
                with open(next(path for path in files if path.endswith('.csv')), encoding='utf-8-sig') as stream:
                    self.assertEqual(len(list(csv.reader(stream))), 1002)
                self.assertIn('Complete CSV index', Path(next(path for path in files if path.endswith('.html'))).read_text())
            finally:
                builder.close()
            self.assertFalse(os.path.exists(builder.workdir))

    def test_late_abstract_enrichment_refreshes_prebuilt_batches(self):
        received = []
        def render(job):
            received.append(job)
            Path(job['path']).write_text('test PDF')
            return job['path']
        with tempfile.TemporaryDirectory() as root, ThreadPoolExecutor(2) as pool, patch.object(reports, '_submit', side_effect=lambda job, **kw: pool.submit(render, job)):
            builder = reports.ReportBuilder(root, 'Water', 'test', include_abstracts=True)
            records = papers(100)
            builder.prepare(records)
            builder.prepared[0]['future'].result()
            records[0].abstract = 'Newly imported complete experimental abstract. ' * 25
            try:
                _, manifest = builder.finish(records)
                report_jobs = [job for job in received if job['kind'] == 'report']
                self.assertEqual(len(report_jobs), 2)
                self.assertIn('Newly imported', report_jobs[-1]['papers'][0]['abstract'])
                self.assertFalse(next(part for part in manifest if part['kind']=='report')['prepared_during_search'])
            finally:
                builder.close()

    def test_unchanged_prebuilt_batch_is_reused(self):
        received = []
        def render(job):
            received.append(job)
            Path(job['path']).write_text('test PDF')
            return job['path']
        with tempfile.TemporaryDirectory() as root, ThreadPoolExecutor(2) as pool, patch.object(reports, '_submit', side_effect=lambda job, **kw: pool.submit(render, job)):
            builder = reports.ReportBuilder(root, 'Water', 'test')
            records = papers(250)
            builder.prepare(records)
            for p in records:
                p._relevance = 90
            try:
                _, manifest = builder.finish(records)
                self.assertEqual(len([j for j in received if j['kind']=='report']), 1)
                self.assertTrue(next(part for part in manifest if part['kind']=='report')['prepared_during_search'])
            finally:
                builder.close()

    def test_removed_records_are_excluded_from_prebuilt_parts(self):
        received = []
        def render(job):
            received.append(job)
            Path(job['path']).write_text('test PDF')
            return job['path']
        with tempfile.TemporaryDirectory() as root, ThreadPoolExecutor(2) as pool, patch.object(reports, '_submit', side_effect=lambda job, **kw: pool.submit(render, job)):
            builder = reports.ReportBuilder(root, 'Water', 'test', include_abstracts=True)
            records = papers(100)
            builder.prepare(records)
            try:
                _, manifest = builder.finish(records[1:])
                self.assertEqual(sum(part['records'] for part in manifest if part['kind']=='report'), 99)
                final_report = [job for job in received if job['kind']=='report'][-1]
                self.assertNotIn(records[0].doi, [row['doi'] for row in final_report['papers']])
            finally:
                builder.close()

    def test_failed_pdf_is_not_silently_excluded(self):
        def fail(job):
            raise OSError('Renderer failure')
        with tempfile.TemporaryDirectory() as root, ThreadPoolExecutor(2) as pool, patch.object(reports, '_submit', side_effect=lambda job, **kw: pool.submit(fail, job)):
            builder = reports.ReportBuilder(root, 'Water', 'test')
            try:
                with self.assertRaisesRegex(OSError, 'Renderer failure'):
                    builder.finish(papers(2))
                self.assertFalse(list(Path(root).glob('MANIFEST*')))
            finally:
                builder.close()

    def test_invalid_pdf_is_not_published(self):
        with tempfile.TemporaryDirectory() as root, patch.object(app, 'generate_documents', side_effect=lambda q, p, path, **kw: Path(path).write_bytes(b'%PDF-incomplete')):
            path = os.path.join(root, 'test.pdf')
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                reports._render({'kind':'report','query':'Water','papers':[], 'path':path,'options':{}})
            self.assertFalse(os.path.exists(path))
            self.assertFalse(os.path.exists(path+'.partial'))

    def test_partition_assigns_each_record_once_and_keeps_review_precedence(self):
        rows = [{'doc_type':'review', 'is_preprint':True}, {'doc_type':'book'}, {'doc_type':'research'}, {'is_preprint':True}]
        groups = app.partition_report_papers(rows)
        self.assertEqual([len(group) for group in groups], [1,1,1,1])
        self.assertIs(groups[0][0], rows[0])

    def test_comprehensive_pipeline_prepares_reports_before_collection_finishes(self):
        builders = []
        calls = []
        def factory(*args, **kwargs):
            builder = reports.ReportBuilder(*args, **kwargs)
            builders.append(builder)
            return builder
        def render(job):
            Path(job['path']).write_text('test PDF')
            return job['path']
        records = papers(201)
        def fetch(query, state, *args):
            calls.append(1)
            if len(calls) == 1:
                return records[:100]
            self.assertTrue(builders[0].prepared, 'A full PDF batch was dispatched before the second retrieval round')
            state['exhausted'] = True
            return records[100:]
        task_id = 'test-report-pipeline'
        with tempfile.TemporaryDirectory() as root, ThreadPoolExecutor(2) as pool, patch.dict(os.environ, {'REPORT_BATCH_SIZE':'25'}), patch.object(reports, '_submit', side_effect=lambda job, **kw: pool.submit(render, job)), patch.object(app, 'ReportBuilder', side_effect=factory), patch.object(app, 'DOWNLOAD_DIR', root), patch.object(app, 'FETCH_BATCH_MAP', {'crossref':fetch}), patch.object(app, 'db_set_task'):
            try:
                app.process_pipeline('water', db_source='crossref', limit=999999, uh='test-owner', task_id=task_id, include_abstracts=False)
                task = app.TASKS[task_id]
                self.assertEqual(task['status'], 'completed')
                self.assertEqual(len(task['papers']), 201)
                self.assertEqual(sum(p['records'] for p in task['report_parts'] if p['kind']=='report'), 201)
                self.assertTrue(Path(task['save_path']).is_file())
                import zipfile
                with zipfile.ZipFile(task['save_path']) as archive:
                    self.assertIsNone(archive.testzip())
                    self.assertTrue(any(name.startswith('INDEX_COMPLETE_') for name in archive.namelist()))
            finally:
                app.TASKS.pop(task_id, None)


if __name__ == '__main__':
    unittest.main()
