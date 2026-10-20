# Generation reliability changes

## Scope

- Credit transitions: serialize reservation transitions and validate terminal
  states and matching retries. The migration was previously applied and its 25
  database regression scenarios passed; this publication does not reapply it.
- Backend: create generations before dependent foreign-key records, compensate
  failed admission using owned IDs, bind idempotency to user/brand/payload, and
  replay saved outcomes without intentionally redispatching the provider.
- Settlement: preserve provider output, complete settlement before publishing
  success, resume checkpointed settlement, attempt quota and credit cleanup
  independently, and retain unknown provider outcomes for explicit review.
- Frontend: retain a stable request intent across ambiguous retries and forward
  its idempotency key through the API proxy.
- Smoke tooling: validate the SDK's PNG multipart upload against the approved
  bucket/object path while retaining provider, redirect, and destination guards.

Backend changes share the endpoint and constraint-aware test fixtures, so they
are published as one coherent backend commit. Credit, frontend, and smoke
tooling changes are separate commits.

## Local verification on October 20, 2026

- Backend: 428 tests passed with external socket connections blocked.
- Frontend: 39 tests passed across seven files.
- Credit runner safety controls: 13 offline tests passed.
- Existing dependency deprecation and React act warnings remain.
- Credit migration SHA-256:
  `438140010C666FFA54BDC5FB5F87F4634766FA8478B0FAB9EB60F7CC0D5AB8FD`.

## Deployment and remaining validation

These application changes require a coordinated frontend/backend rollout:
the backend now requires an idempotency key. Publishing this branch does not
authorize deployment, migration execution, or live tests.

The previous synthetic generation smoke attempt stopped at the upload safety
guard. Its fixtures were cleaned up. The local multipart correction passes
offline tests, but a fresh live smoke attempt still requires separate approval.
Offline tests do not establish that the deployed generation or latency issues
are resolved.

Unknown provider outcomes are not automatically retried or settled. Hard process
crashes and prolonged database outages can still require manual recovery.

Backups, database snapshots, fixture manifests, account fingerprints, and
one-off execution/recovery scripts remain local. The reusable credit runner
ships with approval disabled; the smoke runner requires a separately approved
manifest. No credentials or live-run approvals are included.
