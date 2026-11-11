"""Elice Responses boundary with one local and one campaign-wide USD budget.

Usage-based cost intervals are kept separate from exact cost. Both budgets debit
the interval's upper endpoint, so cache ambiguity cannot release dollar capacity.
This module reads no credentials and never creates a network transport.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from decimal import Decimal
import hashlib
import inspect
import json
import re
from typing import Callable

import httpx

from adapters.guarded_transport import GuardedTransport, _json
from cost_accounting import BudgetRejected, CostBudget, _usd
from elice_billing import normalize_response, normalize_usage, cost_bounds, reservation_bound


class EliceTransport(httpx.AsyncBaseTransport):
    """Reserve both budgets before each real HTTP attempt, including retries.

    All callbacks are synchronous. Audit persistence must complete before the
    delegate can send. Successful raw provider responses are copied to the raw
    callback only after valid usage has settled; headers are never included.
    """

    def __init__(self, delegate: httpx.AsyncBaseTransport, *, budget: CostBudget,
                 global_budget: CostBudget, pricing: dict, allowed_models: set[str],
                 allowed_endpoint: str, allowed_limits: dict[str, dict[str, int]],
                 audit_callback: Callable[[dict], None] | None = None,
                 raw_response_callback: Callable[[dict], None] | None = None) -> None:
        if budget is global_budget:
            raise BudgetRejected('distinct_local_and_global_budgets_required')
        self._validator=GuardedTransport(delegate,budget=budget,pricing=pricing,
            allowed_models=allowed_models,allowed_endpoint=allowed_endpoint,allowed_limits=allowed_limits)
        if any(caps['max_input_bytes']>65536 or caps['max_output_tokens']>4096 for caps in self._validator._limits.values()):
            raise BudgetRejected('elice_campaign_limits_invalid')
        self._delegate=delegate
        self.budget=budget
        self.global_budget=global_budget
        self._audit_callback=audit_callback
        self._raw_callback=raw_response_callback
        self._halt_reason: str | None=None
        self._attempts: list[dict]=[]
        self._active: dict[str,dict]={}
        self._sent_attempts=0
        self._closed=False

    def snapshot(self) -> dict:
        local=self.budget.to_dict()
        global_state=self.global_budget.to_dict()
        for state in (local,global_state):
            state['accounting_basis']='billing_upper_bound'
            state['spent_upper_usd']=state['spent_usd']
        reason=self._halt_reason or global_state['halt_reason'] or local['halt_reason']
        return {'budget':local,'global_budget':global_state,'halted':reason is not None,
            'halt_reason':reason,'attempts':deepcopy(self._attempts),'sent_attempts':self._sent_attempts,
            'transport_integration':'elice_global_guard'}

    def _stop(self, reason: str) -> None:
        self._halt_reason=self._halt_reason or reason
        self.budget.halt(reason)
        self.global_budget.halt(reason)

    @staticmethod
    def _callback(callback, value: dict, code: str) -> None:
        if callback is None:
            return
        try:
            result=callback(deepcopy(value))
            if inspect.isawaitable(result):
                if inspect.iscoroutine(result):
                    result.close()
                raise TypeError('callbacks_must_be_synchronous')
        except BaseException:
            raise BudgetRejected(code) from None

    def _audit(self, row: dict) -> None:
        state=self.snapshot()
        emitted={**deepcopy(row),'budget':state['budget'],'global_budget':state['global_budget'],
            'halted':state['halted'],'halt_reason':state['halt_reason']}
        try:
            self._callback(self._audit_callback,emitted,'audit_persistence_failed')
        except BudgetRejected:
            self._stop('audit_persistence_failed')
            raise

    def _reject(self, code: str, *, model: str | None=None) -> None:
        self._stop(code)
        self._audit({'event':'rejected','error_code':code,**({'model':model} if model else {})})

    def _reserve(self, model: str, upper: Decimal) -> str:
        local_ticket=None
        try:
            local_ticket=self.budget.reserve(upper)
            global_ticket=self.global_budget.reserve(upper)
        except BudgetRejected as error:
            if local_ticket is not None:
                self.budget.settle(local_ticket,Decimal(0))
            self._reject(str(error),model=model)
            raise
        self._active[global_ticket]={'local_ticket':local_ticket,'model':model,'upper':upper,'sent':False}
        try:
            self._audit({'event':'reserved','attempt_id':global_ticket,'local_attempt_id':local_ticket,
                'model':model,'reserved_usd':_usd(upper),'accounting_basis':'billing_upper_bound'})
        except BudgetRejected:
            # No delegate call occurred; release both reservations as known zero.
            self._active.pop(global_ticket,None)
            self.budget.settle(local_ticket,Decimal(0))
            self.global_budget.settle(global_ticket,Decimal(0))
            raise
        return global_ticket

    def _settle(self, global_ticket: str, *, calculated: dict | None=None,
                usage: dict | None=None, response: dict | None=None,
                status: int | None=None, error_code: str | None=None) -> dict:
        active=self._active[global_ticket]
        high=None
        row={'event':'settled','attempt_id':global_ticket,'local_attempt_id':active['local_ticket'],
            'model':active['model'],'reserved_usd':_usd(active['upper']),
            'cost_usd':None,'cost_lower_usd':None,'cost_upper_usd':None,'cost_status':'unconfirmed',
            'accounting_basis':'billing_upper_bound','error_code':error_code,
            'http_status':status,'sent':active['sent'],'response_id':None}
        if calculated is not None:
            high=Decimal(calculated['cost_upper_usd'])
            low=Decimal(calculated['cost_lower_usd'])
            exact=calculated.get('cost_usd')
            if (not high.is_finite() or not low.is_finite() or low<0 or high<low
                    or (exact is not None and Decimal(exact)!=high)
                    or calculated.get('cost_status') not in {'confirmed','bounded'}):
                raise ValueError('billing_result_invalid')
            row.update(cost_usd=exact,cost_lower_usd=_usd(low),cost_upper_usd=_usd(high),
                cost_status=calculated['cost_status'],usage=deepcopy(usage))
            if usage is not None:
                row.update({key:value for key,value in usage.items() if type(value) is int})
        if response is not None:
            identifier=response.get('id')
            if type(identifier) is str and re.fullmatch(r'[A-Za-z0-9_.:-]{1,256}',identifier):
                row['response_id']=identifier
            provider_model=response.get('model')
            if type(provider_model) is str:
                row['provider_model']=provider_model
            encoded=json.dumps(response,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode('utf-8')
            row['raw_response_sha256']=hashlib.sha256(encoded).hexdigest()
        # Nothing can raise between validation and taking ownership of settlement.
        # If construction fails above, the caller can still settle this ticket unknown.
        self._active.pop(global_ticket)
        self.budget.settle(active['local_ticket'],high)
        self.global_budget.settle(global_ticket,high)
        if high is None:
            self._stop(error_code or 'response_usage_unconfirmed')
        elif high>active['upper']:
            row['error_code']='actual_cost_reservation_exceeded'
            self._stop('actual_cost_reservation_exceeded')
        self._attempts.append(deepcopy(row))
        self._audit(row)
        return row

    @staticmethod
    async def _read(response: httpx.Response, maximum: int) -> bytes:
        if response.is_stream_consumed:
            raw=response.content
            if len(raw)>maximum:
                raise BudgetRejected('response_byte_cap_exceeded')
            return raw
        chunks=bytearray()
        # Own closure ourselves: aiter_raw auto-closes before usage can settle,
        # which would discard already received usage on a source-close error.
        if not isinstance(response.stream,httpx.AsyncByteStream):
            raise BudgetRejected('response_stream_invalid')
        async for chunk in response.stream:
            if len(chunks)+len(chunk)>maximum:
                raise BudgetRejected('response_byte_cap_exceeded')
            chunks.extend(chunk)
        return bytes(chunks)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        state=self.snapshot()
        if state['halted']:
            raise BudgetRejected(state['halt_reason'])
        if self._closed:
            self._reject('transport_closed')
            raise BudgetRejected('transport_closed')
        try:
            model,maximum,stream,_=self._validator._request(request)
            if stream:
                raise BudgetRejected('elice_streaming_not_approved')
            request_data=_json(request.content)
            upper=reservation_bound(model,len(request.content),request_data['max_output_tokens'])
        except BudgetRejected as error:
            self._reject(str(error))
            raise
        except Exception:
            self._reject('elice_request_billing_invalid')
            raise BudgetRejected('elice_request_billing_invalid') from None
        ticket=self._reserve(model,upper)
        response=None
        primary_error: BaseException | None=None
        try:
            request.headers['Accept-Encoding']='identity'
            self._active[ticket]['sent']=True
            self._sent_attempts+=1
            response=await self._delegate.handle_async_request(request)
            if response.headers.get('content-encoding','identity').lower()!='identity':
                raise BudgetRejected('response_encoding_not_supported')
            content_type=response.headers.get('content-type','').split(';',1)[0].strip().lower()
            if content_type=='text/event-stream':
                raise BudgetRejected('elice_streaming_not_approved')
            raw=await self._read(response,maximum)
            envelope=_json(raw)
            if type(envelope) is not dict:
                raise ValueError('response_envelope_invalid')
            # A native Messages or Chat response has different cache-total rules.
            # It must never be silently certified as a Responses usage envelope.
            if response.is_success and (type(envelope.get('output')) is not list
                    or envelope.get('status') not in {'completed','incomplete','failed','cancelled'}):
                raise ValueError('response_protocol_invalid')
            raw_usage=envelope.get('usage')
            if (not response.is_success and type(raw_usage) is dict
                    and any(key in raw_usage for key in ('cache_creation_input_tokens','cache_read_input_tokens'))
                    and type(envelope.get('output')) is not list):
                raise ValueError('response_protocol_invalid')
            normalized=normalize_response(envelope,model)
            usage=normalize_usage(raw_usage)
            calculated=cost_bounds(model,usage)
            # Validate billing before removing the active reservation.
            high=Decimal(calculated['cost_upper_usd'])
            low=Decimal(calculated['cost_lower_usd'])
            if not high.is_finite() or not low.is_finite() or low<0 or high<low:
                raise ValueError('billing_result_invalid')
            row=self._settle(ticket,calculated=calculated,usage=usage,response=envelope,status=response.status_code)
            if self.snapshot()['halted']:
                raise BudgetRejected(self.snapshot()['halt_reason'])
            if response.is_success:
                trace=deepcopy(envelope)
                trace['_elice_billing']={'usage':deepcopy(usage),'cost_usd':row['cost_usd'],
                    'cost_lower_usd':row['cost_lower_usd'],'cost_upper_usd':row['cost_upper_usd'],
                    'cost_status':row['cost_status'],'provider_model':envelope.get('model'),
                    'canonical_model':model,'attempt_id':ticket,'accounting_basis':'billing_upper_bound'}
                try:
                    self._callback(self._raw_callback,trace,'raw_response_persistence_failed')
                except BudgetRejected:
                    self._stop('raw_response_persistence_failed')
                    raise
            encoded=json.dumps(normalized,ensure_ascii=False,allow_nan=False).encode('utf-8')
            headers={key:value for key,value in response.headers.items()
                if key.lower() not in {'content-length','content-encoding','transfer-encoding'}}
            return httpx.Response(response.status_code,headers=headers,content=encoded,
                extensions=response.extensions,request=request)
        except BaseException as error:
            primary_error=error
            if isinstance(error,asyncio.CancelledError):
                code='attempt_cancelled'
            elif isinstance(error,BudgetRejected):
                code=str(error)
            else:
                code='response_usage_unconfirmed' if response is not None else 'transport_failed'
            if ticket in self._active:
                try:
                    self._settle(ticket,error_code=code,status=None if response is None else response.status_code)
                except BudgetRejected:
                    self._stop('audit_persistence_failed')
            self._stop(code)
            if isinstance(error,(asyncio.CancelledError,GeneratorExit)):
                raise
            raise BudgetRejected(code) from None
        finally:
            if response is not None:
                try:
                    await response.aclose()
                except BaseException:
                    self._stop('response_close_failed')
                    try:
                        self._audit({'event':'rejected','error_code':'response_close_failed','model':model})
                    except BudgetRejected:
                        pass
                    if primary_error is None:
                        raise BudgetRejected('response_close_failed') from None

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed=True
        # Closing while an attempt is still active cannot release its cost as zero.
        failure: BaseException | None=None
        for ticket in tuple(self._active):
            try:
                self._settle(ticket,error_code='transport_closed_before_usage')
            except BaseException as error:
                failure=failure or error
        try:
            await self._delegate.aclose()
        except BaseException:
            self._stop('transport_close_failed')
            self._audit({'event':'rejected','error_code':'transport_close_failed'})
            raise BudgetRejected('transport_close_failed') from None
        if failure is not None:
            raise failure
