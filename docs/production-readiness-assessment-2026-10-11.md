# TREND production-readiness assessment — 2026-10-11

## Executive decision

**Do not launch this revision for unrestricted public or company-funded AI
generation yet.** The project has substantial product implementation, a
meaningful automated test suite, and a frontend production build that succeeds.
However, this checkout also has an urgent database RPC privilege concern,
non-idempotent credit mutation paths, race-prone rate limiting, a broken Gemini
provider path, current frontend dependency advisories, and conflicting
deployment configurations.

The project could be made suitable for a restricted beta, but only after the
P0/P1 work below has been completed and verified against the actual production
database and deployment. A green unit-test run alone is not sufficient for
billing, authorization, and cloud-runtime readiness.

## Scope and limits

Reviewed the tracked backend, frontend, database migrations, deployment
manifests, tests, and the existing project-health audit. The current checkout
is commit `aa53fd5` on `main`.

This was a source/configuration assessment. I did not connect to the deployed
Supabase project, inspect live database ACLs or secrets, deploy or build a
container image, exercise the live product in a browser, run load tests, or
verify a live provider account. Therefore:

- Database ACL findings below are confirmed omissions in the tracked migration
  history; the effective production grants still need an immediate read-only
  privilege check.
- Deployment findings describe checked-in manifests, not proof of the live
  deployment’s environment variables or running commit.
- Dependency audit results are for the checked-in frontend lockfile and current
  registry advisories, not proof that a particular advisory is exploitable in
  the deployed configuration.
- Product/UI issues documented in the older
  [October 1 audit](./project-health-audit-2026-10-01.md) are historical leads
  and must be revalidated against this later checkout before treating them as
  current defects.

## Verification performed

| Check | Result |
| --- | --- |
| Backend tests | **339 passed**, 6 warnings |
| Frontend tests | **31 passed** across 4 test files |
| Frontend production build | **Passed**, including lint/type-check and static generation |
| Frontend lint | **Passed**, with 5 `<img>` performance warnings |
| Backend Ruff | **Failed: 160 findings**; includes one `F821` undefined-name finding in the Gemini provider |
| Frontend production dependency audit | **1 critical, 11 high, 1 moderate** reported by `npm audit --omit=dev` against the npm registry |
| CI workflow definitions | No tracked GitHub Actions or other CI workflow was found |
| Production/container deployment | Not built or deployed as part of this review |

The checked local backend interpreter is Python 3.11.9 while the container
declares Python 3.13. The tests therefore do not by themselves certify the
declared production Python runtime.

## Release-blocking and high-priority findings

### P0 — Verify and close public execution on privileged credit RPCs

The credit ledger migration defines `SECURITY DEFINER` mutation functions,
including `commit_generation_credit` and `release_generation_credit`, but does
not revoke execution from `PUBLIC`, `anon`, or `authenticated`, nor grant those
functions only to `service_role`. PostgreSQL grants `EXECUTE` on new functions
to `PUBLIC` by default unless database default privileges have been changed.
These functions accept a caller-supplied `p_user_id` and do not themselves
verify the authenticated caller owns that account. The later quota migration
does explicitly revoke public execution for its own RPCs, but does not revoke
the credit commit/release functions; it also replaces
`reserve_generation_credit` without an explicit public-role revoke.

**Impact:** If the deployed ACLs follow PostgreSQL defaults, a browser/API
client may be able to call privileged balance/reservation functions directly
and manipulate another user’s credit state. This is a potential critical
authorization flaw; verify the live ACL before assuming it is exploitable.

**Fix:** Immediately query `pg_proc`/`information_schema.routine_privileges` in
the production database for every `SECURITY DEFINER` RPC. Add a forward-only
migration that revokes `EXECUTE` from `PUBLIC`, `anon`, and `authenticated` on
every service-only credit RPC, grants only `service_role`, and verifies
`search_path` and authorization assumptions. Add a database-role regression
test proving browser roles cannot call these functions. Do not edit or replay
an already-applied migration; ship a new migration.

Evidence: [credit RPC definitions](../supabase/migrations/00028_create_credit_rpc_functions.sql)
and [quota RPC permission pattern and credit replacement](../supabase/migrations/00029_add_free_plan_quotas.sql).

