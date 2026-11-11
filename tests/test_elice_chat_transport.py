"""Mock-only strict Chat transport accounting and canonical contract checks."""
import asyncio
from decimal import Decimal
import json
import unittest
from unittest.mock import patch

import httpx
from cost_accounting import CostBudget,BudgetRejected
from test_elice_transport import body,pricing,Chunks,ENDPOINT
from test_elice_chat_bridge import chat,MODELS


class EliceChatTransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        blocker=patch.object(httpx.AsyncHTTPTransport,'handle_async_request',side_effect=AssertionError('real network forbidden'))
        blocker.start();self.addCleanup(blocker.stop)

    def guard(self,handler,*,model=MODELS[0],audit=None,raw=None,global_budget=None,limits=None,protocol='chat_completions'):
        from adapters.elice_transport import EliceTransport
        try:
            return EliceTransport(httpx.MockTransport(handler),budget=CostBudget(Decimal('1'),22,approved=True),
                global_budget=global_budget or CostBudget(Decimal('10'),192,approved=True),pricing=pricing(model),
                allowed_models={model},allowed_endpoint=ENDPOINT,wire_protocol=protocol,
                allowed_limits=limits or {model:{'max_input_bytes':65536,'max_output_tokens':2000,'max_response_bytes':100000}},
                audit_callback=audit,raw_response_callback=raw)
        except TypeError:self.fail('EliceTransport lacks the explicit approved wire_protocol seam')

    async def send(self,guard,payload=None,url=ENDPOINT):
        async with httpx.AsyncClient(transport=guard,trust_env=False) as client:
            return await client.post(url,json=payload or body(MODELS[0],max_output_tokens=2000),headers={'Authorization':'Bearer FAKE_TEST_ONLY'})

    async def test_chat_wire_is_strict_preserves_store_and_bills_original_usage_for_all_four(self):
        for model in MODELS:
            with self.subTest(model=model):
                seen=[];traces=[];events=[]
                provider=chat(model);provider['choices'][0]['message']['content']=' {"unchanged":true} \n'
                provider['choices'][0]['message'].update(tool_calls=None,function_call=None)
                def respond(request):
                    seen.append(request)
                    self.assertEqual(str(request.url),'https://offline.invalid/v1/chat/completions')
                    self.assertEqual(events[-1]['event'],'reserved')
                    return httpx.Response(200,json=provider)
                guard=self.guard(respond,model=model,audit=events.append,raw=traces.append)
                original=body(model,max_output_tokens=2000)
                response=await self.send(guard,original)
                sent=json.loads(seen[0].content)
                self.assertEqual(sent['messages'][0]['content'],original['instructions'])
                self.assertEqual(sent['messages'][1]['content'],original['input'][0]['content'][0]['text'])
                self.assertEqual(sent['response_format']['json_schema']['schema'],original['text']['format']['schema'])
                self.assertIs(sent['response_format']['json_schema']['strict'],True)
                self.assertIs(sent['store'],False);self.assertIs(sent['stream'],False)
                self.assertEqual(sent['max_completion_tokens'],2000)
                self.assertNotIn('temperature',sent);self.assertNotIn('text',sent)
                self.assertEqual(response.json()['output'][0]['content'][0]['text'],provider['choices'][0]['message']['content'])
                self.assertEqual(response.json()['id'],provider['id'])
                self.assertEqual(response.json()['usage']['input_tokens'],100)
                self.assertEqual(traces[0]['choices'],provider['choices']);self.assertNotIn('output',traces[0])
                self.assertEqual(traces[0]['_elice_wire']['protocol'],'chat_completions')
                self.assertEqual(events[-1]['usage']['input_tokens'],100)
                self.assertEqual(events[-1]['wire_protocol'],'chat_completions')
                self.assertEqual(guard.snapshot()['wire_protocol'],'chat_completions')

    async def test_translated_size_is_reserved_and_persisted_before_delegate(self):
        import adapters.elice_transport as module
        real=module.reservation_bound;seen=[];events=[];provider=chat()
        def bound(model,input_bytes,max_output):
            seen.append(input_bytes);return real(model,input_bytes,max_output)
        def respond(request):
            row=events[-1]
            self.assertEqual(row['wire_request_bytes'],len(request.content))
            self.assertEqual(seen[-1],max(row['canonical_request_bytes'],len(request.content)))
            self.assertEqual(row['reservation_input_bytes'],seen[-1])
            return httpx.Response(200,json=provider)
        guard=self.guard(respond,audit=events.append)
        with patch.object(module,'reservation_bound',side_effect=bound):await self.send(guard)
        self.assertEqual(guard.snapshot()['request_byte_counts'][0]['reservation_input_bytes'],seen[0])

    async def test_wire_growth_beyond_approved_byte_cap_is_rejected_before_reservation(self):
        from adapters.elice_chat_bridge import request_to_chat
        payload=body(MODELS[0],max_output_tokens=2000)
        original=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()
        translated=json.dumps(request_to_chat(payload),ensure_ascii=False,separators=(',',':')).encode()
        self.assertGreater(len(translated),len(original))
        budget=CostBudget(Decimal('10'),192,approved=True);sent=[]
        guard=self.guard(lambda r:sent.append(r),global_budget=budget,
            limits={MODELS[0]:{'max_input_bytes':len(original),'max_output_tokens':2000,'max_response_bytes':100000}})
        async with httpx.AsyncClient(transport=guard,trust_env=False) as client:
            with self.assertRaisesRegex(BudgetRejected,'approved_input_cap_exceeded'):
                await client.post(ENDPOINT,content=original)
        self.assertEqual(sent,[]);self.assertEqual(budget.to_dict()['attempts_started'],0)

    async def test_original_chat_cache_ttl_and_model_alias_are_retained_for_accounting(self):
        model='claude-haiku-5-5';provider=chat('anthropic/'+model)
        provider['usage'].update(cache_write_prompt_tokens=100,cache_write_short_tokens=100)
        traces=[];guard=self.guard(lambda r:httpx.Response(200,json=provider),model=model,raw=traces.append)
        result=(await self.send(guard,body(model,max_output_tokens=2000))).json()
        row=guard.snapshot()['attempts'][0]
        self.assertEqual(Decimal(row['cost_usd']),Decimal('.0000225'))
        self.assertEqual(row['usage']['cache_write_short_tokens'],100)
        self.assertEqual(result['model'],model);self.assertEqual(result['provider_model'],'anthropic/'+model)
        self.assertEqual(traces[0]['usage'],provider['usage'])

    async def test_known_chat_http_error_is_billed_and_captured_once_without_fallback(self):
        traces=[];calls=[];provider=chat()
        guard=self.guard(lambda r:calls.append(r) or httpx.Response(429,json=provider),raw=traces.append)
        response=await self.send(guard)
        self.assertEqual(response.status_code,429);self.assertEqual(len(calls),1)
        self.assertEqual(len(traces),1);self.assertEqual(traces[0]['choices'],provider['choices'])
        self.assertEqual(traces[0]['_elice_diagnostic']['http_status'],429)
        self.assertEqual(guard.snapshot()['global_budget']['unknown_attempts'],0)
        self.assertGreater(Decimal(guard.snapshot()['global_budget']['spent_usd']),Decimal(0))

    async def test_chat_native_cache_semantics_bounded_body_and_cancellation_fail_closed(self):
        for kind in ('native_usage','oversized','cancelled'):
            with self.subTest(kind=kind):
                provider=chat();traces=[]
                provider['usage']={'input_tokens':100,'output_tokens':20,'cache_creation_input_tokens':50}
                if kind=='native_usage':chunks=[json.dumps(provider).encode()];maximum=100000
                elif kind=='oversized':chunks=[b'a'*40,b'b'*40];maximum=60
                else:chunks=[b'{',asyncio.CancelledError()];maximum=100000
                source=Chunks(chunks);guard=self.guard(lambda r:httpx.Response(200,stream=source),raw=traces.append,
                    limits={MODELS[0]:{'max_input_bytes':65536,'max_output_tokens':2000,'max_response_bytes':maximum}})
                with self.assertRaises(asyncio.CancelledError if kind=='cancelled' else BudgetRejected):await self.send(guard)
                self.assertEqual(len(traces),1);self.assertTrue(source.closed)
                self.assertEqual(guard.snapshot()['global_budget']['unknown_attempts'],1)
                self.assertLessEqual(traces[0]['_elice_diagnostic']['captured_body_bytes'],maximum)

    async def test_canonical_endpoint_and_schema_validate_before_any_translation_or_reservation(self):
        for kind in ('endpoint','schema','output','stream'):
            with self.subTest(kind=kind):
                sent=[];budget=CostBudget(Decimal('10'),192,approved=True)
                guard=self.guard(lambda r:sent.append(r),global_budget=budget)
                value=body(MODELS[0],max_output_tokens=2000);url=ENDPOINT
                if kind=='endpoint':url='https://offline.invalid/v1/chat/completions'
                elif kind=='schema':value['text']['format']['strict']=False
                elif kind=='output':value['max_output_tokens']=2001
                else:value['stream']=True
                with self.assertRaises(BudgetRejected):await self.send(guard,value,url)
                self.assertEqual(sent,[]);self.assertEqual(budget.to_dict()['attempts_started'],0)

    async def test_chat_constructor_rejects_unknown_protocol_gpt_or_caps_above_2000(self):
        for kind in ('protocol','gpt','cap'):
            with self.subTest(kind=kind):
                model='gpt-6-luna' if kind=='gpt' else MODELS[0]
                kwargs={'model':model}
                if kind=='protocol':kwargs['protocol']='automatic_fallback'
                if kind=='cap':kwargs['limits']={model:{'max_input_bytes':65536,'max_output_tokens':4096,'max_response_bytes':100000}}
                with self.assertRaises(BudgetRejected):self.guard(lambda r:None,**kwargs)

    async def test_missing_usage_and_error_capture_once_and_halt_next_protocol_model(self):
        for status in (200,400):
            with self.subTest(status=status):
                traces=[];sent=[];budget=CostBudget(Decimal('10'),192,approved=True)
                provider=chat(usage=None) if status==200 else {'error':{'message':'unsupported strict schema'}}
                source=Chunks([json.dumps(provider).encode()])
                guard=self.guard(lambda r:sent.append(1) or httpx.Response(status,stream=source),global_budget=budget,raw=traces.append)
                with self.assertRaises(BudgetRejected):await self.send(guard)
                self.assertEqual(len(traces),1);self.assertEqual(traces[0]['_elice_wire']['protocol'],'chat_completions')
                self.assertEqual(budget.to_dict()['unknown_attempts'],1);self.assertTrue(source.closed)
                second=self.guard(lambda r:sent.append(2),global_budget=budget)
                with self.assertRaises(BudgetRejected):await self.send(second)
                self.assertEqual(sent,[1])

    async def test_invalid_chat_shape_wrong_model_and_non_json_remain_bounded_failures(self):
        for kind in ('choices','model','non_json','native_messages'):
            with self.subTest(kind=kind):
                traces=[];provider=chat()
                if kind=='choices':provider['choices'].append(provider['choices'][0])
                if kind=='model':provider['model']='unexpected-model'
                if kind=='native_messages':provider={'model':MODELS[0],'id':'messages','content':[],'usage':{'input_tokens':1,'output_tokens':1}}
                raw=b'<html>gateway</html>' if kind=='non_json' else json.dumps(provider).encode()
                guard=self.guard(lambda r:httpx.Response(200,content=raw),raw=traces.append)
                with self.assertRaises(BudgetRejected):await self.send(guard)
                self.assertEqual(len(traces),1)
                self.assertEqual(traces[0]['_elice_diagnostic']['kind'],'integration_error')
                self.assertEqual(guard.snapshot()['global_budget']['unknown_attempts'],1)

    async def test_length_refusal_and_filter_are_billed_without_success_rewriting(self):
        for kind in ('length','refusal','content_filter'):
            with self.subTest(kind=kind):
                provider=chat();choice=provider['choices'][0]
                if kind=='refusal':choice['message']={'role':'assistant','content':None,'refusal':'exact refusal'}
                else:choice['finish_reason']=kind
                guard=self.guard(lambda r:httpx.Response(200,json=provider))
                returned=(await self.send(guard)).json()
                self.assertGreater(Decimal(guard.snapshot()['global_budget']['spent_usd']),Decimal(0))
                if kind=='refusal':self.assertEqual(returned['output'][0]['content'][0]['refusal'],'exact refusal')
                else:self.assertNotEqual(returned['status'],'completed')

    async def test_chat_callback_failure_preserves_known_cost_and_exactly_one_trace(self):
        calls=[];provider=chat();source=Chunks([json.dumps(provider).encode()])
        def fail(trace):calls.append(trace);raise OSError('offline persistence failure')
        guard=self.guard(lambda r:httpx.Response(200,stream=source),raw=fail)
        with self.assertRaisesRegex(BudgetRejected,'raw_response_persistence_failed'):await self.send(guard)
        self.assertEqual(len(calls),1);self.assertTrue(source.closed)
        self.assertEqual(guard.snapshot()['global_budget']['unknown_attempts'],0)
        self.assertGreater(Decimal(guard.snapshot()['global_budget']['spent_usd']),Decimal(0))
