# Credit database integration tests

`test-credit-concurrency.mjs` tests the deployed SQL functions, not mocked backend
responses. It requires Node.js 20+ and a Supabase management API access token in
`SUPABASE_ACCESS_TOKEN`. Do not put the token in source control or command arguments.

Run from the repository root, with the explicitly authorized project reference:

```text
node scripts/test-credit-concurrency.mjs --project-ref PROJECT_REF --allow-writes-to PROJECT_REF --approved-run APPROVED_RUN_ID
```

This is an opt-in, mutating integration test. The owner now designates the existing
project as controlled development. `credit-test-target.json` pins that reference,
but its `approvedRun` is null: execution is disabled until explicit approval of
the migration/test review package. Both project arguments and a matching
`--approved-run` identifier are required. Do not run the old staging workflow.
Prior approvals do not authorize another run. Operational backup and execution
evidence are retained privately and are not distributed with this runner.

The runner creates a unique disposable Auth row, profile, brand, two generation
rows, and a credit account per scenario. Users have no password or authenticated
session, use an `example.invalid` email, and do not receive email. No provider
API is called. Each credit account starts with a matching 100-credit grant.
Credit operations execute under `SET LOCAL ROLE service_role`.

For concurrency tests, a separate transaction locks only the disposable credit
account. Two requests start on separate database sessions. The runner observes
both waiting for locks before cancelling only its uniquely named sleeping
blocker query. This releases the lock by rollback. Queries have bounded timeouts.
Failure to observe both waiters is a synchronization failure, not proof of a
product race. Two active reservations are used for terminal races so an incorrect
second transition cannot be hidden by the account's reserved balance reaching zero.

Tests cover duplicate reserve/commit/release, both sequential terminal conflicts,
missing reservations, concurrent duplicate requests, and concurrent commit/release.
Matching reserve retries must now return the prior receipt. Mismatched requests
must fail without mutation. Raw constraint errors fail retry behavior checks.
Balance safety is recorded separately from retry-response correctness.

The runner saves a UUID-named JSON report before the first mutation, including
exact fixture IDs. It deletes only those synthetic users with an exact UUID and
email match, relying on schema cascades, then verifies zero users, profiles,
brands, generations, credit accounts, and ledger entries for the fixtures.
Cleanup runs in `finally`, including after test failures. Abrupt process termination
or a network outage can prevent cleanup: inspect the saved fixture IDs and verify
or remove only those records before another run. No wildcard cleanup is used.

The exit status is nonzero for failed checks or incomplete cleanup. Test results
do not certify application-level auth, provider retry behavior, quota correctness,
or every possible concurrency schedule.
