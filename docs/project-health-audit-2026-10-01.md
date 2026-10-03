# TREND project health audit — 2026-10-01

Repository snapshot: `4691fad`. Public deployment checked: https://trend-d5ba.vercel.app/.

**Assessment: the application builds and has useful automated coverage, but this snapshot is not ready for an unrestricted, company-funded generation trial.** Fix the generation contract/database issues, verify database isolation, and enforce usage controls before enabling public paid requests.

This is an audit, not an implementation change. Dashboard and generation source files were left unchanged so the frontend team can continue its work. No production records were changed, no accounts were created, and no paid generation requests were made. Production may run a different commit; source findings below refer to this checkout.

## Verification results

| Check | Result | Scope |
| --- | --- | --- |
| Backend `venv/Scripts/python.exe -m pytest -q` | **291 passed**, 4 deprecation warnings | Mocked/unit/contract tests; dummy Supabase configuration and blank generation key supplied |
| Frontend `npm run test -- --reporter=dot` | **24 passed, 1 failed** across 4 files | Failure: audience selection hint still says two groups while the test expects three; React `act` warnings also present |
| Frontend `tsc --noEmit --incremental false` | **Passed** | Static type checking |
| Frontend `npm run lint` | **Passed with 2 warnings** | Raw image elements in account profile/sidebar |
| Frontend `npm run build` | **Passed** | 15 static pages generated; image, webpack cache, and ambiguous Tailwind duration warnings |
| Backend Ruff | **Not run successfully** | Ruff is not installed in the existing virtual environment or declared in requirements |
| Production dependency audit | **6 affected package entries: 1 critical, 4 high, 1 low** | Official npm registry; local production dependency tree, not proof of live exploitability |
| Public `/`, `/login`, `/signup` | **HTTP 200** | HTTP checks only, not interactive browser validation |
| Public `/brands` | **307 to `/login`** | Expected unauthenticated page protection |
| Public `/api/health`, `/api/brands`, `/api/me` | **307 to `/login`** | Frontend middleware intercepts these; backend health remains unverified |

The configured npm mirror did not support audits. The successful audit explicitly used `https://registry.npmjs.org`; no registry settings or dependencies were changed. See `project-health-npm-audit-2026-10-01.json` for the captured advisory response.

## Fix before the first meaningful generation test

### H01 — Malformed Brand Kit query blocks generation and captions

- **Priority:** P1, functional blocker. **Owner:** backend.
- Evidence: `backend/app/routers/generations.py:89` selects `tagline, tone, audience, colors, avoid_words, statusو language`.
- The select expression contains an Arabic character instead of a comma. Also, the checked-in `brand_kits` schema has no `language` column. Replacing that character with a comma alone is insufficient.
- Both generation and caption routes call this helper. Once the provider key is configured, a real database call can fail before reaching OpenAI. The image route calls it before inserting the attempt, so this failure may not appear in history.
- Smallest correction: select the actual context fields through `status`; generation language already belongs to the brief/generation record.
- Verify: assert the selected column contract and perform a controlled read against the deployed schema. Current database mocks do not validate selected column names.

### H02 — Selecting an age range sends a value the backend rejects

- **Priority:** P1, functional blocker. **Owner:** frontend with backend contract review.
- Evidence: `frontend/components/generation/brief-audience-step.tsx:44` sends values such as `Under 18`, `18–24`, and `55+`; `backend/app/models/generation.py:165` accepts `under_18`, `18_24`, and `55_plus`.
- Both preview and generation consume the structured brief. Leaving age blank can work; choosing an offered age can produce HTTP 400 with a generic validation message.
- Correction: keep translated labels but send stable enum values; type the field as the same union as the API contract.
- Verify: submit each offered option through the request model/API. Do not rely only on component rendering tests.

### H03 — Product asset table has no checked-in row-level security

