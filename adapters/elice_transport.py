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
from adapters.elice_chat_bridge import CHAT_MODELS, request_to_chat, response_to_responses
from cost_accounting import BudgetRejected, CostBudget, _usd
from elice_billing import normalize_response, normalize_usage, cost_bounds, reservation_bound


class EliceTransport(httpx.AsyncBaseTransport):
    """Reserve both budgets before each real HTTP attempt, including retries.

    All callbacks are synchronous. Audit persistence must complete before the
    delegate can send. Successful responses are copied after valid usage settles.
    HTTP/integration-failure diagnostics follow known or unknown settlement;
    headers and request data are never included. Root owns redaction/persistence.
    """

    def __init__(self, delegate: httpx.AsyncBaseTransport, *, budget: CostBudget,
                 global_budget: CostBudget, pricing: dict, allowed_models: set[str],
                 allowed_endpoint: str, allowed_limits: dict[str, dict[str, int]],
                 audit_callback: Callable[[dict], None] | None = None,
                 raw_response_callback: Callable[[dict], None] | None = None,
                 wire_protocol: str = 'responses') -> None:
        if budget is global_budget:
            raise BudgetRejected('distinct_local_and_global_budgets_required')
        self._validator=GuardedTransport(delegate,budget=budget,pricing=pricing,
            allowed_models=allowed_models,allowed_endpoint=allowed_endpoint,allowed_limits=allowed_limits)
        if any(caps['max_input_bytes']>65536 or caps['max_output_tokens']>4096 for caps in self._validator._limits.values()):
            raise BudgetRejected('elice_campaign_limits_invalid')
        if wire_protocol not in {'responses','chat_completions'}:
            raise BudgetRejected('elice_wire_protocol_not_approved')
        if wire_protocol=='chat_completions' and (not self._validator._models<=CHAT_MODELS
                or any(caps['max_output_tokens']>2000 for caps in self._validator._limits.values())):
            raise BudgetRejected('elice_chat_policy_invalid')
        self.wire_protocol=wire_protocol
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
        self._request_byte_counts: list[dict]=[]

    def snapshot(self) -> dict:
        local=self.budget.to_dict()
        global_state=self.global_budget.to_dict()
        for state in (local,global_state):
            state['accounting_basis']='billing_upper_bound'
            state['spent_upper_usd']=state['spent_usd']
            state['transport_integration']='elice_global_guard'
        reason=self._halt_reason or global_state['halt_reason'] or local['halt_reason']
        return {'budget':local,'global_budget':global_state,'halted':reason is not None,
            'halt_reason':reason,'attempts':deepcopy(self._attempts),'sent_attempts':self._sent_attempts,
            'transport_integration':'elice_global_guard','wire_protocol':self.wire_protocol,
            'request_byte_counts':deepcopy(self._request_byte_counts)}

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
            'halted':state['halted'],'halt_reason':state['halt_reason'],'wire_protocol':self.wire_protocol}
        try:
            self._callback(self._audit_callback,emitted,'audit_persistence_failed')
        except BudgetRejected:
            self._stop('audit_persistence_failed')
            raise

    def _reject(self, code: str, *, model: str | None=None) -> None:
        self._stop(code)
        self._audit({'event':'rejected','error_code':code,**({'model':model} if model else {})})

    def _reserve(self, model: str, upper: Decimal, *, request_metadata: dict | None=None) -> str:
        local_ticket=None
        try:
            local_ticket=self.budget.reserve(upper)
            global_ticket=self.global_budget.reserve(upper)
        except BudgetRejected as error:
            if local_ticket is not None:
                self.budget.settle(local_ticket,Decimal(0))
            self._reject(str(error),model=model)
            raise
        metadata={'wire_protocol':self.wire_protocol,**deepcopy(request_metadata or {})}
        self._active[global_ticket]={'local_ticket':local_ticket,'model':model,'upper':upper,'sent':False,'request_metadata':metadata}
        if request_metadata is not None:
            self._request_byte_counts.append({'attempt_id':global_ticket,**metadata})
        try:
            self._audit({'event':'reserved','attempt_id':global_ticket,'local_attempt_id':local_ticket,
                'model':model,'reserved_usd':_usd(upper),'accounting_basis':'billing_upper_bound',**metadata})
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
            'http_status':status,'sent':active['sent'],'response_id':None,**active['request_metadata']}
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
    async def _read(response: httpx.Response, maximum: int, *, captured: bytearray | None=None) -> bytes:
        if response.is_stream_consumed:
            raw=response.content
            if captured is not None:
                captured.extend(raw[:maximum])
            if len(raw)>maximum:
                raise BudgetRejected('response_byte_cap_exceeded')
            return raw
        chunks=captured if captured is not None else bytearray()
        # Own closure ourselves: aiter_raw auto-closes before usage can settle,
        # which would discard already received usage on a source-close error.
        if not isinstance(response.stream,httpx.AsyncByteStream):
            raise BudgetRejected('response_stream_invalid')
        async for chunk in response.stream:
            if len(chunks)+len(chunk)>maximum:
                chunks.extend(chunk[:maximum-len(chunks)])
                raise BudgetRejected('response_byte_cap_exceeded')
            chunks.extend(chunk)
        return bytes(chunks)

    def _error_diagnostic(self, response: httpx.Response, raw: bytes, *, complete: bool,
                          model: str, ticket: str) -> dict:
        """Build a bounded provider-only diagnostic, never a request/header dump."""
        diagnostic={'kind':'integration_error' if response.is_success else 'http_error','http_status':response.status_code,
            'model':model,'attempt_id':ticket,'captured_body_bytes':len(raw),
            'body_sha256':hashlib.sha256(raw).hexdigest(),'hash_scope':'captured_body_bytes',
            'body_truncated':not complete}
        try:
            parsed=_json(raw)
            # JSON such as 1e999 parses to infinity; never hand it to a JSON writer.
            json.dumps(parsed,ensure_ascii=False,allow_nan=False)
            diagnostic['body_kind']='json'
            trace=deepcopy(parsed) if type(parsed) is dict else {'provider_error_body':deepcopy(parsed)}
        except (ValueError,TypeError,UnicodeError,RecursionError):
            diagnostic['body_kind']='non_json'
            diagnostic['body_text']=raw.decode('utf-8',errors='replace')
            trace={}
        trace['_elice_diagnostic']=diagnostic
        settled=next((row for row in reversed(self._attempts) if row['attempt_id']==ticket),{})
        diagnostic['error_code']=settled.get('error_code')
        trace['_elice_billing']={name:deepcopy(settled.get(name)) for name in
            ('usage','cost_usd','cost_lower_usd','cost_upper_usd','cost_status')}
        trace['_elice_billing'].update(canonical_model=model,provider_model=settled.get('provider_model'),
            attempt_id=ticket,accounting_basis='billing_upper_bound')
        trace['_elice_wire']={'protocol':self.wire_protocol,**{name:settled[name] for name in
            ('canonical_request_bytes','wire_request_bytes','reservation_input_bytes') if name in settled}}
        return trace

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
            canonical_bytes=len(request.content)
            wire_request=request
            if self.wire_protocol=='chat_completions':
                translated=request_to_chat(request_data)
                wire_body=json.dumps(translated,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
                if len(wire_body)>self._validator._limits[model]['max_input_bytes']:
                    raise BudgetRejected('approved_input_cap_exceeded')
                endpoint=self._validator._endpoint
                wire_endpoint=endpoint.copy_with(path=endpoint.path[:-len('/responses')]+'/chat/completions')
                headers=request.headers.copy()
                for name in ('Content-Length','Transfer-Encoding'):
                    headers.pop(name,None)
                wire_request=httpx.Request('POST',wire_endpoint,headers=headers,content=wire_body,extensions=request.extensions)
            wire_bytes=len(wire_request.content)
            metadata={'canonical_request_bytes':canonical_bytes,'wire_request_bytes':wire_bytes,
                'reservation_input_bytes':max(canonical_bytes,wire_bytes)}
            upper=reservation_bound(model,metadata['reservation_input_bytes'],request_data['max_output_tokens'])
        except BudgetRejected as error:
            self._reject(str(error))
            raise
        except Exception:
            self._reject('elice_request_billing_invalid')
            raise BudgetRejected('elice_request_billing_invalid') from None
        ticket=self._reserve(model,upper,request_metadata=metadata)
        response=None
        error_body=bytearray()
        body_complete=False
        raw_trace_attempted=False
        primary_error: BaseException | None=None
        try:
            wire_request.headers['Accept-Encoding']='identity'
            self._active[ticket]['sent']=True
            self._sent_attempts+=1
            response=await self._delegate.handle_async_request(wire_request)
            if response.headers.get('content-encoding','identity').lower()!='identity':
                raise BudgetRejected('response_encoding_not_supported')
            content_type=response.headers.get('content-type','').split(';',1)[0].strip().lower()
            if content_type=='text/event-stream':
                raise BudgetRejected('elice_streaming_not_approved')
            raw=await self._read(response,maximum,captured=error_body)
            body_complete=True
            envelope=_json(raw)
            if type(envelope) is not dict:
                raise ValueError('response_envelope_invalid')
            # A native Messages or Chat response has different cache-total rules.
            # It must never be silently certified as a Responses usage envelope.
            if self.wire_protocol=='responses' and response.is_success and (type(envelope.get('output')) is not list
                    or envelope.get('status') not in {'completed','incomplete','failed','cancelled'}):
                raise ValueError('response_protocol_invalid')
            raw_usage=envelope.get('usage')
            if (type(raw_usage) is dict
                    and any(key in raw_usage for key in ('cache_creation_input_tokens','cache_read_input_tokens'))
                    and (self.wire_protocol=='chat_completions' or
                         (not response.is_success and type(envelope.get('output')) is not list))):
                raise ValueError('response_protocol_invalid')
            normalized=normalize_response(envelope,model)
            if self.wire_protocol=='chat_completions' and response.is_success:
                normalized=response_to_responses(normalized)
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
                trace['_elice_wire']={'protocol':self.wire_protocol,**metadata}
                try:
                    raw_trace_attempted=True
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
                diagnostic_error: BudgetRejected | None=None
                if not raw_trace_attempted and (not response.is_success or primary_error is not None):
                    # Every response follows one settlement path before this point.
                    # Capture once here so invalid/missing usage, model mismatches,
                    # and non-JSON errors remain diagnosable without changing halts.
                    try:
                        trace=self._error_diagnostic(response,bytes(error_body),complete=body_complete,
                            model=model,ticket=ticket)
                        raw_trace_attempted=True
                        self._callback(self._raw_callback,trace,'raw_response_persistence_failed')
                    except BaseException:
                        diagnostic_error=BudgetRejected('raw_response_persistence_failed')
                        self._stop('raw_response_persistence_failed')
                        try:
                            self._audit({'event':'rejected','error_code':'raw_response_persistence_failed','model':model})
                        except BudgetRejected:
                            pass
                close_failed=False
                try:
                    await response.aclose()
                except BaseException:
                    close_failed=True
                    self._stop('response_close_failed')
                    try:
                        self._audit({'event':'rejected','error_code':'response_close_failed','model':model})
                    except BudgetRejected:
                        pass
                if primary_error is None:
                    if diagnostic_error is not None:
                        raise diagnostic_error
                    if close_failed:
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
