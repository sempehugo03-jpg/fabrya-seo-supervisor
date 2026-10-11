# Real GSC data path — existing scheduler and Supervisor

Use the existing hosted task and existing GitHub executor. No new Supervisor.
Runtime/watchdog verification is acquired; never inject a second crash.

## Data intake at each existing scheduled cycle

1. Read the latest private snapshot and public aggregate manifest. Refresh GSC
   at EACH cycle as Hugo explicitly requested on 11 October 2026. Retry a failed
   read next wake, at most three attempts per error cycle; preserve the prior
   actual timestamp when data is unavailable. Do not claim a fresh read from reuse.
2. Use connected GSC Wizard for property https://fabrya.fr/:
   query_search_analytics dimensions [date,query,page], rowLimit 1000;
   query_search_analytics dimensions [page], rowLimit 1000; get_site_summary days28.
   Omit dates for the connector's actual available 28-day window. Paginate using
   returned pagination, bounded to 10 pages. Incomplete pagination is UNKNOWN,
   never full coverage. Require dataSource api, matching dates/searchType web.
   Never substitute the legacy public baseline or fixtures. If API unavailable,
   retain prior observation with its actual date; do not claim a fresh read.
3. Verify sempehugo03-jpg/fabrya-engine remains PRIVATE. Only write data under
   seo/gsc/ on existing branch seo-private-state; no main or product/Kévin edits.
   Persist immutable YYYY-MM-DD-<UTC-slot>.json snapshot with actual read_at,
   source, acquisition HOSTED_SCHEDULED_TASK, this automation's actual metadata,
   full connector responses and missing-value flags. Use create_file, then read
   back and compare. If an identical snapshot exists, reuse it. Never overwrite.
4. Construct aggregate-only state/gsc-latest.json on public SEO branch seo-state:
   exact top-level keys schema=1, source=GSC_API, read_at, start_date, end_date,
   settled_through (UNKNOWN when connector returns null), private_snapshot_commit
   (actual private write commit), acquisition=HOSTED_SCHEDULED_TASK,
   automation_slot=floor(actual current UTC epoch/3600), pages.
   Each page has exact keys url, clicks, impressions, ctr, position,
   commercial_intent COMMERCIAL/BRAND/UNKNOWN, nonbrand_visible_impressions,
   nonbrand_visible_position. Use canonical fabrya.fr URLs without query/fragment.
   Decide intent from actual query meaning, without a fixed sector list. Only
   commercial visible nonbrand rows contribute to their aggregate impressions
   and impression-weighted position. Brand rows never count as nonbrand. If no
   supported visible commercial query, use UNKNOWN. Do not publish query strings.
   Do not infer unknown query ranks from page averages; anonymized rows differ.
   Do not sum page totals and claim property totals. No client/session identifiers.
5. Update manifest using fetched blob SHA CAS; read back. Do not commit daily data on main (it needlessly invalidates source proof). Read current main SHA,
   then execute the normal unique hourly wake protocol. Do not use dispatch.
6. On the following wake, inspect previous actual jobs and cycle receipts and
   saved automation metadata. GSC_DIRECT_READ stays FAIL until the observation's
   slot has independently verified HOSTED_SCHEDULED_TASK delivery attestation.
   A saved prompt or this installation read is not evidence of autonomous intake.
7. Original supervisor.py validates allowlist and decides at most three actions.
   Record real decision and UNKNOWN page quality/conversions. Never invent a sale.
   Inspect the selected public page, compare several hypotheses, and pursue only
   existing reversible SEO actions. No production write without a genuine isolated
   writer, current-version CAS, QA and rollback. Detect source changes and defer.
   No custom security bypass, secret alteration, Stripe/Kévin or Product change
   outside the explicitly authorized CMS SEO/passive attribution boundary.

## Proven integration boundary

Production source inspected at Sites commit 4b7369b5bee6d400d13e0d52616ea88d87d4aab6.
Content resides in sd_seo_pages. Connected Sites exposes read-only D1 rows; the
current app has no SEO-specific mutation endpoint. The internal daily generator
publishes FALLBACK_V2 after provider failures. Do not call or impersonate it as
an executor. Staging/publication/rollback gates must stay FAIL until a safe
SEO-only content writer exists. Acquisition API currently lacks checkout/payment
confirmation and creates a fresh random event id for every POST; it does not
prove deduplication or first-touch payment attribution. CMS SEO and passive attribution preparation are now explicitly authorized.
Do not change Stripe, prices, checkout behavior or activation. Read current
runtime/PRODUCT_BOUNDARY.md and the current Product/public deployments before
using the above dated observations as a release gate; a price mismatch does not
stop safe SEO work or require a normal SEO decision from Hugo.
