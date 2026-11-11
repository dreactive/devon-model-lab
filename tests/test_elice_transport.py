"""Elice accounting boundary tests; every HTTP operation is in memory."""
from __future__ import annotations

import asyncio
from decimal import Decimal
import hashlib
import importlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode=True
LAB=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(LAB))
import httpx
from cost_accounting import CostBudget, BudgetRejected

MODEL='claude-haiku-5-5'
ENDPOINT='https://offline.invalid/v1/responses'


def pricing(model=MODEL):
    return {'models':{model:{'input_usd_per_million':Decimal('.1'),'output_usd_per_million':Decimal('.5'),
        'cached_input_usd_per_million':Decimal('.01'),'reasoning_output_usd_per_million':Decimal('.5'),
        'source_url':'https://offline.invalid/rates','checked_at':'2026-11-11','price_version':'test-only'}}}


def body(model=MODEL,**changes):
    return {'model':model,'instructions':'synthetic instructions','input':[{'role':'user','content':[{'type':'input_text','text':'synthetic input'}]}],
        'text':{'format':{'type':'json_schema','name':'test','schema':{'type':'object'},'strict':True}},
        'max_output_tokens':100,'store':False,**changes}


def envelope(model=MODEL,**changes):
    return {'model':model,'id':'offline-response','status':'completed','usage':{'input_tokens':100,'output_tokens':20,
        'input_tokens_details':{'cached_tokens':0,'cache_write_tokens':0},'output_tokens_details':{'reasoning_tokens':0}},
        'output':[{'type':'message','role':'assistant','status':'completed','content':[{'type':'output_text','text':'{"ok":true}'}]}],**changes}


class Chunks(httpx.AsyncByteStream):
    def __init__(self,chunks,close_error=False): self.chunks=chunks;self.closed=False;self.close_error=close_error
    async def __aiter__(self):
        for chunk in self.chunks:
            if isinstance(chunk,BaseException): raise chunk
            yield chunk
    async def aclose(self):
        self.closed=True
        if self.close_error: raise RuntimeError('synthetic-close-error')


class EliceTransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        blocker=patch.object(httpx.AsyncHTTPTransport,'handle_async_request',side_effect=AssertionError('real network forbidden'))
        blocker.start();self.addCleanup(blocker.stop)

    def guard(self,handler=None,*,global_budget=None,local_budget=None,model=MODEL,audit=None,raw=None,limits=None):
        module=importlib.import_module('adapters.elice_transport')
        return module.EliceTransport(httpx.MockTransport(handler or (lambda request:httpx.Response(200,json=envelope(model)))),
            budget=local_budget or CostBudget(Decimal('1'),22,approved=True),
            global_budget=global_budget or CostBudget(Decimal('10'),192,approved=True),
            pricing=pricing(model),allowed_models={model},allowed_endpoint=ENDPOINT,
            allowed_limits=limits or {model:{'max_input_bytes':65536,'max_output_tokens':4096,'max_response_bytes':100000}},
            audit_callback=audit,raw_response_callback=raw)

    async def send(self,guard,payload=None):
        async with httpx.AsyncClient(transport=guard,trust_env=False) as client:
            return await client.post(ENDPOINT,json=payload or body())

    async def test_two_transports_share_one_global_attempt_cap(self):
        global_budget=CostBudget(Decimal('10'),1,approved=True)
        sent=[]
        first=self.guard(lambda request:sent.append('first') or httpx.Response(200,json=envelope()),global_budget=global_budget)
        second=self.guard(lambda request:sent.append('second') or httpx.Response(200,json=envelope()),global_budget=global_budget)
        await self.send(first)
        with self.assertRaisesRegex(BudgetRejected,'attempt_cap_reached'):
            await self.send(second)
        self.assertEqual(sent,['first'])
        self.assertEqual(global_budget.to_dict()['attempts_started'],1)
        self.assertEqual(global_budget.to_dict()['in_flight_attempts'],0)

    async def test_global_money_reservation_is_durable_before_http(self):
        from elice_billing import reservation_bound
        encoded=json.dumps(body()).encode('utf-8')
        upper=reservation_bound(MODEL,len(encoded),100)
        global_budget=CostBudget(upper+Decimal('.000005'),192,approved=True)
        audit=[];sent=[]
        def respond(request):
            self.assertEqual(global_budget.to_dict()['in_flight_attempts'],1)
            self.assertEqual(audit[-1]['event'],'reserved')
            sent.append(1)
            return httpx.Response(200,json=envelope())
        guard=self.guard(respond,global_budget=global_budget,audit=audit.append)
        async with httpx.AsyncClient(transport=guard,trust_env=False) as client:
            await client.post(ENDPOINT,content=encoded)
            with self.assertRaisesRegex(BudgetRejected,'monetary_cap_insufficient'):
                await client.post(ENDPOINT,content=encoded)
        self.assertEqual(sent,[1])

    async def test_missing_usage_halts_the_next_model_globally(self):
        global_budget=CostBudget(Decimal('10'),192,approved=True)
        sends=[]
        first=self.guard(lambda request:sends.append(1) or httpx.Response(200,json=envelope(usage=None)),global_budget=global_budget)
        with self.assertRaises(BudgetRejected): await self.send(first)
        next_model='gpt-6-luna'
        second=self.guard(lambda request:sends.append(2) or httpx.Response(200,json=envelope(next_model)),global_budget=global_budget,model=next_model)
        with self.assertRaises(BudgetRejected): await self.send(second,body(next_model))
        self.assertEqual(sends,[1])
        self.assertEqual(global_budget.to_dict()['unknown_attempts'],1)

    async def test_cache_write_upper_is_debited_and_reasoning_not_doubled(self):
        usage={'input_tokens':100,'output_tokens':20,'input_tokens_details':{'cached_tokens':0,'cache_write_tokens':100},
            'output_tokens_details':{'reasoning_tokens':5}}
        global_budget=CostBudget(Decimal('10'),192,approved=True)
        guard=self.guard(lambda request:httpx.Response(200,json=envelope(usage=usage)),global_budget=global_budget)
        await self.send(guard)
        row=guard.snapshot()['attempts'][0]
        # Unknown Claude write TTL: upper .1*2*100 + .5*20, no extra reasoning.
        self.assertEqual(Decimal(row['cost_upper_usd']),Decimal('.00003'))
        self.assertEqual(Decimal(global_budget.to_dict()['spent_usd']),Decimal('.00003'))
        self.assertIsNone(row['cost_usd'])
        self.assertEqual(row['cost_status'],'bounded')

    async def test_usage_and_model_aliases_are_normalized_for_original_client(self):
        usage={'prompt_tokens':100,'completion_tokens':20,'cached_prompt_tokens':0,'cache_write_prompt_tokens':0}
        response=await self.send(self.guard(lambda request:httpx.Response(200,json=envelope('anthropic/'+MODEL,usage=usage))))
        returned=response.json()
        self.assertEqual(returned['model'],MODEL)
        self.assertEqual(returned['usage']['input_tokens'],100)
        self.assertEqual(returned['usage']['output_tokens'],20)
        self.assertEqual(returned['output'],envelope()['output'])

    async def test_raw_callback_cannot_mutate_returned_response(self):
        raw=[]
        def capture(value): raw.append(value);value['output']=[]
        response=await self.send(self.guard(raw=capture))
        self.assertEqual(len(raw),1)
        self.assertEqual(response.json()['output'],envelope()['output'])

    async def test_callback_failure_halts_globally_after_cost_is_preserved(self):
        global_budget=CostBudget(Decimal('10'),192,approved=True)
        callbacks=[]
        def fail(value): callbacks.append(True);raise OSError('synthetic-write-error')
        guard=self.guard(global_budget=global_budget,raw=fail)
        with self.assertRaisesRegex(BudgetRejected,'raw_response_persistence_failed'):
            await self.send(guard)
        self.assertTrue(guard.snapshot()['halted'])
        self.assertGreater(Decimal(global_budget.to_dict()['spent_usd']),Decimal(0))
        self.assertTrue(global_budget.to_dict()['halted'])
        self.assertEqual(callbacks,[True])

    async def test_invalid_billing_result_settles_unknown_without_dangling_reservations(self):
        module=importlib.import_module('adapters.elice_transport')
        global_budget=CostBudget(Decimal('10'),192,approved=True)
        local_budget=CostBudget(Decimal('1'),22,approved=True)
        guard=self.guard(global_budget=global_budget,local_budget=local_budget)
        with patch.object(module,'cost_bounds',return_value={'cost_lower_usd':'0','cost_upper_usd':'.00002','cost_usd':None,'cost_status':'invalid'}):
            with self.assertRaises(BudgetRejected): await self.send(guard)
        for budget in (global_budget,local_budget):
            self.assertEqual(budget.to_dict()['unknown_attempts'],1)
            self.assertEqual(budget.to_dict()['in_flight_attempts'],0)

    async def test_close_failure_preserves_known_cost_and_halts_globally(self):
        source=Chunks([json.dumps(envelope()).encode()],close_error=True)
        global_budget=CostBudget(Decimal('10'),192,approved=True)
        guard=self.guard(lambda request:httpx.Response(200,stream=source),global_budget=global_budget)
        with self.assertRaisesRegex(BudgetRejected,'response_close_failed'): await self.send(guard)
        self.assertTrue(source.closed)
        self.assertGreater(Decimal(global_budget.to_dict()['spent_usd']),Decimal(0))
        self.assertEqual(global_budget.to_dict()['unknown_attempts'],0)
        self.assertTrue(global_budget.to_dict()['halted'])

    async def test_transport_close_still_closes_delegate_when_settlement_audit_fails(self):
        global_budget=CostBudget(Decimal('10'),192,approved=True)
        guard=self.guard(global_budget=global_budget)
        guard._reserve(MODEL,Decimal('.0001'))
        closed=[]
        async def close(): closed.append(True)
        guard._delegate.aclose=close
        def fail(row): raise OSError('synthetic-close-audit-error')
        guard._audit_callback=fail
        with self.assertRaises(BudgetRejected): await guard.aclose()
        self.assertEqual(closed,[True])
        self.assertEqual(global_budget.to_dict()['in_flight_attempts'],0)

    async def test_audit_failure_prevents_http(self):
        global_budget=CostBudget(Decimal('10'),192,approved=True);sent=[]
        def fail(row): raise OSError('synthetic-audit-error')
        guard=self.guard(lambda request:sent.append(1),global_budget=global_budget,audit=fail)
        with self.assertRaisesRegex(BudgetRejected,'audit_persistence_failed'): await self.send(guard)
        self.assertEqual(sent,[])
        self.assertTrue(global_budget.to_dict()['halted'])

    async def test_oversized_response_is_unknown_and_stream_is_closed(self):
        source=Chunks([b'x'*40,b'y'*40])
        global_budget=CostBudget(Decimal('10'),192,approved=True)
        guard=self.guard(lambda request:httpx.Response(200,stream=source),global_budget=global_budget,
            limits={MODEL:{'max_input_bytes':65536,'max_output_tokens':4096,'max_response_bytes':60}})
        with self.assertRaises(BudgetRejected): await self.send(guard)
        self.assertTrue(source.closed)
        self.assertEqual(global_budget.to_dict()['unknown_attempts'],1)

    async def test_cancellation_halts_unknown_and_closes_response(self):
        source=Chunks([b'{',asyncio.CancelledError()])
        global_budget=CostBudget(Decimal('10'),192,approved=True)
        guard=self.guard(lambda request:httpx.Response(200,stream=source),global_budget=global_budget)
        with self.assertRaises(asyncio.CancelledError): await self.send(guard)
        self.assertTrue(source.closed)
        self.assertEqual(global_budget.to_dict()['unknown_attempts'],1)

    async def test_http_error_with_usage_is_billed_before_error_diagnostic_capture(self):
        raw=[];global_budget=CostBudget(Decimal('10'),192,approved=True)
        def capture(value):
            self.assertGreater(Decimal(global_budget.to_dict()['spent_usd']),Decimal(0))
            raw.append(value)
        guard=self.guard(lambda request:httpx.Response(429,json=envelope()),global_budget=global_budget,raw=capture)
        response=await self.send(guard)
        self.assertEqual(response.status_code,429)
        self.assertEqual(len(raw),1)
        self.assertEqual(raw[0]['_elice_diagnostic']['http_status'],429)
        self.assertGreater(Decimal(global_budget.to_dict()['spent_usd']),Decimal(0))

    async def test_json_http_error_without_usage_is_captured_once_after_unknown_settlement(self):
        traces=[]
        global_budget=CostBudget(Decimal('10'),192,approved=True)
        provider={'detail':'Not Found','api_key':'FAKE_PROVIDER_ECHO'}
        def capture(value):
            self.assertEqual(global_budget.to_dict()['unknown_attempts'],1)
            self.assertEqual(global_budget.to_dict()['in_flight_attempts'],0)
            traces.append(value)
        guard=self.guard(lambda request:httpx.Response(404,json=provider),global_budget=global_budget,raw=capture)
        with self.assertRaises(BudgetRejected): await self.send(guard)
        self.assertEqual(len(traces),1)
        self.assertEqual(traces[0]['detail'],'Not Found')
        self.assertEqual(traces[0]['_elice_diagnostic']['http_status'],404)
        self.assertEqual(traces[0]['_elice_diagnostic']['body_kind'],'json')
        self.assertNotIn('headers',traces[0])
        self.assertTrue(global_budget.to_dict()['halted'])

    async def test_non_json_http_error_captures_bounded_body_and_hash(self):
        traces=[];raw=b'upstream gateway unavailable'
        global_budget=CostBudget(Decimal('10'),192,approved=True)
        guard=self.guard(lambda request:httpx.Response(502,content=raw),global_budget=global_budget,raw=traces.append)
        with self.assertRaises(BudgetRejected): await self.send(guard)
        self.assertEqual(len(traces),1)
        diagnostic=traces[0]['_elice_diagnostic']
        self.assertEqual(diagnostic['body_kind'],'non_json')
        self.assertEqual(diagnostic['body_text'],raw.decode())
        self.assertEqual(diagnostic['body_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertFalse(diagnostic['body_truncated'])
        self.assertEqual(global_budget.to_dict()['unknown_attempts'],1)

    async def test_oversized_http_error_keeps_only_bounded_prefix_once(self):
        traces=[];source=Chunks([b'a'*40,b'b'*40])
        global_budget=CostBudget(Decimal('10'),192,approved=True)
        guard=self.guard(lambda request:httpx.Response(500,stream=source),global_budget=global_budget,raw=traces.append,
            limits={MODEL:{'max_input_bytes':65536,'max_output_tokens':4096,'max_response_bytes':60}})
        with self.assertRaises(BudgetRejected): await self.send(guard)
        self.assertEqual(len(traces),1)
        diagnostic=traces[0]['_elice_diagnostic']
        self.assertEqual(diagnostic['captured_body_bytes'],60)
        self.assertEqual(diagnostic['body_text'],'a'*40+'b'*20)
        self.assertTrue(diagnostic['body_truncated'])
        self.assertTrue(source.closed)

    async def test_error_diagnostic_callback_failure_does_not_drop_unknown_reservation(self):
        callbacks=[];source=Chunks([b'{"detail":"Not Found"}'])
        global_budget=CostBudget(Decimal('10'),192,approved=True)
        local_budget=CostBudget(Decimal('1'),22,approved=True)
        def fail(value): callbacks.append(True);raise OSError('synthetic-error-trace-failure')
        guard=self.guard(lambda request:httpx.Response(404,stream=source),global_budget=global_budget,local_budget=local_budget,raw=fail)
        with self.assertRaises(BudgetRejected): await self.send(guard)
        self.assertEqual(callbacks,[True])
        for budget in (global_budget,local_budget):
            self.assertEqual(budget.to_dict()['unknown_attempts'],1)
            self.assertEqual(budget.to_dict()['in_flight_attempts'],0)
            self.assertTrue(budget.to_dict()['halted'])
        self.assertTrue(source.closed)

    async def test_snapshot_labels_both_budget_ledgers_as_elice_guard(self):
        guard=self.guard()
        snapshot=guard.snapshot()
        self.assertEqual(snapshot['budget']['transport_integration'],'elice_global_guard')
        self.assertEqual(snapshot['global_budget']['transport_integration'],'elice_global_guard')
        await guard.aclose()

    async def test_known_error_trace_failure_preserves_debit_and_closes_source(self):
        source=Chunks([json.dumps(envelope()).encode()]);callbacks=[]
        global_budget=CostBudget(Decimal('10'),192,approved=True)
        def fail(value): callbacks.append(True);raise OSError('synthetic-error-trace-failure')
        guard=self.guard(lambda request:httpx.Response(429,stream=source),global_budget=global_budget,raw=fail)
        with self.assertRaisesRegex(BudgetRejected,'raw_response_persistence_failed'): await self.send(guard)
        self.assertEqual(callbacks,[True])
        self.assertGreater(Decimal(global_budget.to_dict()['spent_usd']),Decimal(0))
        self.assertEqual(global_budget.to_dict()['unknown_attempts'],0)
        self.assertEqual(global_budget.to_dict()['in_flight_attempts'],0)
        self.assertTrue(global_budget.to_dict()['halted'])
        self.assertTrue(source.closed)

    async def test_error_trace_construction_failure_still_closes_and_halts(self):
        source=Chunks([b'{"detail":"Not Found"}'])
        global_budget=CostBudget(Decimal('10'),192,approved=True)
        guard=self.guard(lambda request:httpx.Response(404,stream=source),global_budget=global_budget)
        with patch.object(guard,'_error_diagnostic',side_effect=ValueError('synthetic-trace-construction-error')):
            with self.assertRaises(BudgetRejected): await self.send(guard)
        self.assertTrue(source.closed)
        self.assertTrue(global_budget.to_dict()['halted'])
        self.assertEqual(global_budget.to_dict()['unknown_attempts'],1)
        self.assertEqual(global_budget.to_dict()['in_flight_attempts'],0)

    async def test_success_status_with_missing_usage_gets_one_integration_diagnostic(self):
        traces=[];global_budget=CostBudget(Decimal('10'),192,approved=True)
        provider=envelope(usage=None)
        guard=self.guard(lambda request:httpx.Response(200,json=provider),global_budget=global_budget,raw=traces.append)
        with self.assertRaises(BudgetRejected): await self.send(guard)
        self.assertEqual(len(traces),1)
        self.assertEqual(traces[0]['_elice_diagnostic']['kind'],'integration_error')
        self.assertEqual(traces[0]['_elice_diagnostic']['http_status'],200)
        self.assertEqual(traces[0]['output'],provider['output'])
        self.assertEqual(global_budget.to_dict()['unknown_attempts'],1)
        self.assertEqual(global_budget.to_dict()['in_flight_attempts'],0)
        self.assertTrue(global_budget.to_dict()['halted'])

    async def test_wrong_model_on_success_status_preserves_provider_body_once(self):
        traces=[];global_budget=CostBudget(Decimal('10'),192,approved=True)
        provider=envelope('unexpected-model')
        guard=self.guard(lambda request:httpx.Response(200,json=provider),global_budget=global_budget,raw=traces.append)
        with self.assertRaises(BudgetRejected): await self.send(guard)
        self.assertEqual(len(traces),1)
        self.assertEqual(traces[0]['model'],'unexpected-model')
        self.assertEqual(traces[0]['_elice_diagnostic']['kind'],'integration_error')
        self.assertEqual(global_budget.to_dict()['unknown_attempts'],1)

    async def test_non_json_on_success_status_preserves_bounded_diagnostic(self):
        traces=[];global_budget=CostBudget(Decimal('10'),192,approved=True)
        raw=b'<html>synthetic proxy error</html>'
        guard=self.guard(lambda request:httpx.Response(200,content=raw),global_budget=global_budget,raw=traces.append)
        with self.assertRaises(BudgetRejected): await self.send(guard)
        self.assertEqual(len(traces),1)
        self.assertEqual(traces[0]['_elice_diagnostic']['kind'],'integration_error')
        self.assertEqual(traces[0]['_elice_diagnostic']['body_text'],raw.decode())
        self.assertEqual(global_budget.to_dict()['unknown_attempts'],1)

    async def test_invalid_request_is_rejected_without_reservations(self):
        global_budget=CostBudget(Decimal('10'),192,approved=True);sent=[]
        guard=self.guard(lambda request:sent.append(1),global_budget=global_budget)
        with self.assertRaises(BudgetRejected): await self.send(guard,body(stream=True))
        self.assertEqual(sent,[])
        self.assertEqual(global_budget.to_dict()['attempts_started'],0)

    async def test_long_input_limit_configuration_is_rejected(self):
        with self.assertRaises(BudgetRejected):
            self.guard(limits={MODEL:{'max_input_bytes':100001,'max_output_tokens':4096,'max_response_bytes':100000}})
