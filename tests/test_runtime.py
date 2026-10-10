import copy
import os
import unittest
from unittest.mock import patch
import supervisor


class DurableRuntime(unittest.TestCase):
    def test_no_runtime_pass_from_push_or_unit_test(self):
        self.assertEqual(supervisor.empty_state()['SEO_RUNTIME_AUTONOMOUS'], 'FAIL')

    def test_scheduled_interruption_is_persisted_before_exit(self):
        state = supervisor.empty_state()
        state['scheduled_baseline'] = {'trigger': 'schedule', 'status': 'COMPLETED'}
        saved = []
        def save(value, sha, message):
            saved.append(copy.deepcopy(value))
            return 'checkpoint'
        env = {'GITHUB_REPOSITORY': supervisor.REPO, 'GITHUB_RUN_ID': '3',
               'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_EVENT_NAME': 'schedule', 'GITHUB_SHA': 'current'}
        with patch.dict(os.environ, env), patch.object(supervisor, 'load', return_value=(state, 'old')), \
             patch.object(supervisor, 'save', side_effect=save), \
             patch.object(supervisor.os, '_exit', side_effect=SystemExit(73)):
            with self.assertRaises(SystemExit):
                supervisor.main()
        self.assertEqual(saved[-1]['lease']['trigger'], 'schedule')
        self.assertEqual(saved[-1]['SEO_RUNTIME_AUTONOMOUS'], 'FAIL')
        self.assertIn('scheduled-runtime-verification-20261010', saved[-1]['probes'])

    def test_following_schedule_pass_requires_real_watchdog_recovery(self):
        state = supervisor.empty_state()
        state['scheduled_baseline'] = {'trigger': 'schedule', 'status': 'COMPLETED'}
        state['probes'] = {'scheduled-runtime-verification-20261010': {'owner': '3:1'}}
        state['events'] = [{'kind': 'RECOVERED', 'old_owner': '3:1',
                            'old_trigger': 'schedule', 'trigger': 'workflow_run'}]
        saved = []
        def save(value, sha, message):
            saved.append(copy.deepcopy(value))
            return 'checkpoint'
        env = {'GITHUB_REPOSITORY': supervisor.REPO, 'GITHUB_RUN_ID': '5',
               'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_EVENT_NAME': 'schedule',
               'GITHUB_SHA': 'current', 'CRASH_PROBE': 'false'}
        with patch.dict(os.environ, env), patch.object(supervisor, 'load', return_value=(state, 'old')), \
             patch.object(supervisor, 'save', side_effect=save), \
             patch.object(supervisor, 'executable_brief_paths', return_value=[]), \
             patch.object(supervisor, 'competitor_review', return_value={'status': 'NO_ACTION'}), \
             patch.object(supervisor, 'restore_normal_cadence') as restore:
            supervisor.main()
        self.assertEqual(saved[-1]['SEO_RUNTIME_AUTONOMOUS'], 'PASS')
        self.assertEqual(saved[-1]['runtime_verification']['following_schedule']['commit'], 'current')
        restore.assert_called_once()

    def test_schedule_checkpoints_no_action_and_current_commit(self):
        state = supervisor.empty_state()
        state['probes'] = {'scheduled-runtime-verification-20261010': {}}
        saved = []
        def save(value, sha, message):
            saved.append(copy.deepcopy(value))
            return 'checkpoint'
        env = {'GITHUB_REPOSITORY': supervisor.REPO, 'GITHUB_RUN_ID': '2',
               'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_EVENT_NAME': 'schedule',
               'GITHUB_SHA': 'current', 'CRASH_PROBE': 'false'}
        with patch.dict(os.environ, env), patch.object(supervisor, 'load', return_value=(state, 'old')), \
             patch.object(supervisor, 'save', side_effect=save), \
             patch.object(supervisor, 'executable_brief_paths', return_value=[]), \
             patch.object(supervisor, 'competitor_review', return_value={'status': 'NO_ACTION'}):
            supervisor.main()
        self.assertEqual(saved[-1]['runtime_cycle']['status'], 'COMPLETED')
        self.assertEqual(saved[-1]['runtime_cycle']['commit'], 'current')
        self.assertEqual(saved[-1]['runtime_cycle']['trigger'], 'schedule')
        self.assertIsNone(saved[-1]['lease'])

    def test_watchdog_recovers_terminal_scheduled_owner(self):
        state = supervisor.empty_state()
        state['lease'] = {'run': '1', 'owner': '1:1', 'task': 'runtime-verification',
                          'trigger': 'schedule'}
        saved = []
        def save(value, sha, message):
            saved.append(copy.deepcopy(value))
            return 'checkpoint'
        env = {'GITHUB_REPOSITORY': supervisor.REPO, 'GITHUB_RUN_ID': '2',
               'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_EVENT_NAME': 'workflow_run',
               'GITHUB_SHA': 'current', 'CRASH_PROBE': 'false'}
        with patch.dict(os.environ, env), patch.object(supervisor, 'load', return_value=(state, 'old')), \
             patch.object(supervisor, 'api', return_value={'status': 'completed', 'conclusion': 'failure'}), \
             patch.object(supervisor, 'save', side_effect=save), \
             patch.object(supervisor, 'executable_brief_paths', return_value=[]), \
             patch.object(supervisor, 'competitor_review', return_value={'status': 'NO_ACTION'}):
            supervisor.main()
        self.assertEqual(saved[0]['events'][0]['kind'], 'RECOVERED')
        self.assertEqual(saved[0]['events'][0]['old_trigger'], 'schedule')
        self.assertEqual(saved[0]['events'][0]['trigger'], 'workflow_run')