### P1 — Make credit commit and release operations genuinely idempotent

The credit commit/release functions update account balances or reservations
before inserting a ledger record with `ON CONFLICT DO NOTHING`. A retry with the
same reservation identifier can therefore mutate the account again even when
the ledger insert is ignored. Commit also does not first prove that the
reservation exists and is still in the reserved state.

**Impact:** A timeout followed by a retry can double-charge credits or
mis-reconcile a reservation; a repeated release can alter reserved balances
more than once.

**Fix:** Model reservation state explicitly and perform state validation,
account mutation, and ledger transition in one transaction. A duplicate
operation should return its prior result without applying a second balance
change. Enforce one-time transitions with unique reservation/operation keys or
row locks plus status checks. Add SQL-level tests for duplicate reserve,
commit, release, and commit-after-release calls.

Evidence: [credit commit/release RPCs](../supabase/migrations/00028_create_credit_rpc_functions.sql).

### P1 — Replace the rate limiter’s read/modify/write sequence with an atomic operation

`check_generation_rate_limit` reads a bucket count, compares it, then inserts or
updates in a separate call. Simultaneous requests can both pass the same
threshold check; simultaneous first requests can also race to insert the same
primary key.

**Impact:** The configured limit can be exceeded under load, or valid requests
can fail with a database uniqueness error. The generation lock is not a
substitute for a correct atomic limiter.

**Fix:** Use one database RPC/SQL statement that atomically upserts a bucket
only when the existing count is below the limit and reports whether it
accepted the request. Test the exact boundary under concurrent calls and keep
the RPC service-role-only.

Evidence: [rate limiter implementation](../backend/app/services/rate_limit.py)
and [rate-limit bucket schema](../supabase/migrations/00025_add_credit_usage_control.sql).

### P1 — Fix or disable the Gemini image-provider option

`gemini_generate` passes `aspect_ratio=aspect_ratio` to the SDK, but
`aspect_ratio` is not defined in the function or module. The backend Ruff run
reports this as `F821`.

**Impact:** Any generation routed to Gemini raises `NameError` rather than
producing an image. This may be latent if production is configured only for
OpenAI.

**Fix:** Derive a supported Gemini aspect ratio from the supplied `width` and
`height` (with a deterministic mapping and documented fallback), or remove
Gemini from selectable/configurable providers until implemented. Add tests that
exercise the SDK request configuration for supported ratios.

Evidence: [Gemini provider](../backend/app/services/providers/gemini_image.py).

### P1 — Reconcile the deployment architecture and configure the runtime it requires

The repository describes multiple incompatible deployment paths:

- [Dockerfile](../Dockerfile) builds and runs both Next.js and FastAPI in one
  image.
- [Render manifest](../render.yaml) deploys only the Python backend from
  `backend/` on the **free** plan.
- [Next.js configuration](../frontend/next.config.mjs) needs a backend URL at
  build time for rewrites; server routes also use runtime backend configuration.

The Render manifest includes the obsolete `SUPABASE_ANON_KEY` variable instead
of the project’s documented publishable-key approach, sets CORS origins to
localhost only, and does not define `OPENAI_API_KEY` even though
`OPENAI_API_KEY` defaults to empty and managed generation uses it. Those facts
make the checked-in Render configuration inconsistent with the documented
product architecture and likely leave generation unavailable unless operators
manually add omitted settings.

**Impact:** It is unclear which deployment is authoritative, and independently
deploying the frontend/backend can produce broken API routing, browser CORS
failures, or an unconfigured generation service. A free hosting plan is not a
reliable basis for a paid or latency-sensitive production promise.

**Fix:** Pick one authoritative architecture. Document its single source of
truth and environment-variable contract; remove stale manifests or align them.
For a separate frontend/backend, set and verify frontend build-time
`NEXT_SERVER_API_URL` and runtime URL, set only the exact required production
origins where browser CORS is used, configure provider credentials through the
host’s secret manager, remove legacy env names, and choose an always-on
production plan. Add a staging deployment smoke test for login, API proxy,
generation, and health checks.

Evidence: [Render manifest](../render.yaml), [container build](../Dockerfile),
[Docker deployment guide](./docker.md), and [backend configuration](../backend/app/config.py).

