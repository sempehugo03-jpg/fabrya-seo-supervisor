"""Fail before public GitHub transmission; never log rejected contents."""
import json
import re

FORBIDDEN = {'query', 'queries', 'exact_query_checks', 'session_id', 'sessionid',
             'email', 'customer_email', 'customer_id', 'stripe_customer_id',
             'payment_intent', 'client_secret', 'token', 'access_token',
             'refresh_token', 'private_key', 'authorization', 'cookie'}
PATTERN = re.compile(r'(?i)(?:\bgh[pousr]_[a-z0-9]{20,}|\bgithub_pat_[a-z0-9_]{20,}|\bsk-[a-z0-9_-]{20,}|-----BEGIN (?:RSA )?PRIVATE KEY-----|[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})')


def check_public_text(text):
    if PATTERN.search(text):
        raise ValueError('PRIVACY_GATE_REJECTED_SECRET_OR_CONTACT')
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return
    def walk(item):
        if isinstance(item, dict):
            if any(str(k).lower() in FORBIDDEN for k in item):
                raise ValueError('PRIVACY_GATE_REJECTED_PRIVATE_FIELDS')
            # Raw GSC rows use keys[]; aggregate envelope never needs them.
            if 'keys' in item and ('impressions' in item or 'clicks' in item):
                raise ValueError('PRIVACY_GATE_REJECTED_RAW_GSC')
            for child in item.values(): walk(child)
        elif isinstance(item, list):
            for child in item: walk(child)
    walk(value)
