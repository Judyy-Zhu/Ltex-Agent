"""Normalize reported usage without double counting caches, reasoning or replays.

The collector stores raw records separately and supplies one final usage per
actual request attempt. These helpers never estimate missing provider usage.
"""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Any

FIELDS = ('input_total', 'input_uncached', 'cache_read', 'cache_write',
          'output_total', 'reasoning_subset', 'token_total')


def _count(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError('Reported token count must be a nonnegative integer or unknown')
    return value


def normalize_raw(usage: Mapping[str, Any] | None) -> dict[str, Any]:
    """Normalize this experiment's OpenAI-compatible raw usage contract."""
    u = usage or {}
    prompt_details = u.get('prompt_tokens_details') or {}
    completion_details = u.get('completion_tokens_details') or {}
    p = _count(u.get('prompt_tokens'))
    c = _count(u.get('completion_tokens'))
    read = _count(prompt_details.get('cached_tokens', u.get('prompt_cache_hit_tokens', u.get('cached_tokens'))))
    write = _count(prompt_details.get('cache_write_tokens'))
    reasoning = _count(completion_details.get('reasoning_tokens'))
    # "Uncached" here means not served from cache-read; cache writes are
    # included in this figure, and also reported as a separate breakdown.
    uncached = p-read if p is not None and read is not None else None
    if uncached is not None and uncached < 0:
        raise ValueError('Cache reads exceed reported total input')
    if write is not None and uncached is not None:
        if uncached-write < 0:
            raise ValueError('Cache reads and writes exceed reported total input')
    if reasoning is not None and c is not None and reasoning > c:
        raise ValueError('Reasoning subset exceeds output under the selected contract')
    reported_total = _count(u.get('total_tokens'))
    total = p+c if p is not None and c is not None else None
    return dict(input_total=p, input_uncached=uncached, cache_read=read,
                cache_write=write, output_total=c, reasoning_subset=reasoning,
                token_total=total, source='provider_raw',
                reported_total_tokens=reported_total,
                total_discrepancy=(reported_total != total) if reported_total is not None and total is not None else None)


def normalize_pi(usage: Mapping[str, Any] | None, *, usage_observed: bool) -> dict[str, Any]:
    """Normalize current Pi counts only when collection established real usage."""
    if not usage_observed:
        return {**dict.fromkeys(FIELDS), 'source':'pi_usage_unconfirmed'}
    u = usage or {}
    fresh, read, write, output, reasoning = (
        _count(u.get(k)) for k in ('input','cacheRead','cacheWrite','output','reasoning'))
    p = fresh+read+write if None not in (fresh,read,write) else None
    total = p+output if p is not None and output is not None else None
    if reasoning is not None and output is not None and reasoning > output:
        raise ValueError('Reasoning subset exceeds output')
    uncached = fresh+write if fresh is not None and write is not None else None
    return dict(input_total=p,input_uncached=uncached,cache_read=read,cache_write=write,
                output_total=output,reasoning_subset=reasoning,token_total=total,source='pi_normalized')


def summarize(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Sum one selected usage source per request; identical replays are idempotent."""
    unique = {}
    for record in records:
        attempt_id = record['attempt_id']
        if not isinstance(attempt_id,str) or not attempt_id:
            raise ValueError('Collector must assign a stable, nonempty request-attempt ID')
        if attempt_id in unique and unique[attempt_id] != record['usage']:
            raise ValueError('Conflicting usage for one attempt; select raw or Pi before aggregation')
        unique[attempt_id] = record['usage']
    result: dict[str, Any] = {'request_attempts':len(unique), 'fields':{}}
    for field in FIELDS:
        values = [_count(u.get(field)) for u in unique.values()]
        known = [v for v in values if v is not None]
        complete = len(known)==len(values)
        result['fields'][field] = {
            'value':sum(known) if complete else None,
            'known_subtotal':sum(known), 'known_requests':len(known),
            'missing_requests':len(values)-len(known),
            'coverage':len(known)/len(values) if values else None,
        }
    return result
