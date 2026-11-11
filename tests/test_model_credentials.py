"""Credential routing is tested only with fake values in temporary folders."""
from pathlib import Path
import tempfile
import unittest

import run_lab


class ModelCredentialsTests(unittest.TestCase):
    def setup_env(self, content):
        temporary=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(temporary.cleanup)
        root=Path(temporary.name)
        assert root.resolve().is_relative_to(Path(__file__).resolve().parent)
        path=root/'.env'
        path.write_text(content,encoding='utf-8')
        return root,path

    def test_shared_pair_is_used_for_each_model(self):
        root,path=self.setup_env('OPENAI_API_KEY=FAKE_SHARED\nLLM_BASE_URL=https://example.invalid/v1/\n')
        self.assertEqual(run_lab._credentials(path,root,model_id='gpt-6.1-sol'),('FAKE_SHARED','https://example.invalid/v1'))

    def test_model_specific_endpoint_uses_shared_key(self):
        root,path=self.setup_env('OPENAI_API_KEY=FAKE_SHARED\nLLM_BASE_URL=\nMODEL_GPT_6_1_SOL_BASE_URL=https://gpt.example.invalid/v1\n')
        self.assertEqual(run_lab._credentials(path,root,model_id='gpt-6.1-sol'),('FAKE_SHARED','https://gpt.example.invalid/v1'))

    def test_model_specific_pair_overrides_shared_and_other_models(self):
        root,path=self.setup_env('OPENAI_API_KEY=FAKE_SHARED\nLLM_BASE_URL=https://common.example.invalid/v1\nMODEL_GEMINI_4_ARGON_API_KEY=FAKE_ARGON\nMODEL_GEMINI_4_ARGON_BASE_URL=https://argon.example.invalid/v1\n')
        self.assertEqual(run_lab._credentials(path,root,model_id='gemini-4-argon'),('FAKE_ARGON','https://argon.example.invalid/v1'))
        self.assertEqual(run_lab._credentials(path,root,model_id='gpt-6-luna'),('FAKE_SHARED','https://common.example.invalid/v1'))

    def test_blank_overrides_do_not_erase_shared_pair(self):
        root,path=self.setup_env('OPENAI_API_KEY=FAKE_SHARED\nLLM_BASE_URL=https://common.example.invalid/v1\nMODEL_GPT_6_LUNA_API_KEY=\nMODEL_GPT_6_LUNA_BASE_URL=\n')
        self.assertEqual(run_lab._credentials(path,root,model_id='gpt-6-luna'),('FAKE_SHARED','https://common.example.invalid/v1'))

    def test_missing_resolved_endpoint_remains_blocked(self):
        root,path=self.setup_env('OPENAI_API_KEY=FAKE_SHARED\nLLM_BASE_URL=\n')
        with self.assertRaisesRegex(ValueError,'local_credentials_required'):
            run_lab._credentials(path,root,model_id='gpt-6-luna')

    def test_foreign_env_is_rejected(self):
        root,path=self.setup_env('OPENAI_API_KEY=FAKE_SHARED\nLLM_BASE_URL=https://common.example.invalid/v1\n')
        with self.assertRaisesRegex(ValueError,'local_env_required'):
            run_lab._credentials(path,root/'other',model_id='gpt-6-luna')
