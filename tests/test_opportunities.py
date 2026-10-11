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

if __name__ == '__main__': unittest.main()
