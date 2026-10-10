"""Original SEO preparation executor. Only its own public repository is writable."""
import base64
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from runtime_status import reconcile

REPO = 'sempehugo03-jpg/fabrya-seo-supervisor'
BRANCH = 'seo-state'
STATE_PATH = 'state/checkpoint.json'
ROOT = Path(__file__).parent
COMPETITORS = (
    'https://fr.wix.com/photography/website',
    'https://wecomm.fr/creation-site-web/photographe/',
    'https://lokalio.fr/creation-site-internet-garagiste',
)
PUBLIC_HOSTS = {'fr.wix.com', 'wecomm.fr', 'lokalio.fr'}
PUBLIC_AGENT = 'FabryaSEOReview/1.0 (+https://github.com/' + REPO + ')'
EXECUTABLE_BRIEFS = ('site-garagiste.md', 'site-photographe.md')


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        from urllib.parse import urlparse
        target = urlparse(newurl)
        if target.scheme != 'https' or target.hostname not in PUBLIC_HOSTS:
            raise RuntimeError('Competitor redirect outside allowlist refused')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def public_read(url):
    from urllib.parse import urlparse
    target = urlparse(url)
    if target.scheme != 'https' or target.hostname not in PUBLIC_HOSTS:
        raise RuntimeError('Public destination refused')
    req = urllib.request.Request(url, headers={'User-Agent': PUBLIC_AGENT})
    # No GitHub auth, cookies, analytics callback or provider credentials.
    with urllib.request.build_opener(SafeRedirect()).open(req, timeout=15) as response:
        body = response.read(1_000_001)
        if len(body) > 1_000_000:
            raise RuntimeError('Public document too large')
        return body


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(); self.hidden = 0; self.parts = []; self.h1 = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag == 'h1':
            self.h1 += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def review_competitor(url):
    from urllib.parse import urlparse
    robot_url = 'https://' + urlparse(url).hostname + '/robots.txt'
    try:
        robots = public_read(robot_url).decode('utf-8', errors='replace')
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        robots = ''
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(robots.splitlines())
    if not parser.can_fetch(PUBLIC_AGENT, url):
        return dict(url=url, status='ROBOTS_DISALLOWED')
    body = public_read(url)
    visible = VisibleText(); visible.feed(body.decode('utf-8', errors='replace'))
    surface = ' '.join(visible.parts).lower()
    terms = [term for term in ('portfolio', 'réservation', 'devis', 'google maps',
        'fiche google', 'galerie', 'démonstration') if term in surface]
    return dict(url=url, status='READ', fetched_at=time.time(),
        document_sha256=hashlib.sha256(body).hexdigest(), h1_count=visible.h1,
        observed_lexical_terms=terms, claims_verified=False)


def competitor_review():
    results = []
    for url in COMPETITORS:
        try:
            results.append(review_competitor(url))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, RuntimeError) as error:
            # A blocked/oversized document is evidence, not grounds to bypass its limit
            # or discard observations from the other explicitly allowed sources.
            results.append(dict(url=url, status='BLOCKED', error_type=type(error).__name__,
                error=str(error)[:300], at=time.time(), claims_verified=False))
    return dict(kind='PUBLIC_COMPETITOR_SURFACE', results=results,
        observed_pages=sum(r['status'] == 'READ' for r in results),
        operational_status='OBSERVED' if all(r['status'] == 'READ' for r in results) else 'WITH_BLOCKERS',
        interpretation='Lexical observations, not feature tests or ranking evidence',
        next_action='Validate one real portfolio-to-request demo before promising booking',
        publication_authorized=False)


