import base64
import unittest
from unittest.mock import patch
import supervisor
from privacy import check_public_text

class PrivacyTest(unittest.TestCase):
    def test_raw_gsc_and_private_identifiers_cannot_reach_http(self):
        for raw in ('{"rows":[{"keys":["private-search"],"impressions":1}]}',
                    '{"session_id":"private-session"}', '{"email":"private@example.test"}'):
            with patch('supervisor.urllib.request.urlopen') as http:
                with self.assertRaises(ValueError):
                    supervisor.api('PUT', '/repos/' + supervisor.REPO + '/contents/state/checkpoint.json',
                        {'content': base64.b64encode(raw.encode()).decode()})
                http.assert_not_called()
    def test_control_evidence_and_aggregate_metrics_allowed(self):
        check_public_text('{"run":"123","position":24,"impressions":2}')

if __name__ == '__main__': unittest.main()
