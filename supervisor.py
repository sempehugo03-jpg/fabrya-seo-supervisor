"""Original SEO preparation executor. Only its own public repository is writable."""
import base64
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = 'sempehugo03-jpg/fabrya-seo-supervisor'
BRANCH = 'seo-state'
STATE_PATH = 'state/checkpoint.json'
ROOT = Path(__file__).parent


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
        status='PARTIAL_DETERMINISTIC', budget_eur=0, completed={}, failures={},
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
    result = api('PUT', '/repos/' + REPO + '/contents/' + STATE_PATH, payload)
    return result['content']['sha']


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


def main():
    if os.environ.get('GITHUB_REPOSITORY') != REPO:
        raise RuntimeError('Wrong repository: isolation refused')
    run = os.environ['GITHUB_RUN_ID']
    attempt = os.environ['GITHUB_RUN_ATTEMPT']
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
            recovered_at=time.time()))
        state['lease'] = None
        sha = save(state, sha, 'seo: recover interrupted checkpoint')
    new = 0
    for path in sorted((ROOT / 'briefs').glob('*.md')):
        key = task_id(path)
        if key in state['completed']:
            print('DEDUP: ' + key); continue
        failures = state['failures'].get(key, 0)
        if failures >= 3:
            print('RETRY_LIMIT: ' + key); continue
        state['lease'] = dict(owner=owner, run=run, task=key,
            heartbeat=time.time(), expires=time.time() + 600)
        sha = save(state, sha, 'seo: claim ' + path.stem)
        # First installation deliberately crashes AFTER a durable claim.
        probe_id = os.environ.get('CRASH_PROBE_ID', 'initial')
        probes = state.setdefault('probes', {})
        if os.environ.get('CRASH_PROBE') == 'true' and probe_id not in probes:
            probes[probe_id] = dict(owner=owner, task=key, at=time.time())
            sha = save(state, sha, 'seo: persist real interruption probe')
            os._exit(73)
        try:
            result = audit(path)
            # Completion/result atomically persisted: no non-idempotent publication.
            state['completed'][key] = dict(result=result, run=run, attempt=attempt,
                completed_at=time.time())
            state['events'].append(dict(kind='COMPLETED', task=key, owner=owner))
            state['lease'] = None
            sha = save(state, sha, 'seo: save useful review ' + path.stem)
            new += 1
        except Exception as error:
            state['failures'][key] = failures + 1
            state['events'].append(dict(kind='ERROR', task=key, owner=owner,
                error_type=type(error).__name__, error=str(error)[:500], at=time.time()))
            state['lease'] = None
            save(state, sha, 'seo: retain failed task for bounded retry')
            raise
    # No hourly empty commits or reports. GitHub run timestamps serve as cycle heartbeat.
    print(json.dumps(dict(new_results=new, completed=len(state['completed']),
        state_branch=BRANCH, status=state['status'], budget_eur=0)))
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a') as out:
            out.write(f'## Isolated SEO preparation\n{new} new reviews; '
                f'{len(state["completed"])} durable results. No production changes.\n'
                'Full supervisor remains PARTIAL_DETERMINISTIC. GSC access blocked.\n')


if __name__ == '__main__':
    main()
