import copy
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from external_scheduler import AUTOMATION_ID, PROBE_ID, wake_metadata
from runtime_status import reconcile


class ExternalScheduler(unittest.TestCase):
    def test_source_push_and_stale_wake_fail_closed(self):
        with patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'push', 'GITHUB_REF': 'refs/heads/main'}):
            with self.assertRaises(RuntimeError):
                wake_metadata()
        with tempfile.NamedTemporaryFile(mode='w') as f:
            json.dump({'schema': 1, 'automation_id': AUTOMATION_ID, 'slot': 1,
                       'issued_at': 3600, 'source_commit': 'a' * 40}, f); f.flush()
            with patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'push', 'GITHUB_REF': 'refs/heads/seo-wake',
                     'SEO_WAKE_FILE': f.name, 'SEO_SOURCE_COMMIT': 'a' * 40}):
                with self.assertRaises(RuntimeError):
                    wake_metadata()

    def fixture(self):
        state = {'external_scheduler_config': {'automation_id': AUTOMATION_ID},
                 'probes': {PROBE_ID: {'owner': '2:1', 'wake': {'source_commit': 'current'}}},
                 'events': [{'kind': 'RECOVERED', 'old_owner': '2:1', 'old_trigger': 'push',
                    'trigger': 'workflow_run', 'previous_conclusion': 'failure', 'by': '3:1'}],
                 'cycle_receipts': [], 'external_scheduler_attestations': {}}
        runs, jobs = [], {}
        for i, branch, event, stamp in [(1, 'seo-wake', 'push', '2026-10-11T01:00:00+00:00'),
                                       (3, 'main', 'workflow_run', '2026-10-11T02:10:00+00:00'),
                                       (4, 'seo-wake', 'push', '2026-10-11T03:00:00+00:00')]:
            from datetime import datetime
            issued = datetime.fromisoformat(stamp).timestamp(); slot = int(issued // 3600)
            wake = {'slot': slot, 'issued_at': issued, 'automation_id': AUTOMATION_ID}
            state['cycle_receipts'].append({'run': str(i), 'commit': 'current',
                                           'status': 'COMPLETED', 'wake': wake})
            runs.append({'id': i, 'head_branch': branch, 'event': event, 'status': 'completed',
                         'conclusion': 'success', 'run_attempt': 1, 'head_sha': 'current' if i == 3 else str(i),
                         'created_at': stamp, 'updated_at': stamp})
            names = ['Verify recovery executor', 'Recover same SEO state and unfinished useful task'] if i == 3 else [
                'Validate isolated executor', 'Prepare useful SEO reviews and recover checkpoints']
            jobs[str(i)] = [{'conclusion': 'success', 'steps': [{'name': n, 'conclusion': 'success'} for n in names]}]
            if i != 3:
                state['external_scheduler_attestations'][str(slot)] = {
                    'automation_id': AUTOMATION_ID, 'run': str(i), 'wake_commit': str(i),
                    'delivery': 'HOSTED_SCHEDULED_TASK', 'observed_last_run_time': stamp,
                    'completed_tasks_unchanged': True}
        return state, runs, jobs

    def test_requires_audited_repeated_wake_and_real_recovery(self):
        state, runs, jobs = self.fixture()
        result = reconcile(state, 'current', runs, jobs)
        self.assertEqual(result['gates']['SEO_RUNTIME_AUTONOMOUS']['status'], 'PASS')
        self.assertEqual(result['gates']['WATCHDOG_RECOVERY']['status'], 'PASS')
        self.assertEqual(result['terminal_state'], 'RUNNING')
        for key in ['events', 'external_scheduler_attestations']:
            s = copy.deepcopy(state); s[key] = {} if key.endswith('attestations') else []
            self.assertEqual(reconcile(s, 'current', runs, jobs)['gates']['SEO_RUNTIME_AUTONOMOUS']['status'], 'FAIL')
        self.assertEqual(reconcile(state, 'current', runs[:-1], jobs)['gates']['SEO_RUNTIME_AUTONOMOUS']['status'], 'FAIL')

    def test_hosted_task_completion_time_after_wake_is_valid(self):
        from datetime import datetime, timezone
        state, runs, jobs = self.fixture()
        receipts = {str(item['wake']['slot']): item for item in state['cycle_receipts']
                    if item.get('wake')}
        for slot, audit in state['external_scheduler_attestations'].items():
            issued = receipts[slot]['wake']['issued_at']
            audit['observed_last_run_time'] = datetime.fromtimestamp(
                issued + 45, tz=timezone.utc).isoformat()
        result = reconcile(state, 'current', runs, jobs)
        self.assertEqual(result['gates']['SEO_RUNTIME_AUTONOMOUS']['status'], 'PASS')
        self.assertEqual(result['gates']['WATCHDOG_RECOVERY']['status'], 'PASS')

    def test_verified_recovery_survives_scheduler_only_source_fix(self):
        state, runs, jobs = self.fixture()
        state['probes'][PROBE_ID]['wake'] = {'source_commit': 'old'}
        for receipt in state['cycle_receipts']:
            receipt['commit'] = 'old' if receipt['run'] == '3' else 'new'
        for run in runs:
            if run['id'] == 3:
                run['head_sha'] = 'old'
        result = reconcile(state, 'new', runs, jobs)
        self.assertEqual(result['gates']['SEO_RUNTIME_AUTONOMOUS']['status'], 'PASS')
        self.assertEqual(result['gates']['WATCHDOG_RECOVERY']['status'], 'PASS')
        self.assertEqual(result['gates']['WATCHDOG_RECOVERY']['evidence']['commit'], 'old')

    def test_manual_marker_wrong_delivery_and_failed_qa_never_pass(self):
        state, runs, jobs = self.fixture()
        for a in state['external_scheduler_attestations'].values():
            a['observed_last_run_time'] = '2026-10-10T00:00:00+00:00'
        self.assertEqual(reconcile(state, 'current', runs, jobs)['gates']['SEO_RUNTIME_AUTONOMOUS']['status'], 'FAIL')
        state, runs, jobs = self.fixture(); jobs['4'][0]['steps'][0]['conclusion'] = 'failure'
        self.assertEqual(reconcile(state, 'current', runs, jobs)['gates']['SEO_RUNTIME_AUTONOMOUS']['status'], 'FAIL')
