"""Elice base-path preflight; only fake local .env files are used."""
from pathlib import Path
import tempfile
import unittest

import run_lab

LAB=Path(__file__).resolve().parents[1]


class EliceEndpointConfigTests(unittest.TestCase):
    def environment(self, endpoint, *, override=None):
        temporary=tempfile.TemporaryDirectory(dir=LAB/'tests')
        root=Path(temporary.name).resolve()
        assert root.is_relative_to((LAB/'tests').resolve())
        self.addCleanup(temporary.cleanup)
        path=root/'.env'
        text=f'OPENAI_API_KEY=FAKE_ENDPOINT_KEY\nLLM_BASE_URL={endpoint}\n'
        if override is not None:
            text+=f'MODEL_GPT_6_1_SOL_BASE_URL={override}\n'
        path.write_text(text,encoding='utf-8')
        return root,path

    def test_elice_requires_v1_base_before_any_transport(self):
        for endpoint in ('https://mlapi.run','https://demo.mlapi.run',
                         'https://demo.mlapi.run/api','https://demo.mlapi.run/v1/responses',
                         'https://demo.mlapi.run/v1/chat/completions'):
            with self.subTest(endpoint=endpoint):
                root,path=self.environment(endpoint)
                with self.assertRaisesRegex(ValueError,'^elice_endpoint_invalid$'):
                    run_lab._credentials(path,root,model_id='gpt-6.1-sol')

    def test_valid_elice_v1_paths_are_normalized(self):
        for endpoint,expected in (
                ('https://mlapi.run/v1','https://mlapi.run/v1'),
                ('https://demo.mlapi.run/v1/','https://demo.mlapi.run/v1'),
                ('https://demo.mlapi.run/api/v1///','https://demo.mlapi.run/api/v1')):
            with self.subTest(endpoint=endpoint):
                root,path=self.environment(endpoint)
                self.assertEqual(run_lab._credentials(path,root,model_id='gpt-6.1-sol'),('FAKE_ENDPOINT_KEY',expected))

    def test_elice_query_fragment_and_http_are_rejected_without_echoing_values(self):
        for endpoint in ('https://demo.mlapi.run/v1?token=FAKE_QUERY_SECRET',
                         'https://demo.mlapi.run/v1#FAKE_FRAGMENT_SECRET',
                         'https://demo.mlapi.run/v1?', 'https://demo.mlapi.run/v1#',
                         'http://demo.mlapi.run/v1',
                         'https://FAKE_USER:FAKE_PASSWORD@demo.mlapi.run/v1'):
            with self.subTest(endpoint=endpoint):
                root,path=self.environment(endpoint)
                with self.assertRaises(ValueError) as caught:
                    run_lab._credentials(path,root,model_id='gpt-6.1-sol')
                self.assertEqual(str(caught.exception),'elice_endpoint_invalid')

    def test_model_override_is_validated_even_when_shared_endpoint_is_valid(self):
        root,path=self.environment('https://example.invalid/v1',override='https://demo.mlapi.run')
        with self.assertRaisesRegex(ValueError,'^elice_endpoint_invalid$'):
            run_lab._credentials(path,root,model_id='gpt-6.1-sol')

    def test_non_elice_fixture_is_unchanged(self):
        for endpoint in ('https://example.invalid/v1/','https://mlapi.run.example.invalid/custom'):
            with self.subTest(endpoint=endpoint):
                root,path=self.environment(endpoint)
                self.assertEqual(run_lab._credentials(path,root),('FAKE_ENDPOINT_KEY',endpoint.rstrip('/')))
