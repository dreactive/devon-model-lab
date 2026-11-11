"""Six models must share the frozen cohort; capture must never reach HTTP."""
import asyncio
from pathlib import Path
import tempfile
import unittest
import copy
from unittest.mock import patch

LAB = Path(__file__).resolve().parents[1]


class SelectionCheckTests(unittest.TestCase):
    def test_stale_http_count_metadata_is_not_certified(self):
        import selection_check
        original=selection_check.read_json
        def stale(path):
            value=original(path)
            if path.name=='dev-30pct-v1.json' and path.parent.name=='experiments':
                value=copy.deepcopy(value)
                value['http_counts']['six_models_cap']=1
            return value
        with tempfile.TemporaryDirectory(dir=LAB/'runs') as directory:
            with patch.object(selection_check,'read_json',side_effect=stale):
                with self.assertRaisesRegex(ValueError,'experiment_count_mismatch'):
                    asyncio.run(selection_check.run(Path('C:/Users/dreac/Desktop/kdt/devon'),Path(directory)/'bad.json'))

    def test_all_six_models_capture_same_sixteen_cases_without_http(self):
        import selection_check
        with tempfile.TemporaryDirectory(dir=LAB/'runs') as directory:
            with patch('httpx.AsyncHTTPTransport.handle_async_request',side_effect=AssertionError('real HTTP prohibited')):
                report=asyncio.run(selection_check.run(
                    Path('C:/Users/dreac/Desktop/kdt/devon'),Path(directory)/'selection.json'))
            self.assertEqual(report['selected_inputs'],16)
            self.assertEqual(report['model_count'],6)
            self.assertEqual(report['api_calls'],0)
            self.assertEqual(report['gold_pairs'],98)
            self.assertEqual(report['A_controls'],33)
            self.assertEqual(report['review_status'],'unreviewed')
            self.assertEqual(report['http_counts']['six_models_cap'],192)
            cohorts=[row['case_versions'] for row in report['models']]
            self.assertTrue(all(cohort==cohorts[0] for cohort in cohorts))
            self.assertEqual(len(cohorts[0]),16)
            self.assertTrue(all(plan['plan']['blocked_reasons'] for plan in report['plans']))
