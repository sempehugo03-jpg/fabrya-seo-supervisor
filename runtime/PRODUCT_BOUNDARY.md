# Authorized targeted Product integration and remaining release boundary

Hugo's 11 October mandate authorizes CMS SEO and passive first-touch attribution
only. Existing runtime, watchdog, GSC and opportunity evidence stays acquired.
Do not reconstruct them, repeat the crash probe, redesign Product or call Kevin.

## Existing private capability

Product branch work/fabrya-product-20261010, PR #202.
Targeted Product commit 1baf79355c313e226c5d0b23116dd63c5cb0d850.
Private Site appgprj_6acac4a9d9808191b57085eb34fa06be, deployment
appgdep_6acbd760840481918076c74f053ab49f succeeded; Sites source
 e57b284b11ead4350b5c68cc13409f5e744ef270.
44 branch Product tests, root build and Worker build passed. Private source tests
43/43 and Worker build passed. Interface and payment files preserved in this change.
The mismatch in test count is the existing Product trust-copy test in its newer
branch; private interface source was deliberately preserved.

Obtain owner-private Site capability with get_site on that exact ID each run.
Never store or print it. Use runtime/private_transport.mjs through masked stdin;
only the fixed private origin, GET SEO pages/preview/aggregate attribution and
POST stage are permitted. The transport cannot call Product or payment APIs.
If code execution is available, fetch this source through GitHub and use a scratch
script or the existing checkout. Never put a capability in shell arguments/files.
No plugin installation, new credential, general proxy or authentication bypass.

GET /api/seo/pages/<slug> reads an existing mirror and CAS hash.
GET /api/seo/attribution reads only aggregate first-touch/payment joins.
POST /api/seo/changes action stage accepts id, slug, expected_version, at most
two allowlisted patch fields, why, source_commit, generation_status EDITORIAL_PATCH,
source_data and expected_effect. source_data contains exactly an actual private
snapshot_commit, read_at, start_date, end_date, impressions, clicks, position, ctr.
Never invent an experiment source. Metadata fields and content_json metadata must
agree. Refuse script markup, fallback/error markers and private information.
The server stores BEFORE, AFTER, hashes, provenance and timestamps. Replaying an
identical command returns the same row; mismatches and concurrent edits fail.
Private publication is disabled even with a supplied QA assertion.

A real manually initiated stage exists: seo-garage-20261011-business-01. It adds
only concrete atelier/vehicle/contact guidance to the existing public-source
mirror. It is not a publication or autonomous stage proof. Source GSC snapshot
8661c4717553c284d7b34dc49ef9c6141818d3b4: 47 page impressions, zero clicks.

## Continue every scheduled cycle

1. Read GSC as the user now requests each cycle, preserving raw rows privately.
   Retain UNKNOWN settled-through and query coverage; page-average position is
   not a visible query's position. Select 1–3 commercially justified actions.
2. Inspect actual existing pages; consider title/snippet, intent, useful content,
   CTA and proof. Page photographer average 5.55 over 11 impressions differs from
   visible non-brand query average 24 over only 2 impressions. Garage page average
   53.87 over 47 differs from visible commercial average 85.28 over 29. No clicks.
   These observed values are a dated baseline, not future priorities or guarantees.
3. Use the private CMS for bounded staging when worthwhile. Never restage a page
   hourly. Reuse an existing id after interruption; cap to 3 actions per cycle and
   avoid identical hypotheses without fresh evidence. Record the actual response
   and automation metadata, only aggregate/hash evidence in the public checkpoint.
4. Read aggregate attribution. A private origin is always test traffic and cannot
   meet the business goal. Missing owner/test exclusion configuration fails closed.
   No first-touch is inferred from GSC, an internal UTM, or a later Google visit.
5. Continue allowed reads/decisions/private staging while the public release
   boundary is unresolved. The old authorization-scope blocker is resolved;
   never request the same CMS/attribution authorization again.

## Current public boundary — revalidated 11 October 2026

This is a dated observation, not a permanent blocker. Hugo requires current
Product and public deployment reads before any release-boundary decision.
On 11 October at 19:05 UTC:
- Public Site version 506 still uses source
  4b7369b5bee6d400d13e0d52616ea88d87d4aab6. Browser /tarifs visibly shows
  EUR90/month, first charge after 30 days. Root metadata agrees. The deployed
  checkout source enforces 9000 EUR cents and trial_period_days=30; no checkout
  or payment was created for this inspection.
- Public /conseils/site-photographe is rendered and its demo CTA targets the
  same public root with internal utm_source=seo. That internal label never
  proves a first acquisition from Google.
- Public D1 overview contains sd_seo_pages and sd_acquisition_events but no
  installed fp_first_touch/fp_seo_changes tables. Its source has client-updated
  campaign context and no bounded /api/seo/changes endpoint. Do not mistake
  the private CMS for the public writer.
- Product Supervisor checkpoint current_commit
  1ff66765548446fbd174357908d2ad405ede1335 follows 18e21823457012f07321eaa6370f77abdf11ab81.
  Product tests PASS; browser QA is being repaired/recovered. PUBLIC_READY=NOT_YET,
  public_deployment_status=NOT_AUTHORIZED. This is an observation of another
  Supervisor, not authorization to release or change billing.
- Private Site version 20 source 537ca5e92d841b1a7b297f3ba744b30d79c71c3b deployed
  successfully at 19:04 UTC. Its live aggregate attribution endpoint still
  responds 200: direct test sessions only, zero projects/demos/checkouts/confirmed
  payments, exclusion_policy_ready=false, first_google_organic_customer=NOT_YET.

Remove PUBLIC_PRODUCT_RELEASE_OUTSIDE_SEO_SCOPE as a blanket human stop.
The price mismatch remains currently observed, but it does not prevent GSC,
page inspection, CMS/attribution preparation or private bounded staging.
Keep the SEO loop RUNNING with the production connection gates FAIL.
A genuinely indispensable out-of-scope release/payment action can require a
separate human gate only at that concrete action, with fresh evidence.

At EACH cycle re-read the actual Product checkpoint, current deployed versions
and the public price/CTA before trusting this snapshot. If the public 59/month
Product becomes deployed, immediately discard the old price blocker and verify
the actual public CMS and immutable first-touch joins; price alone proves neither.
Never promote the private Product, change price/checkout/Stripe/activation, or
create a live payment from the SEO scope. Product may continue independently.
A production SEO-only writer remains explicitly authorized and may be prepared
without asking Hugo for a normal SEO decision.

STAGING_EXECUTOR needs actual scheduled use; SEO_QA needs the real target renderer;
SAFE_AUTO_PUBLISH, MEASUREMENT_LOOP, AUTO_ROLLBACK and ATTRIBUTION_PIPELINE stay
FAIL until production connections/receipts exist. PRIVACY_GATE needs that complete
boundary verified. A private SQL rollback or payment fixture is not public proof.

## Business horizon

Goal: one new actual paying Google-organic customer before 22 October 2026.
Accept verified brand or non-brand Google organic; missing query is UNKNOWN for
brand classification, never manufactured non-brand. Exclude Hugo, tests, technical
traffic, campaigns, outbound and unproven historic acquisitions. Only a joined
new acquisition → project → checkout → confirmed paid LIVE event qualifies.
No paid ads, backlink purchases, model costs, fake clicks/reviews or mass pages.
No guarantee: when the deadline arrives, report actual GSC and funnel values,
UNKNOWN where missing, and GOAL_NOT_MET unless a real attributable payment exists.
