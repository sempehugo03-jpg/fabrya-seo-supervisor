import unittest
from pathlib import Path
import supervisor


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

if __name__ == '__main__':
    unittest.main()
