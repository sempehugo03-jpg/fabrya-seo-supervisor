# Existing Supervisor: external wake transport

Only repository sempehugo03-jpg/fabrya-seo-supervisor is writable.
The existing hosted hourly task 6ac6c67c278081918b6a6d8846594c72 is the scheduler.
It runs independently of an interactive Work session. No second Supervisor.
GitHub executes the same supervisor.py and owns the same seo-state checkpoint.
The seo-wake branch carries only runtime/wake.json; all executable code is fetched
from trusted main. Source updates and manual workflow_dispatch are not wake proof.
Cloudflare Cron administration is not exposed by the connected Sites tools.
No Sites source, environment variables, Kévin, product, Stripe or domain changes.

## Every hosted invocation

1. Read this file, main head, seo-state/state/checkpoint.json, and this exact
   task's saved metadata with automations.peek. Never run_now for periodic proof.
2. Audit PREVIOUS wake commits against this task's observed last_run_time.
   Only attest a wake when its issued_at is within 30 minutes of that observed
   hosted task run, and in the same UTC hourly slot. Do not attest current Work,
   manual run_now, dispatch, native GitHub schedule, rerun, or inferred delivery.
   Fetch GitHub runs on seo-wake, completed success attempt 1, jobs and step
   conclusions. Read completed cycle_receipts with same run and current source
   commit. Require tests and Supervisor execution success. Check completed task
   keys/events for duplicate completion; do not equate another cycle to another
   task. No absent record is proof. Unresolved assertions remain FAIL.
3. Persist only verified attestations to the checkpoint by its fresh blob SHA CAS.
   Key external_scheduler_attestations by UTC slot string, with:
   automation_id, run (string), wake_commit (head_sha),
   delivery=HOSTED_SCHEDULED_TASK, observed_last_run_time (actual peek value),
   completed_tasks_unchanged=true only with dedup evidence.
   Preserve all other state, gates, events and human blockers. On SHA conflict,
   re-read and retry up to three times. Never write raw private acquisition/GSC data.
4. Fetch runtime/wake.json on seo-wake and current main SHA. Once per UTC hour,
   replace exactly that file by its blob SHA CAS, without changing other files:
   {"schema":1,"automation_id":"6ac6c67c278081918b6a6d8846594c72",
    "slot":floor(current_UTC_epoch_seconds/3600),
    "issued_at":current_UTC_epoch_seconds,"source_commit":current_main_SHA}
   If that slot was already issued, do not write again; inspect its actual run.
   Never invent a timestamp, build a new Supervisor, or put credentials in a file.
   Updating this branch triggers the existing Actions executor. No cron dependency.
5. On prior actual failure, inspect logs; existing watchdog owns immediate recovery.
   If watchdog failed, the next unique hourly wake retries the SAME persisted lease
   and unfinished tasks, with no duplicate completed tasks. Repair only proven
   defects inside this isolated SEO repository. No widening permissions or secrets.
6. Read resulting checkpoint on the next invocation. The Supervisor deliberately
   crashes once AFTER an external baseline and a persisted lease, then the existing
   watchdog resumes. Technical runtime PASS requires two independently attested
   successful external slots, actual recovery, and an external success AFTER it.
   Markers, saved scheduling, unit tests and bootstrap commits alone cannot PASS.
7. Continue the existing 11-gate terminal protocol. All gates need real evidence;
   missing GSC/product/staging/attribution capabilities stay FAIL. Do not claim they
   install themselves. Do not alter product/Kévin/Stripe to satisfy a gate.
   Notify Hugo only for COMPLETE (all 11 PASS), a new indispensable human blocker,
   or a verified first Google organic nonbrand real customer. Otherwise silence.
   Technical COMPLETE must not pause ongoing authorized SEO operation.
