import unittest
from pathlib import Path
import supervisor
import base64
import json
import urllib.error
from unittest.mock import patch


class SeoPreparation(unittest.TestCase):
    def test_real_briefs_are_structured_without_authorizing_publication(self):
        paths = list((Path(__file__).parents[1] / 'briefs').glob('*.md'))
        self.assertEqual(len(paths), 2)
        for path in paths:
            result = supervisor.audit(path)
            self.assertEqual(result['findings'], [], path.name)
            self.assertFalse(result['publication_authorized'])
            self.assertEqual(result['editorial_status'], 'NEEDS_HUMAN_REVIEW')

    def test_task_identity_follows_content(self):
        path = Path(__file__).parents[1] / 'briefs/site-photographe.md'
        self.assertEqual(supervisor.task_id(path), supervisor.task_id(path))
        self.assertIn('site-photographe', supervisor.task_id(path))

    def test_budget_and_blockers_are_explicit(self):
        state = supervisor.empty_state()
        self.assertEqual(state['budget_eur'], 0)
        self.assertIn('GSC_DEDICATED_READONLY_ACCESS', state['blocked'])
        self.assertEqual(state['status'], 'PARTIAL_DETERMINISTIC')

    def test_competitor_observation_ignores_scripts_and_is_not_a_feature_proof(self):
        parser = supervisor.VisibleText()
        parser.feed('<h1>Portfolio</h1><script>réservation garantie</script><p>Devis</p>')
        self.assertEqual(parser.h1, 1)
        self.assertNotIn('réservation garantie', ' '.join(parser.parts))
        self.assertIn('Devis', ' '.join(parser.parts))

    def test_public_fetch_rejects_product_and_unknown_hosts_before_network(self):
        for url in ('https://fabrya.fr/robots.txt', 'http://fr.wix.com/', 'https://evil.example/'):
            with self.assertRaises(RuntimeError):
                supervisor.public_read(url)

    def test_committed_checkpoint_then_500_is_confirmed_without_second_write(self):
        state = supervisor.empty_state()
        committed = dict(content=base64.b64encode(json.dumps(state).encode()).decode(), sha='new')
        error = urllib.error.HTTPError('https://api.github.com/test', 500, 'server', {}, None)
        with patch.object(supervisor, 'api', side_effect=[error, committed]) as call:
            self.assertEqual(supervisor.save(state, 'old', 'test'), 'new')
            self.assertEqual([c.args[0] for c in call.call_args_list], ['PUT', 'GET'])

    def test_transient_uncommitted_write_retries_with_original_fence(self):
        state = supervisor.empty_state()
        old = dict(content=base64.b64encode(b'{}').decode(), sha='old')
        error = urllib.error.HTTPError('https://api.github.com/test', 503, 'server', {}, None)
        with patch.object(supervisor, 'api', side_effect=[error, old, dict(content=dict(sha='new'))]) as call:
            with patch.object(supervisor.time, 'sleep'):
                self.assertEqual(supervisor.save(state, 'old', 'test'), 'new')
            puts = [c.args[2] for c in call.call_args_list if c.args[0] == 'PUT']
            self.assertEqual([p['sha'] for p in puts], ['old', 'old'])

    def test_concurrent_change_after_500_fails_closed_without_overwrite(self):
        error = urllib.error.HTTPError('https://api.github.com/test', 500, 'server', {}, None)
        other = dict(content=base64.b64encode(b'{"different_owner":true}').decode(), sha='other')
        with patch.object(supervisor, 'api', side_effect=[error, other]) as call:
            with self.assertRaisesRegex(RuntimeError, 'concurrently'):
                supervisor.save(supervisor.empty_state(), 'old', 'test')
            self.assertEqual([c.args[0] for c in call.call_args_list], ['PUT', 'GET'])

    def test_oversized_competitor_retained_without_losing_other_observations(self):
        observations = [RuntimeError('Public document too large'),
            dict(url=supervisor.COMPETITORS[1], status='READ', claims_verified=False),
            dict(url=supervisor.COMPETITORS[2], status='ROBOTS_DISALLOWED')]
        with patch.object(supervisor, 'review_competitor', side_effect=observations):
            result = supervisor.competitor_review()
            self.assertEqual(result['operational_status'], 'WITH_BLOCKERS')
            self.assertEqual(result['observed_pages'], 1)
            self.assertEqual(result['results'][0]['error'], 'Public document too large')
            self.assertFalse(result['publication_authorized'])

if __name__ == '__main__':
    unittest.main()
