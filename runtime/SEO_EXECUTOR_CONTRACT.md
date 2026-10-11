# Missing isolated production connection — concrete scope

Current production content is in Sites D1 `DB.sd_seo_pages`. Sites tools can
read it but cannot mutate it. There is no SEO mutation route in the inspected
production source. `isAdminRequest` requires platform-injected owner identity;
an unattended GitHub job cannot manufacture or forward that identity.
No owner/admin credentials are available to the isolated Supervisor. Do not
spoof trusted headers, expose a public unauthenticated writer, or change secrets.

A dedicated service connection must expose only these operations:

- Read one canonical advice page and its immutable version/content hash.
- Stage an existing page patch, with BEFORE/AFTER/WHY/private SOURCE_DATA ref
  and EXPECTED_EFFECT; no product/account/billing mutations.
- Return an isolated staging URL for real HTTP, canonical, robots, links, CTA,
  visible content, schema, JS and viewport QA at 1440/390/320. Staging noindex.
- Commit with expected current version CAS and QA certificate; preserve rollback
  checkpoint first. Reject generation abort/timeout/provider error/FALLBACK_V2.
- Restore that exact prior version only if current version is still the one
  published by this experiment. Never overwrite subsequent Kévin/product work.
- Write private experiment receipts and return only public non-sensitive proof.

The current acquisition endpoint has no payment_confirmed or checkout_started
in allowedEvents, no event-id dedup, and no verified first-touch/payer join.
The advice CTA sets internal utm_source=seo&utm_medium=organic: this is not proof
of Google acquisition. The final customer gate remains NOT_YET. Adding the
missing product event path or payment join would cross the explicit current
product/Stripe prohibition. Do not alter those routes to satisfy the gate.

Owner action required: authorize/provide the isolated SEO execution connection,
and authorize a separate minimal read-only attribution integration with the
existing product funnel. Credentials, if needed, belong in secured configuration,
never chat/public GitHub. Keep hourly GSC intake and decisions running meanwhile.
