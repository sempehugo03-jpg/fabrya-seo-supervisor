# Fabrya SEO — isolated deterministic preparation

Budget: €0. No model API, deployment, paid runner, artifact, cache, private source,
Search Console export or secret. Original public preparation tools only.

## Scope and durable operation

GitHub Actions standard ubuntu-latest runner; one concurrency group for push,
schedule and manual runs. Scheduler at minutes 7,22,37,52 checks pending briefs.
Every changed brief receives a content-hash identity. Results and errors are saved
atomically in `seo-state:state/checkpoint.json` with GitHub blob-SHA compare-and-swap.
Claims, heartbeat and owner run/attempt are durable. A following cycle checks the
previous GitHub run status before reclaiming its interrupted task. Live jobs are
never reclaimed merely because the lease expired. Three failed evaluations block
a task for review. Finished work is skipped, including reruns. Empty cycles produce
no commits or hourly comments. GitHub run records retain cycle heartbeats/errors.

The first run deliberately exits 73 after persisting a claim; a later independent
run must prove recovery. No test result alone proves external operation. Consult
Actions and the state branch for actual evidence. Scheduled jobs can be delayed or
dropped by GitHub; this is not an uptime guarantee or permanent 24/7 SLA.

## Productive tasks

Two original proposals target the existing photographer and garage advice pages.
Each contains answer text, useful sections, FAQ, evidence requirements, proposed
CTA, integration checks and a conversion measurement plan. The executor validates
their metadata/structure, persists the complete review and authorizes no publishing.
New approved preparation tasks are added as briefs, not generic content batches.

Weekly deterministic competitor research reads only three allowlisted public
pages (Wix photographer, WeComm photographer, Lokalio garage), respecting robots
and refusing cross-host redirects. It records timestamp, document hash, H1 count
and lexical positioning terms, without republishing text or claiming features
were tested. It selects a concrete next evidence requirement: a real
portfolio-to-request demonstration before promising booking. Three failed attempts
are retained and stop; no credential is sent to competitors. This task continues
without Work supplying a fresh brief each week.

## Isolation and remaining blockers

GITHUB_TOKEN only belongs to this repository: contents write, actions read. The
executor hard-codes this repository and refuses any other runtime identity. No
credentials from Kévin, connection to its repository, shared workflow or deployment.
No HTTP call to the product, because its current public fetch can trigger generation.

Full SEO supervisor status is **PARTIAL_DETERMINISTIC**, never RUNNING. Private GSC
refresh needs a dedicated read-only identity and a private destination at guaranteed
zero cost; neither is provisioned here. The existing private Work/GSC fallback
continues analysis and coordination; it must not re-execute these public brief tasks.
Shared corrections require product coordination. This preparation does not prove
indexation, improved rankings, conversions or organic customers.

Official cost/schedule references:
https://docs.github.com/en/billing/concepts/product-billing/github-actions
https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule

Tests: `python3 -m unittest discover -s tests -v`.
