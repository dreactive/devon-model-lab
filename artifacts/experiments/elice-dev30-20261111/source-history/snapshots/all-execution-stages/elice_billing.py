"""Elice usage normalization and conservative accounting; no network or secrets.

Rates are user-supplied HTML, SHA256
b192518d816ae1568fe75eb28ba70091bc90d5e76caae4940cfe47352f35e095.
Gemini3.8Flash rates come from the explicit comparison in Argon's overview.
The attachment conflicts on Sol cached reads; that ambiguity remains a range.
Claude's ambiguous long-context tariff is avoided by the 65,536-byte request cap.
Canonical input includes read/write-cache tokens; output includes reasoning.
See official Responses usage and token-counting documentation recorded by root.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any

MILLION=Decimal(1_000_000)
MAX_INPUT_BYTES=65536
MAX_OUTPUT_TOKENS=4096
_RAW_RATES={
    'gpt-6.1-sol':('2','10','.10','.20','2.5','2.5'),
    'gemini-3.8-flash':('.75','3.75','0','.75','.75','.75'),
    'gemini-4-argon':('2','10','0','2','2','2'),
    'claude-haiku-5-5':('.10','.50','0','.10','.125','.20'),
    'claude-sonnet-5-5':('2','10','.10','.10','2.5','4'),
    'gpt-6-luna':('.10','.50','0','.10','.125','.125'),
}
_PROVIDERS={'gpt-6.1-sol':'openai','gpt-6-luna':'openai',
    'gemini-3.8-flash':'google','gemini-4-argon':'google',
    'claude-haiku-5-5':'anthropic','claude-sonnet-5-5':'anthropic'}
_RATE_KEYS=('input_usd_per_million','output_usd_per_million',
    'cached_read_lower_usd_per_million','cached_read_upper_usd_per_million',
    'cache_write_short_usd_per_million','cache_write_long_usd_per_million')
_CANONICAL_KEYS=('input_tokens','output_tokens','cached_input_tokens','cache_write_input_tokens',
    'reasoning_output_tokens','cache_write_short_tokens','cache_write_long_tokens')
_SHORT_TTLS=('ephemeral_5m_input_tokens','ttl_5m_tokens','ttl_30m_tokens','short_tokens')
_LONG_TTLS=('ephemeral_1h_input_tokens','ttl_1h_tokens','long_tokens')
_EXTRA_USAGE_KEYS=('tool_usage','server_tool_use','web_search_requests','web_search_tokens',
    'image_tokens','audio_tokens','image_input_tokens','image_output_tokens',
    'audio_input_tokens','audio_output_tokens','input_audio_tokens','output_audio_tokens',
    'input_image_tokens','output_image_tokens','num_tool_calls')


def rates_for(model_id: str) -> dict[str,Decimal]:
    if type(model_id) is not str or model_id not in _RAW_RATES:
        raise ValueError('elice_model_not_priced')
    return {key:Decimal(value) for key,value in zip(_RATE_KEYS,_RAW_RATES[model_id],strict=True)}


def _dict(value: Any) -> dict:
    if value is None:
        return {}
    if type(value) is not dict:
        raise ValueError('elice_usage_invalid')
    return value


def _count(values: list, *, required=False) -> int | None:
    known=[]
    for value in values:
        if value is None and not required:
            continue
        if type(value) is not int or value<0:
            raise ValueError('elice_usage_invalid')
        known.append(value)
    if not known:
        if required:
            raise ValueError('elice_usage_missing')
        return None
    if any(value!=known[0] for value in known):
        raise ValueError('elice_usage_conflicting')
    return known[0]


def _values(objects: tuple[dict,...], keys: tuple[str,...]) -> list:
    return [obj[key] for obj in objects for key in keys if key in obj]


def _empty_or_zero_tree(value: Any) -> bool:
    stack=[(value,0)]
    while stack:
        current,depth=stack.pop()
        if depth>64:
            return False
        if current is None or (type(current) is int and current==0):
            continue
        if type(current) is dict:
            stack.extend((child,depth+1) for child in current.values())
        elif type(current) is list:
            stack.extend((child,depth+1) for child in current)
        else:
            return False
    return True


def _check_extra_usage(value: dict) -> None:
    if any(key in value and not _empty_or_zero_tree(value[key]) for key in _EXTRA_USAGE_KEYS):
        raise ValueError('elice_nontext_usage_not_supported')


def normalize_usage(raw_usage: dict) -> dict[str,int | None]:
    """Normalize only explicit counts; missing details never become invented zeroes."""
    if type(raw_usage) is not dict:
        raise ValueError('elice_usage_missing')
    raw=raw_usage
    _check_extra_usage(raw)
    inp=_count(_values((raw,),('input_tokens','prompt_tokens')),required=True)
    out=_count(_values((raw,),('output_tokens','completion_tokens')),required=True)
    if 'total_tokens' in raw:
        total=_count([raw['total_tokens']],required=True)
        if total!=inp+out:
            raise ValueError('elice_usage_conflicting')
    input_details=tuple(_dict(raw.get(key)) for key in ('input_tokens_details','prompt_tokens_details'))
    output_details=tuple(_dict(raw.get(key)) for key in ('output_tokens_details','completion_tokens_details'))
    cached=_count(_values((raw,),('cached_input_tokens','cached_prompt_tokens','cache_read_input_tokens'))
        +_values(input_details,('cached_tokens','cached_prompt_tokens')))
    written=_count(_values((raw,),('cache_write_input_tokens','cache_write_prompt_tokens','cache_creation_input_tokens'))
        +_values(input_details,('cache_write_tokens','cache_creation_input_tokens')))
    reasoning=_count(_values((raw,),('reasoning_output_tokens','reasoning_tokens'))
        +_values(output_details,('reasoning_tokens',)))
    ttl_details=tuple(_dict(obj.get('cache_write_tokens_details')) for obj in input_details)
    ttl_details+=(_dict(raw.get('cache_creation')),)
    for obj in ttl_details:
        for key,value in obj.items():
            if key not in _SHORT_TTLS+_LONG_TTLS and ('ttl' in key or 'ephemeral' in key):
                if type(value) is not int or value!=0:
                    raise ValueError('elice_cache_ttl_not_supported')
    short=_count(_values((raw,),('cache_write_short_tokens',))+_values(ttl_details,_SHORT_TTLS))
    long=_count(_values((raw,),('cache_write_long_tokens',))+_values(ttl_details,_LONG_TTLS))
    minimum_written=(short or 0)+(long or 0)
    for obj in input_details+output_details:
        for key in ('audio_tokens','image_tokens'):
            if key in obj and (type(obj[key]) is not int or obj[key]!=0):
                raise ValueError('elice_nontext_usage_not_supported')
    if ((cached is not None and cached>inp) or (written is not None and written>inp)
            or (reasoning is not None and reasoning>out) or minimum_written>inp
            or (written is not None and minimum_written>written)
            or (cached or 0)+(written if written is not None else minimum_written)>inp):
        raise ValueError('elice_usage_invalid_subset')
    return {'input_tokens':inp,'output_tokens':out,'cached_input_tokens':cached,
        'cache_write_input_tokens':written,'reasoning_output_tokens':reasoning,
        'cache_write_short_tokens':short,'cache_write_long_tokens':long}


def normalize_response(envelope: dict, requested_model: str) -> dict:
    """Adapt documented aliases and usage, preserving generated output verbatim."""
    rates_for(requested_model)
    if type(envelope) is not dict:
        raise ValueError('elice_response_invalid')
    _check_extra_usage(envelope)
    if type(envelope.get('output')) is list:
        for item in envelope['output']:
            if type(item) is dict and item.get('type') not in {'message','reasoning'}:
                raise ValueError('elice_tool_output_not_supported')
    provider_model=envelope.get('model')
    aliases={requested_model,_PROVIDERS[requested_model]+'/'+requested_model}
    if type(provider_model) is not str or provider_model not in aliases:
        raise ValueError('elice_response_model_mismatch')
    tokens=normalize_usage(envelope.get('usage'))
    normalized={'input_tokens':tokens['input_tokens'],'output_tokens':tokens['output_tokens'],
        'total_tokens':tokens['input_tokens']+tokens['output_tokens']}
    input_details={}
    if tokens['cached_input_tokens'] is not None:
        input_details['cached_tokens']=tokens['cached_input_tokens']
    if tokens['cache_write_input_tokens'] is not None:
        input_details['cache_write_tokens']=tokens['cache_write_input_tokens']
    if input_details:
        normalized['input_tokens_details']=input_details
    if tokens['reasoning_output_tokens'] is not None:
        normalized['output_tokens_details']={'reasoning_tokens':tokens['reasoning_output_tokens']}
    result=deepcopy(envelope)
    result['provider_model']=provider_model
    result['model']=requested_model
    result['usage']=normalized
    return result


def _usd(value: Decimal) -> str:
    rendered=format(value,'f')
    return rendered.rstrip('0').rstrip('.') if '.' in rendered else rendered


def cost_bounds(model_id: str, normalized_usage: dict) -> dict:
    """Return exact cost when possible and a safe upper debit otherwise.

    Cache reads, writes and uncached inputs partition total input; reasoning is
    already part of total output. Ambiguous/missing cache counters produce bounds,
    never a zero-cost assumption. These are supplied-tariff calculations, not an
    assertion about a provider invoice.
    """
    rates=rates_for(model_id)
    tokens=normalize_usage(normalized_usage)
    inp,out=tokens['input_tokens'],tokens['output_tokens']
    if inp>MAX_INPUT_BYTES or out>MAX_OUTPUT_TOKENS:
        raise ValueError('elice_usage_exceeds_small_request_caps')
    base=rates['input_usd_per_million']
    read_low=rates['cached_read_lower_usd_per_million']
    read_high=rates['cached_read_upper_usd_per_million']
    write_short=rates['cache_write_short_usd_per_million']
    write_long=rates['cache_write_long_usd_per_million']
    write_low,write_high=min(write_short,write_long),max(write_short,write_long)
    cached=tokens['cached_input_tokens']
    written=tokens['cache_write_input_tokens']
    short=tokens['cache_write_short_tokens'] or 0
    long=tokens['cache_write_long_tokens'] or 0
    lower=upper=Decimal(short)*write_short+Decimal(long)*write_long
    if written is not None:
        uncertain_written=written-short-long
        lower+=Decimal(uncertain_written)*write_low
        upper+=Decimal(uncertain_written)*write_high
        remaining=inp-written
        if cached is not None:
            lower+=Decimal(cached)*read_low+Decimal(remaining-cached)*base
            upper+=Decimal(cached)*read_high+Decimal(remaining-cached)*base
        else:
            lower+=Decimal(remaining)*min(base,read_low)
            upper+=Decimal(remaining)*max(base,read_high)
    else:
        remaining=inp-short-long
        if cached is not None:
            lower+=Decimal(cached)*read_low+Decimal(remaining-cached)*min(base,write_low)
            upper+=Decimal(cached)*read_high+Decimal(remaining-cached)*max(base,write_high)
        else:
            lower+=Decimal(remaining)*min(base,read_low,write_low)
            upper+=Decimal(remaining)*max(base,read_high,write_high)
    output_cost=Decimal(out)*rates['output_usd_per_million']
    lower=(lower+output_cost)/MILLION
    upper=(upper+output_cost)/MILLION
    if lower>upper:
        raise ValueError('elice_cost_bounds_invalid')
    exact=lower==upper
    return {'cost_usd':_usd(lower) if exact else None,'cost_lower_usd':_usd(lower),
        'cost_upper_usd':_usd(upper),'cost_status':'confirmed' if exact else 'bounded','tokens':tokens}


def reservation_bound(model_id: str, input_bytes: int, max_output_tokens: int) -> Decimal:
    """Reserve the largest supplied tariff against bytes and output-token cap."""
    rates=rates_for(model_id)
    if (type(input_bytes) is not int or not 0<input_bytes<=MAX_INPUT_BYTES
            or type(max_output_tokens) is not int or not 0<max_output_tokens<=MAX_OUTPUT_TOKENS):
        raise ValueError('elice_request_caps_invalid')
    input_rate=max(rates['input_usd_per_million'],rates['cached_read_upper_usd_per_million'],
        rates['cache_write_short_usd_per_million'],rates['cache_write_long_usd_per_million'])
    return (Decimal(input_bytes)*input_rate+Decimal(max_output_tokens)*rates['output_usd_per_million'])/MILLION
