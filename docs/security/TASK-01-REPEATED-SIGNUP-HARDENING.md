# Task 01: Repeated-Signup Hardening

## Executive summary

Task 01 fixes an account-takeover vulnerability in the custom email/password authentication flow. Previously, anyone who submitted another signup request for an existing unverified email address could replace that account's password hash and, when supplied, profile name. If the mailbox owner later verified the account with an earlier code, the attacker-selected password became the credential for the verified account.

The fix makes repeated signup for an unverified address a verification-code resend operation only. It never changes the stored password or profile. Verification-code issuance and email verification now serialize on the PostgreSQL user row, and verification email delivery starts only after the code-issuance transaction has committed.

This change addresses the confirmed repeated-signup vulnerability. It is not a claim that the full authentication system is secure or production-ready.

## Root cause and attack scenario

The old `signup` service looked up the email and, when it found an unverified user, called `update_unverified_user`. That repository operation replaced the existing password hash and optionally changed the profile name without proof that the caller controlled the mailbox.

An attack required all of the following:

1. An account existed for the target email.
2. The account had not completed email verification.
3. The attacker knew the email and submitted signup again with an attacker-selected password.
4. The mailbox owner subsequently completed verification, potentially with a code issued before the attack.

The attacker did not need access to the mailbox to replace the credential. The issue did not apply in the same way to already verified accounts because those requests returned `409 EMAIL_ALREADY_REGISTERED`.

## Files and responsibilities

- `backend/app/services/auth_service.py`: preserves credentials during repeated signup, distinguishes the expected case-insensitive email uniqueness conflict from other database failures, delegates code eligibility and cooldown decisions to the repository transaction, and finalizes email verification atomically.
- `backend/app/repositories/users.py`: implements locked code issuance and atomic verification using PostgreSQL transactions and `SELECT ... FOR UPDATE` on the user row.
- `backend/tests/test_auth_endpoints.py`: covers the service and endpoint contracts, including credential preservation, cooldown behavior, duplicate-signup races, unrelated integrity errors, and verification-disabled mode.
- `backend/tests/test_postgres_integration.py`: exercises the real PostgreSQL locking, uniqueness, and race behavior and uses the guarded disposable-database setup.
- `backend/postgres_test_safety.py`: validates the destructive integration-test target before opening a connection or rebuilding its `public` schema.
- `backend/tests/test_postgres_test_safety.py`: proves that unsafe, ambiguous, malformed, unsupported, and application-equivalent database targets fail before DSN conversion or connection.

## Implemented behavior

### Signup and duplicate handling

For a new email, signup hashes the submitted password and attempts to create the user. The existing case-insensitive unique index, `uq_users_email_ci`, selects the winner if two first-time signups race. The losing request handles only a violation of that named constraint, reloads the winner, and does not modify the winner's password or name. Any unrelated `IntegrityError` is re-raised.

For an existing verified email, the API continues to return `409 EMAIL_ALREADY_REGISTERED`.

For an existing unverified email, the API preserves the existing password hash and profile name. It retains the existing `201` response contract and treats the request as an attempt to resend the verification code.

When `AUTH_REQUIRE_EMAIL_VERIFICATION=false`, signup still creates and signs in a first-time user without sending a code. Any existing email returns `409`; a concurrent duplicate-email loser also returns `409`, and no existing credential is changed.

### Verification-code lifecycle and cooldown

Code issuance locks the associated user row and rechecks eligibility inside the same transaction. Verification codes are allowed only for unverified users, while password-reset codes are allowed only for verified users.

The repository reads the most recent code while holding the user lock. During the 60-second cooldown it returns `cooldown`, leaves the existing code untouched, and causes no email to be sent. After the cooldown, it marks older unconsumed codes as consumed and inserts one new code in the same transaction.

The service returns a pending email only when the repository reports `issued`. The router sends that email after the service call returns, which means the database transaction and row lock have already been released. An SMTP failure can therefore leave a committed code that was not delivered; the user can request another code after the cooldown.

### Email verification transaction

The service first validates the submitted code and then calls `consume_verification_code_and_mark_verified`. That repository method locks the same user row used by issuance, rechecks that the user is still unverified, consumes the selected unconsumed verification code, and sets `email_verified_at` in one transaction.

Because issuance and verification acquire the same row lock, a reissue-versus-verification race has only safe serialized outcomes:

- Verification wins: the code is consumed, the user becomes verified, and later issuance returns `ineligible`.
- Reissue wins: the old code is invalidated and replaced; verification of the old code fails and the account remains unverified.

Wrong-code attempts are still counted atomically by the existing attempt counter. A concurrent transition may consume an attempt before final verification loses a race, but it cannot verify with an invalid or superseded code.

## Behavior before and after

| Scenario | Before Task 01 | After Task 01 |
| --- | --- | --- |
| Repeated signup, verified email | `409 EMAIL_ALREADY_REGISTERED` | Unchanged |
| Repeated signup, unverified email | Replaced password and optional name | Preserves password and name; resend semantics only |
| Repeat within 60 seconds | Returned `201`; credential could already be replaced | Returns `201`, sends no email, and keeps the current code valid |
| Repeat after 60 seconds | Replaced credentials and code | Preserves credentials; atomically invalidates the old code and issues a new one |
| Concurrent first signup | Unique constraint selected a winner, but duplicate handling was broad | Named unique constraint selects a winner; loser never changes winner credentials; unrelated integrity failures propagate |
| Verification racing with reissue | Operations were not serialized on the account | Both operations lock the same user row and produce a safe serialized result |
| Verification disabled | First signup creates a session; existing-account behavior needed race coverage | Contract preserved; existing accounts remain unchanged and return `409` |

