"""Public control metadata only; no search, acquisition or customer payloads."""

from external_scheduler import verified_external_runs, PROBE_ID

GATES = (
    'SEO_RUNTIME_AUTONOMOUS', 'GSC_DIRECT_READ', 'OPPORTUNITY_ENGINE',
    'STAGING_EXECUTOR', 'SEO_QA', 'SAFE_AUTO_PUBLISH', 'MEASUREMENT_LOOP',
    'AUTO_ROLLBACK', 'ATTRIBUTION_PIPELINE', 'WATCHDOG_RECOVERY', 'PRIVACY_GATE',
)


def terminal_state(gates, human_blocker=None):
    if human_blocker:
        return 'BLOCKED_HUMAN'
    if set(gates) == set(GATES) and all(
        gates[name].get('status') == 'PASS' and gates[name].get('evidence')
        for name in GATES
    ):
        return 'COMPLETE'
    return 'RUNNING'


def reconcile(state, current_commit, runs, jobs_by_run):
    gates = {name: {'status': 'FAIL', 'reason': 'CAPABILITY_NOT_INSTALLED_OR_PROVEN',
                    'evidence': None} for name in GATES}
    receipts = {str(item['run']): item for item in state.get('cycle_receipts', [])
                if item.get('status') == 'COMPLETED' and item.get('commit') == current_commit}
    def verified(run, trigger, test_step, execution_step):
        if (run.get('event') != trigger or run.get('status') != 'completed'
            or run.get('conclusion') != 'success' or run.get('head_sha') != current_commit
            or run.get('head_branch') != 'main' or run.get('run_attempt', 1) != 1
            or str(run['id']) not in receipts):
            return False
        jobs = jobs_by_run.get(str(run['id']), [])
        steps = {step.get('name'): step.get('conclusion')
                 for job in jobs if job.get('conclusion') == 'success'
                 for step in job.get('steps', [])}
        return steps.get(test_step) == 'success' and steps.get(execution_step) == 'success'
    schedules = [run for run in runs if run.get('event') == 'schedule']
    successful = [run for run in schedules if verified(run, 'schedule',
        'Validate isolated executor', 'Prepare useful SEO reviews and recover checkpoints')]
    if successful:
        gates['SEO_RUNTIME_AUTONOMOUS'] = {'status': 'PASS', 'reason': '',
            'evidence': {'run': successful[0]['id'], 'commit': current_commit}}
    else:
        gates['SEO_RUNTIME_AUTONOMOUS']['reason'] = 'NO_VERIFIED_SUCCESSFUL_SCHEDULE_ON_CURRENT_COMMIT'
    external = verified_external_runs(state, current_commit, runs, jobs_by_run, receipts)
    probe = state.get('probes', {}).get('scheduled-runtime-verification-20261010')
    recovery = None
    if probe:
        for event in reversed(state.get('events', [])):
            if (event.get('kind') != 'RECOVERED' or event.get('old_owner') != probe.get('owner')
                or event.get('old_trigger') != 'schedule' or event.get('trigger') != 'workflow_run'
                or event.get('previous_conclusion') != 'failure'):
                continue
            recovery_run = next((run for run in runs
                if str(run['id']) == event.get('by', '').split(':')[0]), None)
            if recovery_run and verified(recovery_run, 'workflow_run',
                'Verify recovery executor', 'Recover same SEO state and unfinished useful task'):
                recovery = {'run': recovery_run['id'], 'commit': current_commit,
                            'completed_at': recovery_run.get('updated_at')}
                if any(run.get('created_at', '') > (recovery_run.get('updated_at') or '')
                       for run in successful):
                    gates['WATCHDOG_RECOVERY'] = {'status': 'PASS', 'reason': '',
                        'evidence': recovery}
                break
    gates['WATCHDOG_RECOVERY']['reason'] = (
        gates['WATCHDOG_RECOVERY']['reason'] or '')
    external_probe = state.get('probes', {}).get(PROBE_ID)
    external_recovery = None
    if external_probe:
        for event in reversed(state.get('events', [])):
            if (event.get('kind') != 'RECOVERED' or event.get('old_owner') != external_probe.get('owner')
                or event.get('old_trigger') != 'push' or event.get('trigger') != 'workflow_run'
                or event.get('previous_conclusion') != 'failure'):
                continue
            rr = next((r for r in runs if str(r['id']) == event.get('by', '').split(':')[0]), None)
            if rr and verified(rr, 'workflow_run', 'Verify recovery executor',
                    'Recover same SEO state and unfinished useful task'):
                external_recovery = {'run': rr['id'], 'commit': current_commit, 'completed_at': rr.get('updated_at')}
                break
    following = external_recovery and any(r.get('created_at', '') > external_recovery['completed_at'] for r in external)
    distinct_slots = {receipts[str(r['id'])]['wake']['slot'] for r in external}
    if len(distinct_slots) >= 2 and following:
        proof = {'scheduler': 'HOSTED_AUTOMATION', 'runs': [r['id'] for r in external],
                 'commit': current_commit, 'recovery': external_recovery}
        gates['SEO_RUNTIME_AUTONOMOUS'] = {'status': 'PASS', 'reason': '', 'evidence': proof}
        gates['WATCHDOG_RECOVERY'] = {'status': 'PASS', 'reason': '', 'evidence': external_recovery}
        recovery = external_recovery
    elif state.get('external_scheduler_config'):
        gates['SEO_RUNTIME_AUTONOMOUS'] = {'status': 'FAIL', 'reason': 'EXTERNAL_DELIVERY_RECOVERY_AND_FOLLOWING_WAKE_NOT_YET_PROVEN', 'evidence': None}
        gates['WATCHDOG_RECOVERY'] = {'status': 'FAIL', 'reason': 'EXTERNAL_CRASH_RECOVERY_NOT_YET_PROVEN', 'evidence': None}
    status = {
        'current_commit': current_commit,
        'last_schedule_run': schedules[0]['id'] if schedules else None,
        'last_successful_schedule': successful[0]['id'] if successful else None,
        'last_watchdog_recovery': recovery,
        'last_external_wake': external[0]['id'] if external else None,
        'scheduler': state.get('external_scheduler_config'),
        'gates': gates,
        'current_action': 'VALIDATE_DURABLE_RUNTIME',
        'next_action': ('VERIFY_SCHEDULED_INTERRUPTION_AND_RECOVERY' if successful
                        else 'VERIFY_EXTERNAL_WAKE_RECOVERY_AND_NEXT_CYCLE' if state.get('external_scheduler_config') else 'DIAGNOSE_AND_OBSERVE_REAL_SCHEDULE'),
        'first_google_organic_customer': 'NOT_YET',
        'terminal_state': terminal_state(gates, state.get('human_blocker') if not successful else None),
    }
    if state.get('human_blocker') and not successful:
        status['human_blocker'] = state['human_blocker']
        status['current_action'] = 'ACTIONS_ADMIN_DIAGNOSIS'
        status['next_action'] = 'AUTHORIZE_GITHUB_BROWSER_FALLBACK'
    elif successful:
        state.pop('human_blocker', None)
    state['SEO_AUTOPILOT_STATUS'] = status
    # Older provisional flags are superseded by externally verified evidence.
    state['SEO_RUNTIME_AUTONOMOUS'] = gates['SEO_RUNTIME_AUTONOMOUS']['status']
    return status
