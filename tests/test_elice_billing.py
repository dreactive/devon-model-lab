"""Offline tariff and usage checks; no provider, key or environment access."""
from decimal import Decimal
import copy
import importlib
import unittest


class EliceBillingTests(unittest.TestCase):
    def module(self):
        return importlib.import_module('elice_billing')

    def test_all_six_supplied_base_rates_are_decimal(self):
        b=self.module()
        expected={'gpt-6.1-sol':('2','10'),'gemini-3.8-flash':('.75','3.75'),
            'gemini-4-argon':('2','10'),'claude-haiku-5-5':('.1','.5'),
            'claude-sonnet-5-5':('2','10'),'gpt-6-luna':('.1','.5')}
        for model,(inp,out) in expected.items():
            with self.subTest(model=model):
                rates=b.rates_for(model)
                self.assertEqual(rates['input_usd_per_million'],Decimal(inp))
                self.assertEqual(rates['output_usd_per_million'],Decimal(out))
                self.assertIs(type(rates['input_usd_per_million']),Decimal)

    def test_alias_usage_normalizes_and_preserves_missing_detail_as_none(self):
        b=self.module()
        x=b.normalize_usage({'prompt_tokens':100,'completion_tokens':20,'total_tokens':120,
            'cached_prompt_tokens':10,'completion_tokens_details':{'reasoning_tokens':5}})
        self.assertEqual(x['input_tokens'],100)
        self.assertEqual(x['output_tokens'],20)
        self.assertEqual(x['cached_input_tokens'],10)
        self.assertEqual(x['reasoning_output_tokens'],5)
        self.assertIsNone(x['cache_write_input_tokens'])

    def test_observed_haiku_top_level_cache_write_tokens_is_an_explicit_subset(self):
        b=self.module()
        raw={'prompt_tokens':12120,'completion_tokens':1011,'cached_prompt_tokens':0,'cache_write_tokens':9677}
        saved=copy.deepcopy(raw);tokens=b.normalize_usage(raw)
        self.assertEqual(tokens['input_tokens'],12120)
        self.assertEqual(tokens['output_tokens'],1011)
        self.assertEqual(tokens['cached_input_tokens'],0)
        self.assertEqual(tokens['cache_write_input_tokens'],9677)
        result=b.cost_bounds('claude-haiku-5-5',tokens)
        base=Decimal(12120-9677)*Decimal('.1')+Decimal(1011)*Decimal('.5')
        self.assertEqual(Decimal(result['cost_lower_usd']),(base+Decimal(9677)*Decimal('.125'))/1000000)
        self.assertEqual(Decimal(result['cost_upper_usd']),(base+Decimal(9677)*Decimal('.2'))/1000000)
        self.assertEqual(result['cost_status'],'bounded');self.assertIsNone(result['cost_usd'])
        canonical=b.normalize_response({'id':'offline-observed-shape','model':'claude-haiku-5-5','usage':raw},'claude-haiku-5-5')
        self.assertEqual(canonical['usage']['input_tokens_details']['cache_write_tokens'],9677)
        self.assertEqual(raw,saved)

    def test_top_level_cache_write_tokens_alias_conflicts_are_rejected(self):
        b=self.module()
        alternatives=[{name:9676} for name in ('cache_write_input_tokens','cache_write_prompt_tokens','cache_creation_input_tokens')]
        alternatives+=[{'input_tokens_details':{'cache_write_tokens':9676}},
            {'prompt_tokens_details':{'cache_write_tokens':9676}}]
        for alternative in alternatives:
            with self.subTest(alternative=alternative):
                raw={'input_tokens':12120,'output_tokens':1011,'cache_write_tokens':9677,**alternative}
                with self.assertRaisesRegex(ValueError,'elice_usage_conflicting'):b.normalize_usage(raw)
        same={'input_tokens':12120,'output_tokens':1011,'cache_write_tokens':9677,
            'cache_write_prompt_tokens':9677,'input_tokens_details':{'cache_write_tokens':9677}}
        self.assertEqual(b.normalize_usage(same)['cache_write_input_tokens'],9677)

    def test_top_level_cache_write_tokens_invalid_counts_and_partitions_are_rejected(self):
        b=self.module()
        for value in (True,False,-1,1.5,12121):
            with self.subTest(value=value),self.assertRaises(ValueError):
                b.normalize_usage({'input_tokens':12120,'output_tokens':1011,'cache_write_tokens':value})
        for extra in ({'cached_prompt_tokens':2444},{'cache_write_short_tokens':9678}):
            with self.subTest(extra=extra),self.assertRaisesRegex(ValueError,'elice_usage_invalid_subset'):
                b.normalize_usage({'input_tokens':12120,'output_tokens':1011,'cache_write_tokens':9677,**extra})
        tokens=b.normalize_usage({'input_tokens':12120,'output_tokens':1011,'cache_write_tokens':0})
        self.assertEqual(tokens['cache_write_input_tokens'],0)

    def test_top_level_cache_write_tokens_and_short_ttl_are_not_double_counted(self):
        b=self.module()
        raw={'input_tokens':12120,'output_tokens':1011,'cached_prompt_tokens':0,'cache_write_tokens':9677,
            'input_tokens_details':{'cache_write_tokens_details':{'ephemeral_5m_input_tokens':9677}}}
        tokens=b.normalize_usage(raw)
        result=b.cost_bounds('claude-haiku-5-5',tokens)
        expected=(Decimal(12120-9677)*Decimal('.1')+Decimal(9677)*Decimal('.125')+Decimal(1011)*Decimal('.5'))/1000000
        self.assertEqual(result['cost_status'],'confirmed')
        self.assertEqual(Decimal(result['cost_usd']),expected)
        self.assertEqual(Decimal(result['cost_upper_usd']),expected)

    def test_conflicting_invalid_and_missing_counts_are_rejected(self):
        b=self.module()
        for usage in ({'output_tokens':1},{'input_tokens':None,'output_tokens':1},
            {'input_tokens':True,'output_tokens':1},{'input_tokens':-1,'output_tokens':1},
            {'input_tokens':1.5,'output_tokens':1},{'input_tokens':float('nan'),'output_tokens':1},
            {'input_tokens':100,'prompt_tokens':101,'output_tokens':20},
            {'input_tokens':100,'output_tokens':20,'total_tokens':119},
            {'input_tokens':100,'output_tokens':20,'input_tokens_details':{'cached_tokens':101}},
            {'input_tokens':100,'output_tokens':20,'output_tokens_details':{'reasoning_tokens':21}},
            {'input_tokens':100,'output_tokens':20,'cached_prompt_tokens':60,'cache_creation_input_tokens':41}):
            with self.subTest(usage=usage), self.assertRaises(ValueError):
                b.normalize_usage(usage)

    def test_gpt_cache_write_and_reasoning_are_not_double_counted(self):
        b=self.module()
        tokens=b.normalize_usage({'input_tokens':1000,'output_tokens':200,
            'input_tokens_details':{'cached_tokens':0,'cache_write_tokens':400},
            'output_tokens_details':{'reasoning_tokens':150}})
        x=b.cost_bounds('gpt-6.1-sol',tokens)
        expected=(Decimal(600)*2+Decimal(400)*Decimal('2.5')+Decimal(200)*10)/1000000
        self.assertEqual(Decimal(x['cost_usd']),expected)
        self.assertEqual(x['cost_status'],'confirmed')

    def test_claude_short_long_write_breakdown_is_exact(self):
        b=self.module()
        tokens=b.normalize_usage({'input_tokens':1000,'output_tokens':200,
            'input_tokens_details':{'cached_tokens':100,'cache_write_tokens':500,
                'cache_write_tokens_details':{'ephemeral_5m_input_tokens':300,'ephemeral_1h_input_tokens':200}}})
        x=b.cost_bounds('claude-sonnet-5-5',tokens)
        expected=(Decimal(400)*2+Decimal(100)*Decimal('.1')+Decimal(300)*Decimal('2.5')+Decimal(200)*4+Decimal(200)*10)/1000000
        self.assertEqual(Decimal(x['cost_usd']),expected)
        self.assertEqual(x['cost_status'],'confirmed')

    def test_unknown_cache_details_are_bounded_and_never_called_exact(self):
        b=self.module()
        tokens=b.normalize_usage({'input_tokens':1000,'output_tokens':100})
        x=b.cost_bounds('claude-sonnet-5-5',tokens)
        self.assertIsNone(x['cost_usd'])
        self.assertEqual(x['cost_status'],'bounded')
        self.assertEqual(Decimal(x['cost_lower_usd']),Decimal('0.0011'))
        self.assertEqual(Decimal(x['cost_upper_usd']),Decimal('0.005'))

    def test_known_write_total_unknown_ttl_uses_125_to_2_bounds(self):
        b=self.module()
        tokens=b.normalize_usage({'input_tokens':1000,'output_tokens':0,
            'input_tokens_details':{'cached_tokens':0,'cache_write_tokens':1000}})
        x=b.cost_bounds('claude-haiku-5-5',tokens)
        self.assertEqual(Decimal(x['cost_lower_usd']),Decimal('.000125'))
        self.assertEqual(Decimal(x['cost_upper_usd']),Decimal('.0002'))
        self.assertIsNone(x['cost_usd'])

    def test_gpt_cached_read_price_conflict_remains_a_range(self):
        b=self.module()
        x=b.cost_bounds('gpt-6.1-sol',b.normalize_usage({'input_tokens':1000,'output_tokens':0,
            'input_tokens_details':{'cached_tokens':1000,'cache_write_tokens':0}}))
        self.assertEqual(Decimal(x['cost_lower_usd']),Decimal('.0001'))
        self.assertEqual(Decimal(x['cost_upper_usd']),Decimal('.0002'))
        self.assertIsNone(x['cost_usd'])

    def test_no_cache_write_premium_for_gemini(self):
        b=self.module()
        x=b.cost_bounds('gemini-3.8-flash',b.normalize_usage({'input_tokens':1000,'output_tokens':100,
            'input_tokens_details':{'cached_tokens':0}}))
        self.assertEqual(Decimal(x['cost_usd']),Decimal('.001125'))

    def test_response_model_alias_normalizes_without_changing_semantic_output(self):
        b=self.module()
        raw={'id':'fake-1','model':'openai/gpt-6-luna','output':[{'type':'message','content':[{'type':'output_text','text':'{"x":1}'}]}],
            'usage':{'prompt_tokens':100,'completion_tokens':20,'cached_prompt_tokens':0}}
        before=copy.deepcopy(raw)
        result=b.normalize_response(raw,'gpt-6-luna')
        self.assertEqual(raw,before)
        self.assertEqual(result['provider_model'],'openai/gpt-6-luna')
        self.assertEqual(result['model'],'gpt-6-luna')
        self.assertEqual(result['output'],raw['output'])
        self.assertEqual(result['usage']['input_tokens'],100)
        self.assertEqual(result['usage']['output_tokens'],20)
        with self.assertRaises(ValueError): b.normalize_response(raw,'gpt-6.1-sol')

    def test_ttl_partial_and_unknown_positive_ttl_are_fail_closed(self):
        b=self.module()
        with self.assertRaises(ValueError):
            b.normalize_usage({'input_tokens':100,'output_tokens':0,'input_tokens_details':{
                'cache_write_tokens':5,'cache_write_tokens_details':{'ephemeral_5m_input_tokens':6}}})
        with self.assertRaises(ValueError):
            b.normalize_usage({'input_tokens':100,'output_tokens':0,'input_tokens_details':{
                'cache_write_tokens':5,'cache_write_tokens_details':{'ttl_12h_tokens':5}}})

    def test_reservation_uses_write_premium_and_strict_text_caps(self):
        b=self.module()
        x=b.reservation_bound('claude-sonnet-5-5',10000,4096)
        self.assertEqual(x,(Decimal(10000)*4+Decimal(4096)*10)/1000000)
        for inp,out in [(65537,1),(100,4097),(True,1),(100,0)]:
            with self.subTest(inp=inp,out=out),self.assertRaises(ValueError): b.reservation_bound('gpt-6-luna',inp,out)

    def test_ambiguous_mixed_short_ttl_formats_are_rejected(self):
        b=self.module()
        # Different providers' TTL vocabularies must not be silently merged.
        with self.assertRaises(ValueError):
            b.normalize_usage({'input_tokens':1000,'output_tokens':100,
                'input_tokens_details':{'cached_tokens':0,'cache_write_tokens':300,
                    'cache_write_tokens_details':{'ttl_5m_tokens':100,'ttl_30m_tokens':200,'ttl_1h_tokens':0}}})

    def test_bounds_contain_all_admissible_cache_partitions(self):
        b=self.module()
        for partial in ({},{'cached_input_tokens':2},{'cache_write_input_tokens':3},
            {'cache_write_input_tokens':3,'cache_write_short_tokens':1},
            {'cache_write_short_tokens':1,'cache_write_long_tokens':2}):
            observed={'input_tokens':8,'output_tokens':2,**partial}
            bound=b.cost_bounds('claude-sonnet-5-5',b.normalize_usage(observed))
            admissible=0
            for cached in range(9):
                for short in range(9-cached):
                    for long in range(9-cached-short):
                        written=short+long
                        facts={'cached_input_tokens':cached,'cache_write_input_tokens':written,
                               'cache_write_short_tokens':short,'cache_write_long_tokens':long}
                        if any(facts[key]!=value for key,value in partial.items()): continue
                        actual=(Decimal(8-cached-short-long)*2+Decimal(cached)*Decimal('.1')
                            +Decimal(short)*Decimal('2.5')+Decimal(long)*4+Decimal(2)*10)/1000000
                        self.assertLessEqual(Decimal(bound['cost_lower_usd']),actual)
                        self.assertGreaterEqual(Decimal(bound['cost_upper_usd']),actual)
                        admissible+=1
            self.assertGreater(admissible,0)

    def test_reported_usage_beyond_small_request_tariff_is_rejected(self):
        b=self.module()
        for inp,out in [(100001,100),(100,4097)]:
            with self.assertRaises(ValueError): b.cost_bounds('claude-haiku-5-5',b.normalize_usage({'input_tokens':inp,'output_tokens':out}))

    def test_nontext_or_server_tool_cost_counters_are_rejected(self):
        b=self.module()
        for extra in ({'tool_usage':{'web_search':{'num_requests':1}}},
            {'server_tool_use':{'web_search_requests':1}}, {'web_search_requests':1},
            {'audio_tokens':3},{'image_tokens':1},{'input_audio_tokens':1},
            {'tool_usage':{'web_search':{'num_requests':True}}}):
            with self.subTest(extra=extra),self.assertRaises(ValueError):
                b.normalize_usage({'input_tokens':100,'output_tokens':1,**extra})
        x=b.normalize_usage({'input_tokens':100,'output_tokens':1,
            'tool_usage':{'web_search':{'num_requests':0}},'server_tool_use':{},'audio_tokens':0})
        self.assertEqual(x['input_tokens'],100)