### P1 — Remediate frontend dependency advisories in a controlled upgrade

The current frontend production dependency audit reported **1 critical, 11
high, and 1 moderate** affected package entries. The direct `next` dependency
is pinned to `14.2.35`; the existing October 2 audit also records an earlier
critical Next.js advisory. An audit finding is a risk signal, not proof of
exploitability in the live service.

**Fix:** Triage the current advisories against deployed usage and supported
fixes; upgrade Next.js and affected transitive dependencies in a dedicated
branch, without blindly forcing a major upgrade. Run frontend unit tests,
lint, production build, auth/API route smoke tests, and the audit again. Keep
the resulting lockfile and a reviewable upgrade note.

Evidence: [frontend dependency manifest](../frontend/package.json),
[frontend lockfile](../frontend/package-lock.json), and
[October 2 captured audit](./project-health-npm-audit-2026-10-02-rollback.json).

### P1 — Lock backend dependencies and add automated CI gates

`backend/requirements.txt` uses broad lower bounds for most runtime packages
and no backend lockfile is present. A clean build can therefore resolve
different packages on different days. There are no tracked CI workflow
definitions. The current Ruff check fails with **160 findings**, including
unused imports, blind exception handlers, import-order issues, and the
undefined Gemini name.

**Impact:** Builds are not fully reproducible, dependency changes can arrive
without review, and local test success does not gate pull requests or release.

**Fix:** Adopt a lockfile/constraints workflow for Python runtime and dev
dependencies; separate production from test/tooling dependencies; build/test
on Python 3.13 and Node 20 in CI; gate pull requests on tests, Ruff, frontend
lint, frontend tests/build, dependency audits, and migration checks. First
triage the lint findings and fix correctness/security findings before applying
bulk style fixes.

Evidence: [backend requirements](../backend/requirements.txt),
[frontend scripts](../frontend/package.json), and the Ruff/test results above.

### P1 — Add a database readiness check and basic operational observability

`/health` always returns `healthy` with a timestamp and does not check whether
the application can reach Supabase. The container health check checks only
HTTP responses from the two local processes. There is no tracked metrics,
tracing, alert, or explicit service-level objective configuration.

**Impact:** A process may be marked healthy while auth, data, storage, or
generation is unavailable; operators may learn of failures from users rather
than an alert.

**Fix:** Keep a lightweight liveness probe and add readiness that makes a
bounded, low-cost dependency check; avoid exposing secret/config detail in
health output. Emit structured logs with a request/correlation ID, record
provider latency/error/cost and credit transitions, add alerts for error rate,
queue/stuck-generation rate, provider spend, and database failures, and test
graceful shutdown and restart recovery.

Evidence: [health route](../backend/app/routers/health.py),
[FastAPI application](../backend/app/main.py), and
[container health check](../Dockerfile).

## Important conditional risks to resolve before a broad launch

### Public storage and user data

The `brand-assets` bucket is configured as public and has a public-read policy.
If logos or generated assets are meant to be private, use a private bucket and
short-lived signed URLs. If public URLs are an intentional product behavior,
state that clearly in UX/privacy terms and define deletion/retention behavior.
The product-assets bucket is private and has a separate service-only table
policy, which is a good control to preserve.

Evidence: [brand-assets bucket and policies](../supabase/migrations/00009_create_storage_bucket.sql)
and [product-assets privilege migration](../supabase/migrations/20261002120000_secure_product_assets.sql).

### Upload and image-processing limits

The existing audit identified upload handlers that read complete uploads
before checking size and perform image decode/processing in request handlers.
Revalidate those findings on this revision. Enforce a request-body cap at the
proxy/framework layer, read uploads in bounded chunks, validate actual image
format and pixel dimensions before expensive processing, and test malformed
and oversized files. Avoid blocking the async event loop with CPU-heavy work.

### Monetization and entitlement

The schema contains plans/subscriptions and Stripe identifier fields, but this
review did not find an end-to-end payment webhook/reconciliation path in the
tracked backend. If paid plans are in scope, implement signed webhook
verification, idempotent subscription transitions, failed-payment handling,
refund/credit adjustments, and reconciliation before charging users. If this
is intentionally a free beta, document that scope and do not imply paid
entitlements are operational.

