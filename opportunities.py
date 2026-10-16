"""Sector-neutral decisions from a strict, aggregate-only public envelope.
Raw query rows remain in the existing private mission repository. Never consume
legacy exports or equate a page average with the rank of a visible query.
"""
import math
from datetime import date, datetime, timezone
from urllib.parse import urlsplit

TOP = {'schema', 'source', 'read_at', 'start_date', 'end_date', 'settled_through',
       'private_snapshot_commit', 'acquisition', 'automation_slot', 'pages'}
PAGE = {'url', 'clicks', 'impressions', 'ctr', 'position', 'commercial_intent',
        'nonbrand_visible_impressions', 'nonbrand_visible_position'}


def validate(data):
    if set(data) != TOP or data['schema'] != 1 or data['source'] != 'GSC_API':
        raise ValueError('Unsupported aggregate envelope')
    read_at = datetime.fromisoformat(data['read_at'].replace('Z', '+00:00'))
    if not read_at.tzinfo or (datetime.now(timezone.utc) - read_at).total_seconds() < -300:
        raise ValueError('Invalid read timestamp')
    if date.fromisoformat(data['start_date']) > date.fromisoformat(data['end_date']):
        raise ValueError('Invalid GSC window')
    if data['settled_through'] != 'UNKNOWN':
        date.fromisoformat(data['settled_through'])
    if data['acquisition'] not in ('INSTALLATION', 'HOSTED_SCHEDULED_TASK'):
        raise ValueError('Invalid acquisition')
    if len(data['private_snapshot_commit']) != 40 or any(c not in '0123456789abcdef' for c in data['private_snapshot_commit']):
        raise ValueError('Private snapshot missing')
    if data['automation_slot'] is not None and type(data['automation_slot']) is not int:
        raise ValueError('Invalid slot')
    if len(data['pages']) > 1000:
        raise ValueError('Unbounded input')
    for row in data['pages']:
        if set(row) != PAGE:
            raise ValueError('Private or unsupported fields refused')
        url = urlsplit(row['url'])
        if url.scheme != 'https' or url.netloc != 'fabrya.fr' or url.query or url.fragment or url.username:
            raise ValueError('Only canonical public page URLs accepted')
        if row['commercial_intent'] not in ('COMMERCIAL', 'BRAND', 'UNKNOWN'):
            raise ValueError('Invalid intent')
        for key in ('clicks', 'impressions', 'ctr', 'position', 'nonbrand_visible_impressions', 'nonbrand_visible_position'):
            value = row[key]
            if value == 'UNKNOWN' and key.startswith('nonbrand_'):
                continue
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError('Invalid metric')
        if row['clicks'] > row['impressions'] or row['ctr'] > 1:
            raise ValueError('Invalid metric relation')
    return data


def decide(data):
    validate(data)
    actions = []
    for row in data['pages']:
        if row['commercial_intent'] != 'COMMERCIAL' or row['impressions'] == 0:
            continue
        visible = row['nonbrand_visible_impressions']
        position = row['nonbrand_visible_position']
        if visible == 'UNKNOWN' or position == 'UNKNOWN' or visible == 0:
            continue
        # Ranking proxy, not a claimed probability of sale. Conversion/page quality
        # are UNKNOWN until first-party and current-page inspection exist.
        proximity = 1 / (1 + max(0, position - 10) / 10)
        coverage = min(1, visible / row['impressions'])
        score = math.log1p(visible) * proximity * coverage
        hypotheses = ['Inspect query/page intent alignment and useful evidence',
                      'Inspect internal links and commercial CTA']
        if position <= 20 and row['impressions'] >= 100:
            hypotheses.insert(0, 'Compare faithful title/snippet alternatives')
        actions.append({'url': row['url'], 'score': round(score, 6),
            'action': 'INSPECT_EXISTING_PAGE', 'hypotheses': hypotheses,
            'visible_nonbrand_position': position, 'query_coverage': round(coverage, 4),
            'sample_warning': 'LOW_SAMPLE' if visible < 30 else 'NONE',
            'page_quality': 'UNKNOWN', 'conversion_probability': 'UNKNOWN',
            'expected_effect': 'Resolve uncertainty before selecting one reversible improvement',
            'publication_authorized': False})
    return sorted(actions, key=lambda a: (-a['score'], a['url']))[:3]


def consume(state, data, run, trigger):
    validate(data)
    evidence_id = data['private_snapshot_commit']
    history = state.setdefault('gsc_observations', [])
    if not any(x['snapshot_commit'] == evidence_id for x in history):
        history.append({'snapshot_commit': evidence_id, 'read_at': data['read_at'],
            'start_date': data['start_date'], 'end_date': data['end_date'],
            'settled_through': data['settled_through'], 'acquisition': data['acquisition'],
            'automation_slot': data['automation_slot'], 'consumed_by_run': run})
    state['gsc_observations'] = history[-60:]
    actions = decide(data)
    state['seo_decision'] = {'run': run, 'trigger': trigger, 'source_snapshot': evidence_id,
        'source_read_at': data['read_at'], 'actions': actions,
        'decision': 'INSPECT' if actions else 'NO_ACTION',
        'reason': 'Current page inspection required; no proven production writer' if actions
                  else 'No commercial opportunity supported by visible nonbrand queries',
        'next_action': 'INSPECT_CURRENT_PAGE_AND_ISOLATED_SEO_WRITER',
        'first_google_organic_customer': 'NOT_YET'}
    state.setdefault('seo_decision_history', []).append(state['seo_decision'].copy())
    state['seo_decision_history'] = state['seo_decision_history'][-60:]
    return state['seo_decision']


def capability_gates(state):
    decision = state.get('seo_decision')
    if not decision:
        return {}
    result = {'OPPORTUNITY_ENGINE': {'status': 'PASS', 'reason': '',
              'evidence': {'run': decision['run'], 'snapshot': decision['source_snapshot'],
                           'decision': decision['decision']}}}
    attested = state.get('external_scheduler_attestations', {})
    observed = [x for x in state.get('gsc_observations', [])
        if x.get('acquisition') == 'HOSTED_SCHEDULED_TASK'
        and x.get('automation_slot') is not None
        and x.get('consumed_by_run') is not None
        and str(x.get('automation_slot')) in attested
        and attested[str(x.get('automation_slot'))].get('delivery') == 'HOSTED_SCHEDULED_TASK'
        and str(attested[str(x.get('automation_slot'))].get('run')) == str(x.get('consumed_by_run'))]
    result['GSC_DIRECT_READ'] = {'status': 'PASS' if observed else 'FAIL',
        'reason': '' if observed else 'REAL_READ_PERSISTED_AWAITING_HOSTED_DELIVERY_PROOF',
        'evidence': observed[-1] if observed else None}
    return result
