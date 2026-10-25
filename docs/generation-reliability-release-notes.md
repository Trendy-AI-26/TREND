# Generation reliability changes

Port of PR #82 (`fix/generation-reliability-mvp-20261020`) onto the plain-Postgres
stack of `coolify-postgres` (SQLAlchemy/psycopg access through `app/db` and
`app/repositories`, S3-compatible storage, no Supabase).

## Scope

- **Credit transitions (migration `0003`).** Reserve, commit and release lock the
  user's `credit_accounts` row first, so concurrent transitions for one account
  queue instead of racing; different users stay concurrent. Matching retries are
  idempotent. A conflicting terminal state, a mismatching receipt or an
  inconsistent ledger is rejected without changing anything. Only function bodies
  are replaced: names, signatures and return types are unchanged.
- **Admission.** The `generations` row is created first, then the per-user lock,
  then the `idempotency_records` row that references the generation. A failed
  admission is compensated using the preallocated generation ID only (never by
  user or key alone), and each cleanup step runs even if another fails. No quota,
  credit or provider work happens before admission succeeds.
- **Idempotency.** The key is bound to user, brand and the validated payload.
  Reusing a key with another brand or payload returns `409 IDEMPOTENCY_KEY_REUSED`.
  A retry replays the saved outcome and never calls the provider again.
- **Settlement.** The provider output is saved and a checkpoint is persisted
  before credits and quota are committed. Success is published (generation row and
  idempotency record) only after both commits return. A replay with the same key
  resumes a checkpointed settlement. Quota and credit cleanup on failure are
  attempted independently.
- **Unknown outcomes.** If the provider (or a reservation) may have acted, quota,
  credits, lock and generation row are kept for review and the request is not
  restarted automatically.
- **Generation lock.** An expired lock is only taken over when the generation that
  owned it is finished (or no longer exists). An expired lock whose generation is
  still `pending`/`processing` needs recovery and is not taken over. Only a
  primary-key conflict is reported as "in progress"; other database faults surface
  as real errors.
- **Frontend.** A stable generation intent and `Idempotency-Key` are kept across
  ambiguous retries (network failure, "in progress", settlement pending) and
  rotated only after a definite server answer or an explicit "generate another".
  The Next.js route handler forwards `Cookie`, `Authorization` and
  `Idempotency-Key`.

## Deployment

- **Migration `0003_serialize_credit_reservation_transitions.sql` applies
  automatically on the next deploy** (the migration runner applies pending files
  at start-up, each in its own transaction). It only replaces three function
  bodies and changes no data. `0001` and `0002` are untouched.
- **Breaking API change: the backend now requires the `Idempotency-Key` header on
  `POST /brands/{brand_id}/generate`** (16 to 128 characters). Deploy frontend and
  backend together: an older frontend that does not send the header gets
  `400 IDEMPOTENCY_KEY_REQUIRED`. Any other client of this endpoint must send a
  fresh key per request and reuse it only to retry that same request.

### Error codes

| Code | HTTP | Meaning / client action |
| --- | --- | --- |
| `IDEMPOTENCY_KEY_REQUIRED` | 400 | Header missing. A header outside 16-128 characters is a `400 VALIDATION_ERROR`. |
| `IDEMPOTENCY_KEY_REUSED` | 409 | Same key with a different user/brand/payload. Use a new key. |
| `GENERATION_IN_PROGRESS` | 409 | Same key still processing, or another generation holds the lock. Retry with the same key. |
| `GENERATION_SETTLEMENT_PENDING` | 503 | Output saved, finalization pending. Retry with the same key to resume. |
| `GENERATION_OUTCOME_UNKNOWN` | 503 / 409 | Provider outcome needs review. Do not retry automatically. |
| `GENERATION_ADMISSION_FAILED` | 503 | Admission failed and was rolled back. Retry with the same key. |
| `GENERATION_ADMISSION_CLEANUP_FAILED` | 503 | Admission could not be fully rolled back; needs review. |
| `IDEMPOTENCY_CREATE_FAILED` | 500 | The idempotency record could not be created. |

Saved failures replay with their original status and code (for example
`INSUFFICIENT_CREDITS` 402, `GENERATION_LIMIT_REACHED` 402, `TRIAL_EXPIRED` 403,
provider errors 502).

New user-facing strings (`GENERATION_SETTLEMENT_PENDING`,
`GENERATION_OUTCOME_UNKNOWN`, `GENERATION_INTENT_UNRESOLVED`) are in both
`frontend/messages/ar.json` and `en.json`.

## Not ported

The PR's `scripts/mvp-generation-smoke.py`, its upload-guard test and the credit
concurrency scripts (`scripts/test-credit-concurrency.mjs`, `credit-scenario*`,
`credit-test-target*`, `credit-concurrency-tests.md`) are tied to Supabase (project
host and PostgREST/Storage request guards, Supabase Management API token). They
cannot run against `DATABASE_URL` plus S3 and are not included.

## Verification status

Only static checks were run for this port (ruff `F,E9`, backend import, frontend
lint, `tsc --noEmit`, i18n key parity). The backend and frontend test suites and
the frontend build were not run, and the migration was not applied to a live
database. The new `0003` behaviour is covered by the Postgres integration tests
in `backend/tests/test_postgres_integration.py`, which need a real database.

Unknown provider outcomes are not automatically retried or settled. Hard process
crashes and prolonged database outages can still require manual recovery.