- **Priority:** P1 security; verify immediately on the deployed database. **Owner:** backend/Supabase.
- Evidence: `supabase/migrations/00019_create_product_assets.sql` creates a public-schema table without enabling RLS; no later checked-in migration enables it. Migration 00021 secures storage objects, not this table.
- Impact depends on deployed grants and any out-of-band policies. If exposed through the Data API with ordinary grants, direct clients can bypass FastAPI's ownership checks. Do not treat the private storage bucket as database-table protection.
- Correction: a forward migration enabling RLS and explicitly restricting client grants/policies. Since current product asset CRUD uses the service client, service-only table access is a possible minimal design. If direct client access is required, enforce both uploader identity and ownership of the referenced brand.
- Verify: inspect live RLS/grants; test anonymous access and two users without exposing real customer data. Live exposure was **not tested** in this audit.
- Reference: [Supabase row-level security](https://supabase.com/docs/guides/database/postgres/row-level-security).

### H04 — Shared paid generation has no per-user trial enforcement

- **Priority:** P1 before public trial. **Owner:** backend/product.
- Evidence: generation and caption routes in `backend/app/routers/generations.py` authenticate/authorize, then call the configured provider. No quota reservation, per-user rate limit, request idempotency, or trial ledger is present in the checked-in backend/migrations.
- Adding a shared key enables repeated paid requests by authenticated users once the functional blockers are fixed. A disabled button or dashboard count is not enforcement.
- Minimal internal demo: add a server-side tester allowlist before enabling the key. This allowlist does not currently exist.
- Minimal public trial: durable per-user allowance across all brands, atomic reservation before provider calls, bounded caption requests, rate/concurrency limits, and a defined refund policy for failures. Enforce the rules on every paid endpoint.
- Keep usage accounting separate from deletable generation history; otherwise deleting designs can reset a naive count. The current generation RLS also allows owners to insert/update/delete their records, so these records are not a trustworthy billing ledger.
- Verify: concurrent requests cannot exceed the allowance; a second brand, deleted history, and repeated caption generation do not reset or bypass it. Retrying an identical request must not create unintended duplicate charges.

### H05 — Production dependencies have current security advisories

- **Priority:** P1 dependency triage. **Owner:** frontend/deployment.
- `npm audit --omit=dev --registry=https://registry.npmjs.org --json` reports `next` critical; `nanoid`, `picomatch`, `postcss`, and `ws` high; `postcss-selector-parser` low.
- The project pins Next.js `14.2.35`. The captured report suggests a major-version change for some fixes. Do not run `npm audit fix --force` blindly during the team's UI work.
- Assess applicable advisories, upgrade on a coordinated branch, align Next/React/ESLint requirements, and rerun auth, middleware, build, and generation proxy checks. The audit's proposed version is not a migration plan.
- Maintainer advisories include [AVIF image optimization](https://github.com/vercel/next.js/security/advisories/GHSA-2xp9-vwfh-vxw4) and [Windows-hosted servers](https://github.com/vercel/next.js/security/advisories/GHSA-p293-qw3h-jr36). The latter is deployment-specific; do not claim it proves the Vercel deployment is exploitable. No exploitation was attempted.

## User flow and backend issues

| ID / priority | Evidence and impact | Smallest useful correction / owner |
| --- | --- | --- |
| H06 / P1 if product upload is exposed | `generations.py:375` validates the product asset and stores its ID, but `:466` never passes image bytes to OpenAI. `services/providers/openai_image.py` also accepts but ignores `reference_image`. Current generator UI does not submit a product asset ID. | Hide/defer the feature or complete image-reference handling end to end. Test actual product preservation. Backend + frontend. |
| H07 / P2 | `frontend/types/generation.ts` omits brief language, and the generator sends no language choice. Backend defaults to Arabic. Changing interface locale does not request English output. | Decide explicit content-language selection versus a documented Arabic-only release; keep content language distinct from interface locale. Frontend. |
| H08 / P2 | `generations.py:365` returns the caption without persistence. `use-caption.ts` and `caption-panel.tsx` keep results/edits in component state. Refresh loses them. | Persist the latest caption if library retrieval is promised, or label copy-only behavior clearly. Backend + frontend. |
| H09 / P2 | `brief-audience-step` limits selection to three; English/Arabic messages still describe two. This causes the single failing frontend test. | Agree on three, update both dictionaries and stale type comments, rerun the targeted test. Frontend. |
| H10 / P2 | `frontend/lib/validation.ts` accepts a nonempty 1–2 character custom goal/content/tone, while the backend requires at least 3. Backend returns generic payload errors for many fields. | Align field limits and return/render field-level validation feedback. Both teams. |
| H11 / P2 | `history/page.tsx:62` filters platform only within loaded pages. Matching older records can appear absent until more pages load. | Move filtering into the database query before pagination, or defer the platform filter. Both teams. |
| H12 / P2 | `error-message.tsx` sends `INVALID_KEY` users to a disabled provider-keys page, although generation uses a server-owned key. `error_mapping.py` maps every 429 to a retry-later rate-limit message, including billing/spend errors. | Tell users generation is temporarily unavailable; route diagnostic details to operators. Distinguish funding/permission errors from transient throttling. Both teams. |
| H13 / P2 | `verify-code/page.tsx:74` only resets UI on resend; it sends no email. Successful recovery verification offers a login link instead of leading to password reset. The main forgot-password page currently uses an email-link flow instead. | Choose and test one recovery path. Remove the unused OTP entry point or implement resend and reset navigation fully. Frontend. |
| H14 / P2 | Middleware includes `/api/*`. Live unauthenticated API requests return HTML redirects. `apiRequest` follows redirects and returns `null` for a non-JSON 200, potentially hiding session-expiry errors. | Let backend auth govern proxied APIs or return JSON 401 for API paths; reject unexpected successful HTML in the API client. Frontend. |
| H15 / P2 | `brands.py:246` deletes generation images/logos but never removes product-assets files before the brand's database cascade. Product-asset deletion logs storage failures and deletes the row anyway. | Clean up product files with a defined retry/error policy; test failures so inaccessible orphan files do not silently accumulate. Backend. |
| H16 / P2 | Product/logo/avatar uploads read the whole file before checking size; product assets decode before checking dimensions. DB constraints cap product dimensions but the handler lacks matching early checks. | Bounded reads, header/dimension checks before full decode, consistent 400/413 errors. Backend. |
| H17 / P2 | Synchronous Supabase queries/storage operations and Pillow processing run directly inside async handlers. Generation runs within the HTTP request; a worker restart can leave `processing` records hidden from history. | Offload blocking work and add stale-attempt reconciliation; keep background job infrastructure out of this week unless measured need demands it. Backend. |
| H18 / P2 | `resize_to_preset` center-crops a small set of provider aspect ratios into all target presets. Very wide banners can lose important text/content. | Manually inspect square, story, and banner output; define safe placement or a suitable sizing strategy before advertising every format equally. Backend + design. |

Additional UX observations from source review: the studio is still a placeholder; notification/subscription controls include unfinished actions; history includes hardcoded English; validation/provider errors are shown in English in Arabic UI. The mobile drawer sets `inert` when closed but lacks an evident focus trap/Escape handler when open. These need interactive keyboard/mobile verification, which was not performed here.

The agreed library design remains a good minimal scope: one page with successful designs and generation-history tabs, one shared detail page, automatic saving of successful images, and no claim of permanent audit history after deletion. Do not introduce published-content counts or readiness scores without real supporting data.

## Deployment and configuration

The live frontend is Vercel. `render.yaml` describes a separate Python backend, while Docker/AGENTS instructions describe a Bunny single-container deployment. The actual backend host was not supplied or verified. Do not configure Vercel as if it contains the FastAPI process.

| Location | Configuration for the current architecture |
| --- | --- |
| Vercel frontend | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `NEXT_PUBLIC_API_URL=/api`, `NEXT_SERVER_API_URL=https://<actual-backend-host>` |
| FastAPI host, e.g. Render if used | `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `GENERATION_PROVIDER=openai`, `GENERATION_MODEL=gpt-image-2`, `GENERATION_API_KEY=<secret>` |

`next.config.mjs` uses `NEXT_SERVER_API_URL` while creating rewrites at build time; the generation route uses it at runtime. Redeploy the frontend after changing these settings. For same-origin `/api` proxying, browser CORS does not require the Vercel origin on the backend. If calling the backend directly from browsers, configure its exact allowed origin.

Configuration findings:

- `render.yaml` does not declare generation settings. They must be set on the actual backend host; adding only `OPENAI_API_KEY` will not work with this resolver.
- `SUPABASE_ANON_KEY` has reappeared in `backend/app/config.py` and `render.yaml`, contrary to project instructions. It is not needed in the current backend.
- `MANAGED_GENERATION_ENABLED` and `MANAGED_*` settings are declared but not used by the generation resolver. They are not a working enable/disable switch.
- `/health` only reports that the application process is responding. It does not verify DB, storage, migrations, or provider configuration. Add non-secret readiness diagnostics; do not make paid requests from health checks.
- Docker does not supply the `NEXT_PUBLIC_API_URL` used by `frontend/lib/api.ts`; `.env.local` is excluded from the build context. A Docker build therefore needs `/api` explicitly configured or a safe application default.
- Makefile default image/container names contain spaces and uppercase letters (`TRENDY AI`); its unquoted Docker arguments do not provide usable defaults. This is a Docker-path issue, not evidence that Vercel is down.
- Python requirements have broad minimum versions and no lockfile. The existing Windows virtual environment targets Python 3.11, while Docker specifies 3.13. Passing this local suite does not establish reproducible production dependency resolution. Pin/lock the tested backend environment and declare dev tools separately.
- No `.github` CI directory was present. A required pre-merge build/test check would catch the currently failing frontend suite.
- Generated images and logos share a public bucket. They are accessible through public object URLs and public read policy; confirm this matches product privacy expectations. Private product-assets and avatars do not make generated outputs private.

## OpenAI trial setup and first test

The existing architecture is **TREND pays the provider using a server key**. Users do not need to supply keys. The image adapter uses HTTP directly, so installing the OpenAI Python SDK is not required for the current path.

The current image model is `gpt-image-2`; captions use the separately hardcoded text model `gpt-4o-mini` with the same key. Keep this distinction when checking project model permissions. The resolver currently supports OpenAI only even though some Gemini code remains in the repository.

1. Resolve H01/H02 and verify H03. Decide internal testers versus a public allowance and implement H04 accordingly.
2. Create a dedicated OpenAI API project/key, configure its billing, and verify access to the actual image and text models. Do not assume free image API credit. GPT Image access may require organization verification; verify account-specific access in the console. [Official image guide](https://developers.openai.com/api/docs/guides/image-generation), [configured image model](https://developers.openai.com/api/docs/models/gpt-image-2).
3. Configure spend alerts and an enforced project hard spend limit appropriate to the test. Alerts alone do not stop requests. Enforcement can lag tracked spending slightly, so this complements rather than replaces application quotas. [Official spend controls](https://developers.openai.com/api/docs/guides/spend-limits).
4. Set the three `GENERATION_*` values above in the **backend hosting environment**, never in a `NEXT_PUBLIC_*` variable, Git, browser storage, or chat. Restart/redeploy the backend.
5. Confirm Vercel API routing, remote Supabase migrations/buckets, and auth Site URL/allowed recovery redirects. Do not run a local Supabase instance for this project.
6. Using one controlled test account, create a brand, complete its kit, and generate one simple square design. Capture the generation ID, provider request ID, latency, storage success, and actual provider usage. There is no verified per-design price in this audit.
7. Generate one caption, copy it, download the image, reload, and check history/detail. Caption persistence currently fails the reload expectation unless H08 is implemented.
8. Try a selected age range, English content if supported, a portrait format, and one banner. Inspect Arabic text and logo placement manually; mocks cannot establish visual quality.
9. Use mocked/staging failure cases for missing key, refused prompt, provider timeout, spend exhaustion, storage failure, and concurrent quota requests. Avoid deliberately spending money to test exhaustion.

Do not automatically retry paid requests after a gateway timeout without checking whether the first attempt completed. A disconnected browser does not prove the provider did no work.

## Suggested work allocation this week

| Order | Backend / deployment | Frontend / design |
| --- | --- | --- |
| First | Fix Brand Kit query; secure product-assets table; implement internal tester gate or trial allowance | Fix age enum values; resolve audience copy/test mismatch; show service-unavailable messaging |
| Next | Verify runtime env, schema, buckets; triage dependency upgrade with frontend owner | Continue dashboard/generation work; coordinate Next upgrade separately; use shared library/detail components |
| Then | Persist captions if promised; repair storage cleanup; add useful readiness | Fix auth/API error flow and one password recovery path; localize errors and empty states |
| Before inviting testers | One controlled real image/caption test; two-user isolation and concurrent allowance checks | Verify mobile/RTL/keyboard, download, reload/history, return navigation, and failures |

## Limits of this audit

No authenticated deployed session, direct backend URL, Supabase administration access, provider key, or interactive browser tooling was used. Therefore production migrations/grants, backend routing after login, email delivery, exact deployed source revision, real provider access/billing, image quality, responsive rendering, and accessibility are not certified. No live load/security exploitation tests or Python dependency vulnerability scan were performed. The dependency audit and build apply to the local lockfile/source snapshot. These limits do not diminish the concrete source defects above, but they prevent claiming the deployed end-to-end flow works.
