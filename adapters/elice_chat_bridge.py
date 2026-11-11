"""Pure strict-schema bridge for the four documented Elice Chat models.

Only the protocol envelope changes. Prompts, user text, the complete schema,
generated output strings and provider usage are never rewritten or repaired.
"""
from __future__ import annotations

from copy import deepcopy

CHAT_MODELS=frozenset({'gemini-3.8-flash','gemini-4-argon','claude-haiku-5-5','claude-sonnet-5-5'})


def request_to_chat(canonical: dict) -> dict:
    """Translate the exact service request; never weaken unsupported settings."""
    try:
        required={'model','instructions','input','text','max_output_tokens','store'}
        if (type(canonical) is not dict or not required<=set(canonical)
                or set(canonical)-required-{'stream','reasoning'}
                or canonical['model'] not in CHAT_MODELS
                or type(canonical['instructions']) is not str or canonical['store'] is not False
                or canonical.get('stream',False) is not False
                or type(canonical['max_output_tokens']) is not int
                or not 1<=canonical['max_output_tokens']<=2000):
            raise ValueError
        inputs=canonical['input']
        if (type(inputs) is not list or len(inputs)!=1 or type(inputs[0]) is not dict
                or set(inputs[0])!={'role','content'} or inputs[0]['role']!='user'
                or type(inputs[0]['content']) is not list or len(inputs[0]['content'])!=1):
            raise ValueError
        content=inputs[0]['content'][0]
        if (type(content) is not dict or set(content)!={'type','text'}
                or content['type']!='input_text' or type(content['text']) is not str):
            raise ValueError
        text=canonical['text']
        if type(text) is not dict or set(text)!={'format'}:
            raise ValueError
        schema_format=text['format']
        if (type(schema_format) is not dict or set(schema_format)!={'type','name','schema','strict'}
                or schema_format['type']!='json_schema' or schema_format['strict'] is not True
                or type(schema_format['name']) is not str or not schema_format['name']
                or type(schema_format['schema']) is not dict):
            raise ValueError
        result={'model':canonical['model'],'messages':[
            {'role':'system','content':canonical['instructions']},
            {'role':'user','content':content['text']}],
            'response_format':{'type':'json_schema','json_schema':{
                name:deepcopy(schema_format[name]) for name in ('name','schema','strict')}},
            'max_completion_tokens':canonical['max_output_tokens'],'stream':False,'store':False}
        if 'reasoning' in canonical:
            reasoning=canonical['reasoning']
            allowed={'none','low','medium','high'}
            if canonical['model'].startswith('claude-'):
                allowed|={'xhigh','max'}
            if (type(reasoning) is not dict or set(reasoning)!={'effort'}
                    or reasoning['effort'] not in allowed):
                raise ValueError
            result['reasoning_effort']=reasoning['effort']
        return result
    except (KeyError,ValueError,TypeError,AttributeError):
        raise ValueError('elice_chat_request_invalid') from None


def response_to_responses(provider: dict) -> dict:
    """Adapt one textual assistant choice while preserving terminal failures."""
    try:
        if (type(provider) is not dict or type(provider.get('id')) is not str or not provider['id'].strip()
                or type(provider.get('model')) is not str or not provider['model'].strip()
                or type(provider.get('usage')) is not dict
                or type(provider.get('choices')) is not list or len(provider['choices'])!=1):
            raise ValueError
        choice=provider['choices'][0]
        if (type(choice) is not dict or type(choice.get('index')) is not int or choice['index']!=0
                or type(choice.get('message')) is not dict):
            raise ValueError
        message=choice['message'];finish=choice.get('finish_reason');tools=message.get('tool_calls')
        if (message.get('role')!='assistant' or finish not in {'stop','length','content_filter'}
                or (tools is not None and (type(tools) is not list or tools))
                or message.get('function_call') is not None):
            raise ValueError
        refusal=message.get('refusal')
        if refusal is not None and type(refusal) is not str:
            raise ValueError
        text=message.get('content')
        if type(text) is not str and not (text is None and (refusal or finish=='content_filter')):
            raise ValueError
        content=[]
        if type(text) is str:
            content.append({'type':'output_text','text':text})
        if refusal:
            content.append({'type':'refusal','refusal':refusal})
        status={'stop':'completed','length':'incomplete','content_filter':'failed'}[finish]
        result={'id':provider['id'],'model':provider['model'],'usage':deepcopy(provider['usage']),
            'status':status,'output':[{'type':'message','role':'assistant','status':status,'content':content}]}
        if 'provider_model' in provider:
            result['provider_model']=provider['provider_model']
        if finish=='length':
            result['incomplete_details']={'reason':'max_output_tokens'}
        if finish=='content_filter':
            result['error']={'code':'content_filter'}
        return result
    except (KeyError,ValueError,TypeError,AttributeError):
        raise ValueError('elice_chat_response_invalid') from None
