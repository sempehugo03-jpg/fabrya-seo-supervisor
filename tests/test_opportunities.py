import copy
import json
import unittest
from pathlib import Path
from opportunities import consume, decide, validate, capability_gates

class OpportunitiesTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((Path(__file__).parents[1] / 'inputs/gsc-latest.json').read_text())
    def test_real_input_is_bounded_and_not_sector_fixed(self):
        result = decide(self.data)
        self.assertLessEqual(len(result), 3)
        self.assertTrue(result)
        self.assertTrue(all(not x['publication_authorized'] for x in result))
        alternative = copy.deepcopy(self.data)
        for row in alternative['pages']:
            row['url'] = row['url'].replace('site-photographe', 'solution-nouvelle')
        self.assertTrue(any(x['url'].endswith('solution-nouvelle') for x in decide(alternative)))
    def test_private_fields_and_tracking_urls_rejected(self):
        for key in ('query', 'session_id', 'email', 'token'):
            candidate = copy.deepcopy(self.data)
            candidate['pages'][0][key] = 'must-never-be-public'
            with self.assertRaises(ValueError): validate(candidate)
        candidate = copy.deepcopy(self.data)
        candidate['pages'][0]['url'] = 'https://fabrya.fr/?session_id=secret'
        with self.assertRaises(ValueError): validate(candidate)
    def test_page_rank_cannot_be_substituted_for_query_rank(self):
        photo = next(x for x in decide(self.data) if x['url'].endswith('site-photographe'))
        self.assertEqual(photo['visible_nonbrand_position'], 24)
        self.assertFalse(any('snippet' in h for h in photo['hypotheses']))
    def test_manual_read_never_proves_autonomy(self):
        state = {}
        consume(state, self.data, 'installation', 'push')
        consume(state, self.data, 'second', 'schedule')
        self.assertEqual(len(state['gsc_observations']), 1)
        self.assertEqual(capability_gates(state)['GSC_DIRECT_READ']['status'], 'FAIL')

    def test_incomplete_observation_fails_closed_without_crashing(self):
        state = {'external_scheduler_attestations': {
            '497831': {'delivery': 'HOSTED_SCHEDULED_TASK', 'run': 'consumer-run'}
        }, 'gsc_observations': [{
            'acquisition': 'HOSTED_SCHEDULED_TASK',
            'automation_slot': 497831,
            'snapshot_commit': 'error-receipt'
        }], 'seo_decision': {
            'run': 'consumer-run',
            'source_snapshot': 'previous-snapshot',
            'decision': 'NO_ACTION'
        }}
        self.assertEqual(capability_gates(state)['GSC_DIRECT_READ']['status'], 'FAIL')

    def test_consume_tolerates_incomplete_observation_history(self):
        state = {'gsc_observations': [{
            'acquisition': 'HOSTED_SCHEDULED_TASK',
            'automation_slot': 497910,
            'read_at': '2026-10-20T06:00:00Z'
        }]}
        decision = consume(state, self.data, 'consumer-run', 'push')
        self.assertEqual(decision['source_snapshot'], self.data['private_snapshot_commit'])
        self.assertEqual(len(state['gsc_observations']), 2)
        self.assertEqual(state['gsc_observations'][-1]['consumed_by_run'], 'consumer-run')

    def test_attestation_must_match_the_run_that_consumed_snapshot(self):
        data = copy.deepcopy(self.data)
        data['acquisition'] = 'HOSTED_SCHEDULED_TASK'
        data['automation_slot'] = 497703
        state = {'external_scheduler_attestations': {
            '497703': {'delivery': 'HOSTED_SCHEDULED_TASK', 'run': 'earlier-run'}
        }}
        consume(state, data, 'consumer-run', 'push')
        self.assertEqual(capability_gates(state)['GSC_DIRECT_READ']['status'], 'FAIL')
        state['external_scheduler_attestations']['497703']['run'] = 'consumer-run'
        self.assertEqual(capability_gates(state)['GSC_DIRECT_READ']['status'], 'PASS')

if __name__ == '__main__': unittest.main()
