"""Public control metadata only; no search, acquisition or customer payloads."""

from datetime import datetime

from external_scheduler import verified_external_runs, PROBE_ID
from opportunities import capability_gates

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
    all_receipts = {str(item['run']): item for item in state.get('cycle_receipts', [])
                    if item.get('status') == 'COMPLETED'}
    receipts = {run: item for run, item in all_receipts.items()
                if item.get('commit') == current_commit}
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
    external = verified_external_runs(state, current_commit, runs, jobs_by_run, all_receipts)
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
            rr_receipt = rr and all_receipts.get(str(rr['id']))
            probe_commit = external_probe.get('wake', {}).get('source_commit')
            rr_jobs = jobs_by_run.get(str(rr['id']), []) if rr else []
            rr_steps = {step.get('name'): step.get('conclusion')
                        for job in rr_jobs if job.get('conclusion') == 'success'
                        for step in job.get('steps', [])}
            if (rr and rr_receipt and probe_commit
                    and rr.get('event') == 'workflow_run'
                    and rr.get('status') == 'completed' and rr.get('conclusion') == 'success'
                    and rr.get('head_branch') == 'main' and rr.get('head_sha') == probe_commit
                    and rr.get('run_attempt', 1) == 1
                    and rr_receipt.get('commit') == probe_commit
                    and rr_steps.get('Verify recovery executor') == 'success'
                    and rr_steps.get('Recover same SEO state and unfinished useful task') == 'success'):
                external_recovery = {'run': rr['id'], 'commit': probe_commit,
                                     'completed_at': rr.get('updated_at')}
                break
    if external_recovery:
        state['external_recovery_evidence'] = {
            'run': str(external_recovery['run']),
            'commit': external_recovery['commit'],
            'completed_at': external_recovery['completed_at'],
            'probe_owner': external_probe.get('owner'),
            'event_by': next((event.get('by') for event in state.get('events', [])
                if event.get('kind') == 'RECOVERED'
                and event.get('old_owner') == external_probe.get('owner')
                and event.get('old_trigger') == 'push'
                and event.get('trigger') == 'workflow_run'
                and event.get('previous_conclusion') == 'failure'), None),
            'receipt_status': 'COMPLETED',
            'run_attempt': 1,
            'run_conclusion': 'success',
            'steps_verified': [
                'Verify recovery executor',
                'Recover same SEO state and unfinished useful task',
            ],
        }
    else:
        durable = state.get('external_recovery_evidence')
        durable_run = durable and str(durable.get('run'))
        durable_receipt = durable_run and all_receipts.get(durable_run)
        durable_receipt_valid = (
            durable_receipt is None or (
                durable.get('commit') == durable_receipt.get('commit')
                and durable_receipt.get('status') == 'COMPLETED'
                and durable_receipt.get('trigger') == 'workflow_run'
                and str(durable_receipt.get('attempt')) == '1'
            )
        ) if durable else False
        durable_event = next((event for event in state.get('events', [])
            if event.get('kind') == 'RECOVERED'
            and event.get('old_owner') == (external_probe or {}).get('owner')
            and event.get('old_trigger') == 'push'
            and event.get('trigger') == 'workflow_run'
            and event.get('previous_conclusion') == 'failure'
            and event.get('by') == durable.get('event_by')), None) if durable else None
        if (durable and external_probe and durable_event
                and durable.get('probe_owner') == external_probe.get('owner')
                and durable.get('event_by') == durable_run + ':1'
                and durable.get('commit') == external_probe.get('wake', {}).get('source_commit')
                and durable_receipt_valid
                and durable.get('completed_at')
                and durable.get('receipt_status') == 'COMPLETED'
                and durable.get('run_attempt') == 1
                and durable.get('run_conclusion') == 'success'
                and durable.get('steps_verified') == [
                    'Verify recovery executor',
                    'Recover same SEO state and unfinished useful task',
                ]):
            external_recovery = {'run': durable_run, 'commit': durable['commit'],
                                 'completed_at': durable.get('completed_at')}

    def instant(value):
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return datetime.fromisoformat(str(value).replace('Z', '+00:00')).timestamp()
        except (TypeError, ValueError):
            return 0.0

    following = external_recovery and any(
        instant(r.get('created_at')) > instant(external_recovery.get('completed_at'))
        for r in external)
    distinct_slots = {all_receipts[str(r['id'])]['wake']['slot'] for r in external}
    if len(distinct_slots) >= 2 and following:
        proof = {'scheduler': 'HOSTED_AUTOMATION', 'runs': [r['id'] for r in external],
                 'commit': current_commit,
                 'transport_sources': sorted({all_receipts[str(r['id'])]['commit'] for r in external}),
                 'recovery': external_recovery}
        gates['SEO_RUNTIME_AUTONOMOUS'] = {'status': 'PASS', 'reason': '', 'evidence': proof}
        gates['WATCHDOG_RECOVERY'] = {'status': 'PASS', 'reason': '', 'evidence': external_recovery}
        recovery = external_recovery
    elif state.get('external_scheduler_config'):
        gates['SEO_RUNTIME_AUTONOMOUS'] = {'status': 'FAIL', 'reason': 'EXTERNAL_DELIVERY_RECOVERY_AND_FOLLOWING_WAKE_NOT_YET_PROVEN', 'evidence': None}
        gates['WATCHDOG_RECOVERY'] = {'status': 'FAIL', 'reason': 'EXTERNAL_CRASH_RECOVERY_NOT_YET_PROVEN', 'evidence': None}
    gates.update(capability_gates(state))
    if not state.get('seo_decision'):
        gates['GSC_DIRECT_READ']['reason'] = 'REAL_PRIVATE_READ_AVAILABLE; FIRST_HOSTED_CONSUMPTION_AND_ATTESTATION_PENDING'
        gates['OPPORTUNITY_ENGINE']['reason'] = 'INSTALLED; FIRST_REAL_SUPERVISOR_DECISION_PENDING'
    reasons = {
        'STAGING_EXECUTOR': 'NO_AUTHORIZED_ISOLATED_CMS_WRITE_CONNECTION',
        'SEO_QA': 'NO_REAL_STAGING_CHANGE_TO_VERIFY',
        'SAFE_AUTO_PUBLISH': 'NO_CMS_CAS_QA_AND_ROLLBACK_WRITER; FALLBACK_V2_PRESENT_IN_SEO_GENERATOR',
        'MEASUREMENT_LOOP': 'NO_PUBLISHED_EXPERIMENT_TO_OBSERVE',
        'AUTO_ROLLBACK': 'NO_CMS_RESTORE_EXECUTOR_OR_REAL_RESTORATION_PROOF',
        'ATTRIBUTION_PIPELINE': 'FIRST_TOUCH_CHECKOUT_PAYMENT_JOIN_AND_EVENT_DEDUP_NOT_AVAILABLE',
        'PRIVACY_GATE': 'SUPERVISOR_WRITES_FILTERED; EXTERNAL_WRITER_AND_ARTIFACT_PATHS_NOT_FULLY_PROVEN',
    }
    if state.get('seo_boundary'):
        reasons.update({
            'STAGING_EXECUTOR': 'REAL_PRIVATE_CMS_STAGE_ACCEPTED; SCHEDULED_EXECUTOR_CONSUMPTION_PENDING',
            'SEO_QA': 'PRIVATE_STAGE_EXISTS; REAL_TARGET_RENDERER_QA_PENDING',
            'ATTRIBUTION_PIPELINE': 'IMMUTABLE_PRIVATE_FIRST_TOUCH_JOIN_INSTALLED; PUBLIC_FUNNEL_AND_OWNER_EXCLUSIONS_PENDING',
            'SAFE_AUTO_PUBLISH': 'PRIVATE_STAGING_CANNOT_PUBLISH; PRODUCTION_SEO_WRITER_AND_TARGET_QA_PENDING',
        })
    for name, reason in reasons.items():
        gates[name]['reason'] = reason

    status = {
        'current_commit': current_commit,
        'last_wake': state.get('runtime_cycle'),
        'last_successful_cycle': state.get('cycle_receipts', [None])[-1] if state.get('cycle_receipts') else None,
        'last_schedule_run': schedules[0]['id'] if schedules else None,
        'last_successful_schedule': successful[0]['id'] if successful else None,
        'last_watchdog_recovery': recovery,
        'last_external_wake': external[0]['id'] if external else None,
        'scheduler': state.get('external_scheduler_config'),
        'gates': gates,
        'current_action': state.get('seo_decision', {}).get('decision', 'WAIT_FRESH_GSC'),
        'next_action': state.get('seo_decision', {}).get('next_action', 'READ_GSC_VIA_EXISTING_SCHEDULER'),
        'first_google_organic_customer': 'NOT_YET',
        'terminal_state': terminal_state(gates, state.get('human_blocker')),
    }
    if state.get('human_blocker'):
        status['human_blocker'] = state['human_blocker']
        status['next_action'] = state['human_blocker'].get('next_action', 'OWNER_ACTION_REQUIRED')
    state['SEO_AUTOPILOT_STATUS'] = status
    # Older provisional flags are superseded by externally verified evidence.
    state['SEO_RUNTIME_AUTONOMOUS'] = gates['SEO_RUNTIME_AUTONOMOUS']['status']
    return status

