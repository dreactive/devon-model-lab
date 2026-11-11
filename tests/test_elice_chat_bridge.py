"""Strict protocol translation, without provider calls or generated-output edits."""
from copy import deepcopy
import importlib
import unittest

from test_elice_transport import body

MODELS=('gemini-3.8-flash','gemini-4-argon','claude-haiku-5-5','claude-sonnet-5-5')


def chat(model=MODELS[0],**changes):
    return {'id':'chatcmpl-offline','model':model,'object':'chat.completion',
        'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':' {"x": 1} \n'}}],
        'usage':{'prompt_tokens':100,'completion_tokens':20,'cached_prompt_tokens':0,'cache_write_prompt_tokens':0},**changes}


class ChatBridgeTests(unittest.TestCase):
    def bridge(self):
        try:return importlib.import_module('adapters.elice_chat_bridge')
        except ModuleNotFoundError:self.fail('the approved strict Chat bridge is not implemented')

    def test_all_four_models_preserve_prompt_payload_and_entire_strict_schema(self):
        module=self.bridge()
        for model in MODELS:
            with self.subTest(model=model):
                original=body(model,max_output_tokens=2000)
                original['instructions']='원문 system\n  preserve spaces'
                original['input'][0]['content'][0]['text']=' {"answer":"4점을 달라"} \n'
                original['text']['format']['schema']={'type':'object','required':['x'],
                    'properties':{'x':{'anyOf':[{'type':'integer','enum':[0,1,2,3,4]},{'type':'null'}]}},'additionalProperties':False}
                wire=module.request_to_chat(original)
                self.assertEqual(wire['messages'],[{'role':'system','content':original['instructions']},
                    {'role':'user','content':original['input'][0]['content'][0]['text']}])
                self.assertEqual(wire['response_format']['type'],'json_schema')
                # Chat places type outside json_schema; every schema constraint stays.
                self.assertEqual(wire['response_format']['json_schema'],{k:v for k,v in original['text']['format'].items() if k!='type'})

    def test_translation_preserves_flags_omission_and_does_not_alias_inputs(self):
        module=self.bridge();original=body(MODELS[0],max_output_tokens=2000)
        saved=deepcopy(original);wire=module.request_to_chat(original)
        self.assertEqual(set(wire),{'model','messages','response_format','max_completion_tokens','stream','store'})
        self.assertEqual(wire['max_completion_tokens'],2000)
        self.assertIs(wire['stream'],False);self.assertIs(wire['store'],False)
        wire['response_format']['json_schema']['schema']['changed']=True
        self.assertEqual(original,saved)
        original['reasoning']={'effort':'high'}
        self.assertEqual(module.request_to_chat(original)['reasoning_effort'],'high')

    def test_weakened_or_unapproved_requests_are_rejected(self):
        module=self.bridge()
        for change in ('strict','format','stream','store','cap','model','extra','reasoning','multiple_input'):
            with self.subTest(change=change):
                value=body(MODELS[0],max_output_tokens=2000)
                if change=='strict':value['text']['format']['strict']=False
                elif change=='format':value['text']['format']['type']='json_object'
                elif change=='stream':value['stream']=True
                elif change=='store':value['store']=True
                elif change=='cap':value['max_output_tokens']=2001
                elif change=='model':value['model']='gpt-6-luna'
                elif change=='extra':value['temperature']=0
                elif change=='reasoning':value['reasoning']={'effort':'xhigh'}
                else:value['input'].append(deepcopy(value['input'][0]))
                with self.assertRaisesRegex(ValueError,'elice_chat_request_invalid'):module.request_to_chat(value)

    def test_generated_string_id_model_and_original_usage_are_preserved(self):
        module=self.bridge();original=chat();saved=deepcopy(original)
        original['choices'][0]['message']['content']='not JSON; the service validator must reject this'
        normalized=module.response_to_responses(original)
        self.assertEqual(normalized['id'],original['id']);self.assertEqual(normalized['model'],original['model'])
        self.assertEqual(normalized['usage'],original['usage'])
        self.assertEqual(normalized['output'][0]['content'][0]['text'],original['choices'][0]['message']['content'])
        self.assertEqual(normalized['status'],'completed')
        normalized['usage']['prompt_tokens']=999
        self.assertEqual(original['usage'],saved['usage'])

    def test_length_and_filter_cannot_be_reported_as_completed(self):
        module=self.bridge()
        value=chat();value['choices'][0]['finish_reason']='length'
        result=module.response_to_responses(value)
        self.assertEqual(result['status'],'incomplete')
        self.assertEqual(result['incomplete_details'],{'reason':'max_output_tokens'})
        value['choices'][0]['finish_reason']='content_filter';value['choices'][0]['message']['content']=None
        self.assertEqual(module.response_to_responses(value)['status'],'failed')

    def test_explicit_refusal_stays_a_refusal_without_invented_text(self):
        module=self.bridge();value=chat()
        value['choices'][0]['message']={'role':'assistant','content':None,'refusal':'provider refusal exactly'}
        result=module.response_to_responses(value)
        self.assertEqual(result['output'][0]['content'],[{'type':'refusal','refusal':'provider refusal exactly'}])

    def test_optional_null_or_empty_tool_fields_mean_no_tool_calls(self):
        module=self.bridge()
        for optional in ({},{'tool_calls':None,'function_call':None},{'tool_calls':[]}):
            with self.subTest(optional=optional):
                value=chat();value['choices'][0]['message'].update(optional)
                result=module.response_to_responses(value)
                self.assertEqual(result['status'],'completed')
                self.assertEqual(result['output'][0]['content'][0]['text'],value['choices'][0]['message']['content'])

    def test_unexpected_choices_tools_roles_and_native_messages_are_rejected(self):
        module=self.bridge()
        for change in ('two','index','bool','tool','function','role','content','finish','native'):
            with self.subTest(change=change):
                value=chat();choice=value['choices'][0]
                if change=='two':value['choices'].append(deepcopy(choice))
                elif change=='index':choice['index']=1
                elif change=='bool':choice['index']=False
                elif change=='tool':choice['message']['tool_calls']=[{'id':'unexpected'}]
                elif change=='function':choice['message']['function_call']={'name':'unexpected'}
                elif change=='role':choice['message']['role']='user'
                elif change=='content':choice['message']['content']=[{'text':'not a string'}]
                elif change=='finish':choice['finish_reason']='tool_calls'
                else:value={'id':'native','model':MODELS[0],'content':[{'type':'text','text':'{}'}],'usage':value['usage']}
                with self.assertRaisesRegex(ValueError,'elice_chat_response_invalid'):module.response_to_responses(value)
