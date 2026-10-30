"""Owner-authorized stop decisions and non-refundable user cancellation."""
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from starlette.responses import Response
from access_control import issue_session
from models import CanonicalPaper
import app


class StopDecisionTests(unittest.TestCase):
    def run_decision(self, action):
        task_id = 'test-stop-' + action
        owner = 'test-owner-abcdef'
        cookie = Response()
        issue_session(cookie, owner, secure=True)
        headers = {'Cookie': cookie.headers['set-cookie'].split(';', 1)[0]}
        second_started, release_provider, paused = threading.Event(), threading.Event(), threading.Event()
        records = [CanonicalPaper(title=f'Water measurement {i}', doi=f'10.1000/water{i}', authors=['Test Author'], year='2025', sources=['crossref']) for i in range(3)]
        calls = []
        def fetch(query, state, *args):
            calls.append(1)
            if len(calls) == 1:
                return records
            second_started.set()
            release_provider.wait(3)
            state['exhausted'] = True
            return []
        original_set_task = app._set_task
        def set_task(tid, **kwargs):
            original_set_task(tid, **kwargs)
            if kwargs.get('status') == 'awaiting_stop_decision':
                paused.set()
        with tempfile.TemporaryDirectory() as root, patch.object(app, 'DOWNLOAD_DIR', root), patch.object(app, 'FETCH_BATCH_MAP', {'crossref':fetch}), patch.object(app, 'is_local_instance', return_value=False), patch.object(app, 'db_set_task'), patch.object(app, '_set_task', side_effect=set_task), patch.object(app, 'refund_guest_search_quota') as refund, patch.object(app, 'generate_documents', side_effect=lambda q,p,path,*a,**kw: Path(path).write_bytes(b'%PDF-test')) as render, TestClient(app.app, base_url='https://testserver') as client:
            app._set_task(task_id, status='processing', user_hash=owner, quota_charged_units=30)
            worker = threading.Thread(target=app.process_pipeline, kwargs=dict(query='water', db_source='crossref', limit=30, uh=owner, task_id=task_id, is_guest=True, guest_ip='ip', guest_fp='fp'))
            worker.start()
            try:
                self.assertTrue(second_started.wait(2))
                self.assertEqual(client.post(f'/api/cancel/{task_id}', data={'action':'pause'}).status_code, 403)
                response = client.post(f'/api/cancel/{task_id}', data={'action':'pause'}, headers=headers)
                self.assertEqual(response.status_code, 200)
                release_provider.set()
                self.assertTrue(paused.wait(2))
                snapshot = client.get(f'/api/status/{task_id}', headers=headers).json()
                self.assertEqual(snapshot['status'], 'awaiting_stop_decision')
                self.assertEqual(snapshot['collected_count'], 3)
                self.assertEqual(snapshot['quota_charged_units'], 30)
                self.assertFalse(render.called, 'No PDF is generated before the owner chooses')
                self.assertFalse(refund.called)
                response = client.post(f'/api/cancel/{task_id}', data={'action':action}, headers=headers)
                self.assertEqual(response.status_code, 200)
                worker.join(3)
                self.assertFalse(worker.is_alive())
                task = app.TASKS[task_id]
                self.assertFalse(refund.called, 'Owner-requested cancellation must not refund the reservation')
                if action == 'preserve':
                    self.assertEqual(task['status'], 'completed', task.get('error'))
                    self.assertEqual(len(task['papers']), 3)
                    self.assertTrue(Path(task['save_path']).is_file())
                else:
                    self.assertEqual(task['status'], 'cancelled')
                    self.assertEqual(task['papers'], [])
                    self.assertFalse(render.called)
                    self.assertFalse(list(Path(root).rglob('*.pdf')))
            finally:
                release_provider.set()
                event = app.STOP_EVENTS.get(task_id)
                if event:
                    app.TASKS[task_id]['stop_action'] = 'discard'
                    event.set()
                worker.join(3)
                app.TASKS.pop(task_id, None)
                app.CANCELLED_TASKS.discard(task_id)
                app.STOP_EVENTS.pop(task_id, None)

    def test_preserve_pauses_then_generates_pdfs_without_refunding_quota(self):
        self.run_decision('preserve')

    def test_discard_pauses_then_deletes_results_without_refunding_quota(self):
        self.run_decision('discard')

    def test_invalid_action_is_rejected(self):
        with TestClient(app.app) as client:
            self.assertEqual(client.post('/api/cancel/invalid', data={'action':'other'}).status_code, 400)

    def test_user_cancellation_while_queued_retains_charged_quota(self):
        task_id = 'test-stop-queued'
        app.TASKS[task_id] = {'status':'queued', 'stop_requested':True, 'stop_action':'discard', 'quota_charged_units':10}
        app.CANCELLED_TASKS.add(task_id)
        with patch.object(app, 'db_set_task'), patch.object(app, 'refund_guest_search_quota') as refund, patch.object(app, 'GUEST_QUEUE', []), patch.object(app, 'ACTIVE_GUESTS', set()):
            try:
                app.managed_pipeline_wrapper('water', 'keyword', 'all', 10, '', 'test-owner', task_id, False, None, None, False, True, guest_ip='ip', guest_fp='fp')
                self.assertEqual(app.TASKS[task_id]['status'], 'cancelled')
                self.assertFalse(refund.called)
            finally:
                app.TASKS.pop(task_id, None)
                app.CANCELLED_TASKS.discard(task_id)

    def test_collection_slot_is_released_once_before_reporting_or_waiting(self):
        def pipeline(*args, **kwargs):
            self.assertEqual(app.PREMIUM_USERS_COUNT, 1)
            kwargs['on_collection_stopped']()
            kwargs['on_collection_stopped']()
            self.assertEqual(app.PREMIUM_USERS_COUNT, 0)
            self.assertTrue(app.GUESTS_CAN_RUN.is_set())
        with patch.object(app, 'PREMIUM_USERS_COUNT', 0), patch.object(app, 'process_pipeline', side_effect=pipeline):
            app.managed_pipeline_wrapper('water', 'keyword', 'all', 10, '', 'test-owner', 'slot-test', False, None, None, False, False)
            self.assertEqual(app.PREMIUM_USERS_COUNT, 0)


if __name__ == '__main__':
    unittest.main()