### Product correctness and unfinished workflow leads

The dated [October 1 audit](./project-health-audit-2026-10-01.md) documented
additional potentially relevant issues around product-reference image
generation, caption persistence, account recovery, API middleware behavior,
asset cleanup, pagination, localization, and image cropping. That audit was
against commit `4691fad`, not this checkout. Treat it as a checklist to
revalidate, not as a claim that each issue remains present.

## Remediation plan

### Phase 0 — Stop unsafe exposure and confirm production state

1. Check the live database function ACLs for every `SECURITY DEFINER` routine.
2. If browser roles can execute credit RPCs, revoke access immediately with a
   forward-only migration; grant only the backend service role.
3. Confirm the currently deployed commit, hosting architecture, production
   provider configuration, and whether any paid traffic is enabled.
4. Until confirmed, do not enable unrestricted paid generation.

**Exit criteria:** Browser roles cannot execute service-only RPCs; deployment,
database, and provider configuration are known and recorded.

### Phase 1 — Protect money, quotas, and provider calls

1. Make commit/release transitions idempotent and validate active reservations.
2. Replace rate-limit read/modify/write with an atomic database operation.
3. Fix the Gemini aspect-ratio defect or disable that provider.
4. Reconcile stale generation/idempotency/reservation records after worker or
   process failure; verify provider retries cannot create duplicate charges.
5. Add concurrent and retry-focused database integration tests.

**Exit criteria:** Duplicate/replayed operations have no second effect;
parallel requests cannot bypass rate/quota limits; every configured provider
passes a real controlled integration test.

### Phase 2 — Make release artifacts secure and reproducible

1. Upgrade vulnerable frontend dependencies in a dedicated, tested change.
2. Pin/lock backend runtime dependencies and target Python 3.13 in CI.
3. Add CI gates for backend tests/Ruff, frontend tests/lint/build, npm audit,
   database migration checks, and container build.
4. Fix the Ruff undefined-name and other correctness/security findings before
   broad autofixes.
5. Build the container and scan dependencies/image layers; confirm no secrets
   enter build args, logs, or artifacts.

**Exit criteria:** CI is green from a clean checkout, dependency audit has no
unaccepted critical/high findings, and the tagged image is reproducible.

### Phase 3 — Establish one operational deployment

1. Choose single-container hosting or separate frontend/backend hosting and
   remove contradictory unused deployment instructions.
2. Use managed secrets for Supabase service key and AI provider keys; remove
   obsolete `SUPABASE_ANON_KEY` configuration.
3. Set actual production API URLs/CORS, health/readiness probes, restart
   policy, resource limits, and an always-on plan appropriate for the SLO.
4. Test deployment migrations, rollback/forward recovery, auth redirects,
   provider availability, and graceful termination in staging.

**Exit criteria:** Staging smoke tests pass with production-like settings and
the application can detect dependency outages.

### Phase 4 — Verify customer-facing and recovery behavior

1. Run two-user authorization/isolation tests against a staging Supabase
   project, including storage paths and admin permissions.
2. Run end-to-end login, create-brand, upload, generation, history, download,
   caption, deletion, and account-recovery journeys.
3. Test provider failure/timeouts, concurrent requests, process restart during
   generation, and storage cleanup failures.
4. Verify backup restoration and retention/deletion procedures; review
   accessibility, mobile/RTL behavior, and error localization.
5. For monetization, test webhook replay, payment failure, refunds, and
   credit-to-provider-cost reconciliation.

**Exit criteria:** Critical user journeys and recovery procedures pass in
staging; production owner accepts privacy, budget, and availability risks.

## Go/no-go criteria

Do not call this production-ready until all of the following are true:

- No public execution of privileged RPCs; proven from the live database ACLs.
- Credit, quota, and rate-limit actions are atomic, idempotent, and concurrency
  tested.
- Every advertised provider path works, or unsupported providers are disabled.
- No unaccepted critical/high dependency advisories remain.
- Reproducible Python 3.13/Node 20 build and CI gates are in place.
- One deployment architecture has verified environment, routing, secrets,
  readiness, restart behavior, and alerts.
- Staging isolation, upload, billing (if applicable), backup/restore, and
  critical end-to-end user journeys pass.
