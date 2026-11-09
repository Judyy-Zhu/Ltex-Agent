"""Guard the experiment against cache, reasoning and event replay double counts."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from usage_accounting import normalize_raw, normalize_pi, summarize


class UsageAccountingTests(unittest.TestCase):
    def test_cache_and_reasoning_are_not_extra_tokens(self):
        raw=normalize_raw({'prompt_tokens':1000,'completion_tokens':200,'total_tokens':1200,
                           'prompt_tokens_details':{'cached_tokens':700},
                           'completion_tokens_details':{'reasoning_tokens':80}})
        pi=normalize_pi({'input':300,'cacheRead':700,'cacheWrite':0,'output':200,'reasoning':80},usage_observed=True)
        self.assertEqual(raw['token_total'],1200)
        self.assertEqual(raw['input_uncached'],300)
        self.assertEqual(raw['token_total'],pi['token_total'])

    def test_observed_paratera_cached_tool_roundtrip(self):
        raw=normalize_raw({'prompt_tokens':367,'completion_tokens':1,'total_tokens':368,
                           'prompt_tokens_details':{'cached_tokens':256},
                           'completion_tokens_details':{'reasoning_tokens':0}})
        self.assertEqual(raw['input_uncached'],111)
        self.assertEqual(raw['token_total'],368)

    def test_cache_writes_stay_in_non_hit_input_but_not_extra_total(self):
        raw=normalize_raw({'prompt_tokens':100,'completion_tokens':2,
                           'prompt_tokens_details':{'cached_tokens':20,'cache_write_tokens':10}})
        pi=normalize_pi({'input':70,'cacheRead':20,'cacheWrite':10,'output':2},usage_observed=True)
        self.assertEqual(raw['input_uncached'],80)
        self.assertEqual(raw['input_uncached'],pi['input_uncached'])
        self.assertEqual(pi['token_total'],102)

    def test_missing_usage_is_not_free(self):
        initialized=normalize_pi({'input':0,'output':0,'cacheRead':0,'cacheWrite':0},usage_observed=False)
        result=summarize([{'attempt_id':'known','usage':normalize_raw({'prompt_tokens':10,'completion_tokens':2})},
                          {'attempt_id':'network-retry','usage':initialized}])
        total=result['fields']['token_total']
        self.assertIsNone(total['value'])
        self.assertEqual(total['known_subtotal'],12)
        self.assertEqual(total['coverage'],.5)

    def test_replayed_event_is_not_another_request_but_retry_is(self):
        usage=normalize_raw({'prompt_tokens':10,'completion_tokens':2})
        a={'attempt_id':'a','usage':usage}
        result=summarize([a,a,{'attempt_id':'b','usage':usage}])
        self.assertEqual(result['request_attempts'],2)
        self.assertEqual(result['fields']['token_total']['value'],24)

    def test_conflicting_sources_cannot_be_added(self):
        with self.assertRaises(ValueError):
            summarize([{'attempt_id':'a','usage':normalize_raw({'prompt_tokens':10,'completion_tokens':2})},
                       {'attempt_id':'a','usage':normalize_raw({'prompt_tokens':20,'completion_tokens':2})}])

    def test_inconsistent_provider_counts_are_exposed(self):
        result=normalize_raw({'prompt_tokens':10,'completion_tokens':2,'total_tokens':99})
        self.assertTrue(result['total_discrepancy'])
        with self.assertRaises(ValueError):
            normalize_raw({'prompt_tokens':10,'completion_tokens':2,'prompt_tokens_details':{'cached_tokens':11}})


if __name__=='__main__': unittest.main()