## PostgreSQL regression coverage

Five new PostgreSQL tests provide database-level coverage:

1. `test_verification_code_issuance_is_serialized_per_user` starts two simultaneous issuance attempts and verifies that one issues while the other observes cooldown, leaving one active code.
2. `test_verification_and_reissue_race_has_one_safe_outcome` races email verification against code replacement and accepts only the two safe serialized outcomes.
3. `test_repeated_signup_keeps_original_credentials_in_postgres` proves that a repeated signup cannot change the original password hash or name.
4. `test_concurrent_first_signups_keep_one_winners_credentials` races two initial signups and verifies that exactly one credential/name pair wins intact.
5. `test_signup_without_verification_still_rejects_existing_user_in_postgres` verifies that verification-disabled mode returns `409` for an existing address without changing its credentials.

The migration assertion was also updated to expect both `0001_baseline.sql` and `0002_kit_complete_without_tone.sql` on a fresh database.

## Disposable test database guard

The PostgreSQL integration fixture rebuilds the target's `public` schema with `DROP SCHEMA public CASCADE`. Before DSN conversion, connection, or destructive SQL, `postgres_test_safety.py` requires all of the following:

- `ALLOW_DESTRUCTIVE_TEST_DB=1` is explicitly set.
- The driver is exactly `postgresql` or `postgresql+psycopg`.
- The host is exactly `127.0.0.1` or `localhost`.
- The port is exactly `55432`.
- The database is exactly `trendy_integration_test`.
- The user is exactly `trendy_test`.
- A password is present.
- No URL query parameters are present.
- The target is not equivalent to the application's `DATABASE_URL`; the two loopback spellings are normalized and password differences are ignored for this comparison.
- If a provided `DATABASE_URL` is malformed or uses an unsupported driver, execution fails closed.

Error messages do not include credentials. These restrictions are intended for the dedicated disposable PostgreSQL 17 container used by this test procedure, not for an existing local, staging, or production database.

## Validation evidence

The project owner reported the following manual results from VS Code PowerShell after the final safety-guard patch:

- PostgreSQL 17 integration suite: **25 passed**, including the five tests listed above.
- Complete backend suite: **511 passed**, with **5 non-blocking deprecation warnings**.
- Ruff on the PostgreSQL safety-guard files: **passed**.
- `git diff --check`: **passed**.
- The disposable PostgreSQL container was removed successfully.
- No production database, deployment, or existing container was modified.

During the final handoff session, the reviewing agent personally verified the branch and diff, fetched the remote branch reference, confirmed that local and remote were at the same commit, ran the targeted Ruff check on the guard files successfully, and ran `git diff --check` successfully. Earlier agent-side pytest attempts were blocked by an incomplete local virtual environment and are not represented as agent-executed passing tests. The database and full-suite counts above are user-reported results.

## Known limitations and out-of-scope risks

- Authentication endpoints do not have a general request rate limiter. Code cooldown and per-code attempt limits reduce specific abuse paths but do not replace per-IP and per-account signup, login, resend, and recovery rate limits.
- Session JWTs are stateless and have no server-side revocation list or token version. Logout clears the client cookie but does not invalidate a copied token before its expiry.
- The approved `409 EMAIL_ALREADY_REGISTERED` response for verified accounts permits email-address enumeration through signup.
- Email delivery is not transactional with database state. A committed code may not be delivered if SMTP fails after commit.
- This task does not change password policy, MFA, bot protection, audit-event coverage, secret rotation, or broader authorization behavior.
- The integration guard protects this fixture's destructive path. It does not make arbitrary developer database commands safe.

## Deployment and post-deployment checks

No schema migration is required for this task. Deployment should use the normal reviewed Coolify/PostgreSQL release process, preserve the case-insensitive `uq_users_email_ci` constraint, and verify that production has a valid `AUTH_JWT_SECRET` and email configuration.

Recommended post-deployment smoke tests should use a dedicated test mailbox and should avoid real customer accounts:

1. Sign up once and confirm the API returns `201` with `verification_required=true`.
2. Repeat signup within 60 seconds with a different password/name; confirm `201`, no additional email, the first code remains valid, and the original password works after verification.
3. With a fresh account, repeat signup after 60 seconds; confirm a new email is sent, the old code fails, the new code succeeds, and the original password/name remain unchanged.
4. Confirm an already verified email still returns `409 EMAIL_ALREADY_REGISTERED`.
5. Confirm login, session retrieval, logout-cookie clearing, resend, and password recovery retain their expected contracts.
6. Review application and SMTP logs for unhandled integrity errors, transaction failures, duplicate sends, or credential data in logs.

These checks should be performed through the deployed public API while monitoring the release. They must not use destructive database commands.

## Rollback considerations

There is no database migration to reverse. A code rollback is mechanically simple, but rolling back to the previous implementation restores the account-takeover vulnerability and should be avoided. Prefer a forward fix or temporarily restrict signup if a release problem affects this path.

The repository and service changes must be rolled back together because their function contracts changed. The test fixture safety guard is independent of runtime application behavior and should remain in place even if application changes require a follow-up.

No production deployment or live smoke test was performed as part of Task 01 or this handoff.