def api(method, path, body=None):
    # No arbitrary destinations, private repository, provider API or site HTTP.
    assert path.startswith('/repos/' + REPO + '/')
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request('https://api.github.com' + path, data=data,
        method=method, headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
        'Accept': 'application/vnd.github+json', 'User-Agent': 'fabrya-seo-isolated',
        'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def empty_state():
    return dict(identity='fabrya-seo-deterministic-v1', schema=1,
        status='PARTIAL_DETERMINISTIC', SEO_RUNTIME_AUTONOMOUS='FAIL',
        budget_eur=0, completed={}, failures={},
        lease=None, events=[], blocked=['GSC_DEDICATED_READONLY_ACCESS',
        'PRODUCT_ZERO_BUDGET_GATE', 'PRODUCTION_COORDINATION'])


def load():
    base = '/repos/' + REPO
    try:
        result = api('GET', base + '/contents/' + STATE_PATH + '?ref=' + BRANCH)
        return json.loads(base64.b64decode(result['content'])), result['sha']
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    try:
        head = api('GET', base + '/git/ref/heads/main')['object']['sha']
        api('POST', base + '/git/refs', {'ref': 'refs/heads/' + BRANCH, 'sha': head})
    except urllib.error.HTTPError as error:
        if error.code != 422:
            raise
    return empty_state(), None


def save(state, sha, message):
    # GitHub content SHA is a compare-and-swap fence, conflicting writers fail closed.
    content = base64.b64encode((json.dumps(state, ensure_ascii=False, indent=2) + '\n').encode()).decode()
    payload = dict(message=message, content=content, branch=BRANCH)
    if sha:
        payload['sha'] = sha
    path = '/repos/' + REPO + '/contents/' + STATE_PATH
    for attempt in range(3):
        try:
            result = api('PUT', path, payload)
            return result['content']['sha']
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            if isinstance(error, urllib.error.HTTPError) and error.code < 500:
                raise  # Never retry an authorization failure or CAS conflict.
            # A real GitHub 500 occurred AFTER applying a checkpoint. Read before retrying.
            try:
                observed = api('GET', path + '?ref=' + BRANCH)
                if json.loads(base64.b64decode(observed['content'])) == state:
                    print('AMBIGUOUS_WRITE_CONFIRMED: checkpoint persisted once')
                    return observed['sha']
                if observed['sha'] != sha:
                    raise RuntimeError('Checkpoint changed concurrently; write refused') from error
            except urllib.error.HTTPError as read_error:
                if read_error.code != 404 or sha is not None:
                    raise
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    raise RuntimeError('Unreachable checkpoint retry state')


def executable_brief_paths():
    """Return only canonical SEO work items; policy/support docs are never executable."""
    paths = [ROOT / 'briefs' / name for name in EXECUTABLE_BRIEFS]
    missing = [path.name for path in paths if not path.is_file()]
    if missing:
        raise RuntimeError('Missing executable SEO briefs: ' + ', '.join(missing))
    return paths


def audit(path):
    text = path.read_text()
    title = re.search(r'^title: (.+)$', text, re.M).group(1)
    description = re.search(r'^description: (.+)$', text, re.M).group(1)
    headings = re.findall(r'^## (.+)$', text, re.M)
    issues = []
    if not 25 <= len(title) <= 65:
        issues.append('TITLE_LENGTH_REVIEW')
    if not 100 <= len(description) <= 175 or not description.endswith('.'):
        issues.append('DESCRIPTION_REVIEW')
    for needed in ('Demande', 'Preuves', 'Validation', 'Mesure'):
        if not any(needed.lower() in h.lower() for h in headings):
            issues.append('MISSING_' + needed.upper())
    if 'utm_source=' in text or 'réservation garantie' in text:
        issues.append('UNVERIFIED_ACQUISITION_OR_PROMISE')
    return dict(page=path.stem, title=title, description=description,
        title_length=len(title), description_length=len(description),
        headings=headings, findings=issues, editorial_status='NEEDS_HUMAN_REVIEW',
        publication_authorized=False, body=text)


def task_id(path):
    return 'brief-review:' + path.stem + ':' + hashlib.sha256(path.read_bytes()).hexdigest()


def restore_normal_cadence():
    """CAS restore of the existing scheduler, only after external proof."""
    path = '/repos/' + REPO + '/contents/.github/workflows/seo.yml'
    current = api('GET', path + '?ref=main')
    text = base64.b64decode(current['content']).decode()
    accelerated = "cron: '*/5 * * * *'"
    if accelerated not in text:
        return
    restored = text.replace(accelerated, "cron: '7,22,37,52 * * * *'")
    api('PUT', path, dict(sha=current['sha'], branch='main',
        message='seo: restore normal cadence after scheduled recovery proof',
        content=base64.b64encode(restored.encode()).decode()))


def reconcile_runtime_status(state):
    base = '/repos/' + REPO
    current = api('GET', base + '/git/ref/heads/main')['object']['sha']
    runs = api('GET', base + '/actions/runs?per_page=100')['workflow_runs']
    receipt_ids = {str(item['run']) for item in state.get('cycle_receipts', [])}
    jobs = {}
    for run in runs:
        if (str(run['id']) in receipt_ids and run.get('head_sha') == current
            and run.get('status') == 'completed' and run.get('conclusion') == 'success'):
            jobs[str(run['id'])] = api('GET', base + '/actions/runs/'
                + str(run['id']) + '/jobs')['jobs']
    return reconcile(state, current, runs, jobs)


def reconcile_only():
    if os.environ.get('GITHUB_REPOSITORY') != REPO:
        raise RuntimeError('Wrong repository')
    state, sha = load()
    status = reconcile_runtime_status(state)
    save(state, sha, 'seo: reconcile externally verified autopilot status')
    print(json.dumps(status))


def diagnose_runtime():
    if os.environ.get('GITHUB_REPOSITORY') != REPO:
        raise RuntimeError('Wrong repository')
    base = '/repos/' + REPO
    diagnosis = {}
    for label, path in (
        ('workflows', '/actions/workflows'),
        ('actions_settings', '/actions/permissions'),
        ('default_token_permissions', '/actions/permissions/workflow'),
    ):
        try:
            value = api('GET', base + path)
            if label == 'workflows':
                value = [{'id': item['id'], 'path': item['path'], 'state': item['state']}
                         for item in value['workflows']]
            diagnosis[label] = value
        except urllib.error.HTTPError as error:
            diagnosis[label] = {'status': 'READ_UNAVAILABLE', 'http_status': error.code}
    print(json.dumps({'runtime_diagnosis': diagnosis}))


def main():
    if os.environ.get('GITHUB_REPOSITORY') != REPO:
        raise RuntimeError('Wrong repository: isolation refused')
    run = os.environ['GITHUB_RUN_ID']
    attempt = os.environ['GITHUB_RUN_ATTEMPT']
    trigger = os.environ['GITHUB_EVENT_NAME']
    owner = run + ':' + attempt
    state, sha = load()
    lease = state['lease']
    if lease:
        previous = api('GET', '/repos/' + REPO + '/actions/runs/' + lease['run'])
        terminal = previous['status'] == 'completed'
        same_run_new_attempt = lease['run'] == run and lease['owner'] != owner
        if not terminal and not same_run_new_attempt:
            # Expiry alone never permits overlapping live GitHub jobs.
            print('LOCKED: previous run still active'); return
        state['events'].append(dict(kind='RECOVERED', old_owner=lease['owner'],
            by=owner, previous_conclusion=previous.get('conclusion'), task=lease['task'],
            trigger=trigger, old_trigger=lease.get('trigger'), recovered_at=time.time()))
        state['lease'] = None
        sha = save(state, sha, 'seo: recover interrupted checkpoint')
    # Every scheduled cycle advances an inspectable, non-private checkpoint.
    state['runtime_cycle'] = dict(run=run, attempt=attempt, trigger=trigger,
        commit=os.environ['GITHUB_SHA'], started_at=time.time(), status='STARTED')
    state['lease'] = dict(owner=owner, run=run, task='runtime-verification',
        trigger=trigger, heartbeat=time.time(), expires=time.time() + 600)
    sha = save(state, sha, 'seo: checkpoint durable cycle start')
    # One reversible scheduled failure, recovered by the existing watchdog.
    runtime_probe_id = 'scheduled-runtime-verification-20261010'
    probes = state.setdefault('probes', {})
    if trigger == 'schedule' and 'scheduled_baseline' in state and runtime_probe_id not in probes:
        probes[runtime_probe_id] = dict(owner=owner, task='runtime-verification',
            trigger=trigger, at=time.time())
        sha = save(state, sha, 'seo: persist scheduled interruption probe')
        os._exit(73)
    state['lease'] = None
    new = 0
    tasks = [(task_id(path), path.stem, lambda p=path: audit(p))
        for path in executable_brief_paths()]
    week = datetime.now(timezone.utc).strftime('%G-W%V')
    tasks.append(('competitor-surface:' + week + ':v2', 'competitor-surface', competitor_review))
    for key, label, evaluate in tasks:
        if key in state['completed']:
            print('DEDUP: ' + key); continue
        failures = state['failures'].get(key, 0)
        if failures >= 3:
            print('RETRY_LIMIT: ' + key); continue
        state['lease'] = dict(owner=owner, run=run, task=key, trigger=trigger,
            heartbeat=time.time(), expires=time.time() + 600)
        sha = save(state, sha, 'seo: claim ' + label)
        # First installation deliberately crashes AFTER a durable claim.
        probe_id = os.environ.get('CRASH_PROBE_ID', 'initial')
        probes = state.setdefault('probes', {})
        if os.environ.get('CRASH_PROBE') == 'true' and probe_id not in probes:
            probes[probe_id] = dict(owner=owner, task=key, trigger=trigger, at=time.time())
            sha = save(state, sha, 'seo: persist real interruption probe')
            os._exit(73)
        try:
            result = evaluate()
            # Completion/result atomically persisted: no non-idempotent publication.
            state['completed'][key] = dict(result=result, run=run, attempt=attempt,
                trigger=trigger, commit=os.environ['GITHUB_SHA'], completed_at=time.time())
            state['events'].append(dict(kind='COMPLETED', task=key, owner=owner, trigger=trigger))
            state['lease'] = None
            sha = save(state, sha, 'seo: save useful review ' + label)
            new += 1
        except Exception as error:
            state['failures'][key] = failures + 1
            state['events'].append(dict(kind='ERROR', task=key, owner=owner,
                error_type=type(error).__name__, error=str(error)[:500], at=time.time()))
            state['lease'] = None
            save(state, sha, 'seo: retain failed task for bounded retry')
            raise
    state['runtime_cycle'].update(status='COMPLETED', completed_at=time.time(), new_results=new,
        decision='PREPARATION_COMPLETED' if new else 'NO_ACTION',
        reason='Canonical briefs unchanged; no GSC/product connection configured in this Supervisor' if not new else 'Brief review completed')
    if trigger == 'schedule':
        state.setdefault('scheduled_baseline', dict(state['runtime_cycle']))
        probe = state.get('probes', {}).get(runtime_probe_id)
        recovered = probe and any(event.get('kind') == 'RECOVERED'
            and event.get('old_owner') == probe.get('owner')
            and event.get('old_trigger') == 'schedule'
            and event.get('trigger') == 'workflow_run' for event in state['events'])
        if recovered:
            state['SEO_RUNTIME_AUTONOMOUS'] = 'PASS'
            state['runtime_verification'] = dict(baseline=state['scheduled_baseline'],
                interruption=probe, following_schedule=dict(state['runtime_cycle']))
    state.setdefault('SEO_RUNTIME_AUTONOMOUS', 'FAIL')
    state.setdefault('cycle_receipts', []).append(dict(state['runtime_cycle']))
    state['cycle_receipts'] = state['cycle_receipts'][-100:]
    reconcile_runtime_status(state)
    sha = save(state, sha, 'seo: checkpoint durable cycle result')
    if state['SEO_AUTOPILOT_STATUS']['gates']['WATCHDOG_RECOVERY']['status'] == 'PASS':
        restore_normal_cadence()
    # Cycle metadata contains no private performance or acquisition data.
    print(json.dumps(dict(new_results=new, completed=len(state['completed']),
        trigger=trigger, run=run, state_branch=BRANCH, status=state['status'], budget_eur=0)))
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a') as out:
            out.write(f'## Isolated SEO preparation\n{new} new reviews; '
                f'{len(state["completed"])} durable results. No production changes.\n'
                'Full supervisor remains PARTIAL_DETERMINISTIC. GSC access blocked.\n')


if __name__ == '__main__':
    if '--diagnose-runtime' in sys.argv:
        diagnose_runtime()
    elif '--reconcile' in sys.argv:
        reconcile_only()
    else:
        main()

