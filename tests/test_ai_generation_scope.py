import unittest
import sys
import types
from unittest.mock import patch

# The scope tests never perform HTTP; keep them runnable in the minimal CI runtime.
sys.modules.setdefault('requests', types.ModuleType('requests'))

from src.ai_generator import AIGenerator
from src.core.database_model import Paper


class AIGenerationScopeTests(unittest.TestCase):
    def setUp(self):
        self.generator = AIGenerator()

    def test_batch_analogy_scope_generates_only_missing_analogy(self):
        paper = Paper(title='Scoped Paper')

        with (
            patch.object(self.generator, 'is_available', return_value=True),
            patch.object(
                self.generator,
                'generate_field',
                return_value='[AI generated] analogy',
            ) as generate_field,
            patch('src.ai_generator.time.sleep'),
        ):
            papers, changed = self.generator.batch_enhance_papers(
                [paper], fields_to_gen=['analogy_summary']
            )

        self.assertTrue(changed)
        self.assertEqual(papers[0].analogy_summary, '[AI generated] analogy')
        self.assertEqual(papers[0].summary_motivation, '')
        self.assertEqual(papers[0].summary_innovation, '')
        self.assertEqual(papers[0].summary_method, '')
        self.assertEqual(papers[0].summary_conclusion, '')
        self.assertEqual(papers[0].summary_limitation, '')
        self.assertEqual(generate_field.call_count, 1)
        self.assertEqual(generate_field.call_args.args[1], 'analogy_summary')

    def test_batch_scope_does_not_overwrite_existing_analogy(self):
        paper = Paper(title='Human Entry', analogy_summary='human text')

        with (
            patch.object(self.generator, 'is_available', return_value=True),
            patch.object(self.generator, 'generate_field') as generate_field,
            patch('src.ai_generator.time.sleep'),
        ):
            papers, changed = self.generator.batch_enhance_papers(
                [paper], fields_to_gen=['analogy_summary']
            )

        self.assertFalse(changed)
        self.assertEqual(papers[0].analogy_summary, 'human text')
        generate_field.assert_not_called()


if __name__ == '__main__':
    unittest.main()
