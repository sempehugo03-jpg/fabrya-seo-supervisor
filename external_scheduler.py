"""Wake transport only. The original Supervisor owns every SEO decision."""
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

AUTOMATION_ID = '6ac6c67c278081918b6a6d8846594c72'
PROBE_ID = 'external-runtime-verification-20261011'


def wake_metadata():
    if os.environ.get('GITHUB_EVENT_NAME') != 'push':
        return None
    if os.environ.get('GITHUB_REF') != 'refs/heads/seo-wake':
        raise RuntimeError('Interactive/source push is not a periodic wake')
    value = json.loads(Path(os.environ['SEO_WAKE_FILE']).read_text())
    if (set(value) != {'schema', 'automation_id', 'slot', 'issued_at', 'source_commit'}
            or value['schema'] != 1 or value['automation_id'] != AUTOMATION_ID
            or not re.fullmatch(r'[0-9a-f]{40}', value['source_commit'])
            or value['source_commit'] != os.environ['SEO_SOURCE_COMMIT']
            or not isinstance(value['slot'], int)
            or not isinstance(value['issued_at'], (int, float))
            or int(value['issued_at'] // 3600) != value['slot']
            or not 0 <= time.time() - value['issued_at'] <= 1800):
        raise RuntimeError('Invalid, stale or mismatched external wake')
    return value


def verified_external_runs(state, current_commit, runs, jobs, receipts):
    """Marker is NOT proof. Require separately audited hosted task delivery."""
    attestations = state.get('external_scheduler_attestations', {})
    verified = []
    for run in runs:
        receipt = receipts.get(str(run['id']))
        wake = receipt and receipt.get('wake')
        audit = wake and attestations.get(str(wake['slot']))
        if not (wake and audit and run.get('event') == 'push'
                and run.get('head_branch') == 'seo-wake'
                and run.get('status') == 'completed' and run.get('conclusion') == 'success'
                and run.get('run_attempt', 1) == 1
                and receipt.get('commit') == current_commit
                and audit.get('automation_id') == AUTOMATION_ID
                and audit.get('run') == str(run['id'])
                and audit.get('wake_commit') == run.get('head_sha')
                and audit.get('delivery') == 'HOSTED_SCHEDULED_TASK'
                and audit.get('observed_last_run_time')
                and audit.get('completed_tasks_unchanged') is True):
            continue
        try:
            delivered_at = datetime.fromisoformat(audit['observed_last_run_time'].replace('Z', '+00:00')).timestamp()
            if int(delivered_at // 3600) != wake['slot'] or not 0 <= wake['issued_at'] - delivered_at <= 1800:
                continue
        except (ValueError, TypeError):
            continue
        steps = {s.get('name'): s.get('conclusion') for j in jobs.get(str(run['id']), [])
                 if j.get('conclusion') == 'success' for s in j.get('steps', [])}
        if (steps.get('Validate isolated executor') == 'success'
                and steps.get('Prepare useful SEO reviews and recover checkpoints') == 'success'):
            verified.append(run)
    return verified
