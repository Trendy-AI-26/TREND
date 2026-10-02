# Retained health audit fixes — 2026-10-02

Updated scope following the requested rollback: retain H03 database isolation,
H02 age values, and the existing Brand Kit corrections. Remove the H04 internal
tester gate and defer H05 dependency upgrades. H14 API authentication behavior
remains unchanged.

## Retained changes

- Age labels remain translated; submitted values match all six backend enum
  values. The frontend field uses a TypeScript union, with frontend and backend
  regression tests for each option.
- The corrected Brand Kit query in `backend/app/routers/generations.py` is
  preserved. It selects existing context fields including `industry` and `status`.
- `20261002081029_require_industry_for_new_brand_kit_completions.sql` is retained.
  It was recovered from remote migration history, not newly applied in this work.
  It requires industry, audience and colors for newly completed/updated kits,
  while preserving legacy rows via a NOT VALID constraint.
- `20261002120000_secure_product_assets.sql` remains applied remotely. It enables
  and forces RLS, revokes table privileges from PUBLIC/anon/authenticated, and
  grants CRUD to the service role. FastAPI ownership checks and storage policies
  are unchanged.

Remote verification with `supabase/tests/product_assets_service_only.sql` passed
before this rollback: client roles cannot read the table, and the service role
retains CRUD privileges. Verification used metadata and zero-row queries without
customer data changes. This rollback does not modify the remote database.

## Reverted changes

- Removed `GENERATION_TESTER_USER_IDS`, the tester-access service, endpoint gates,
  gate-specific test setup/tests, and deployment configuration.
- Restored the original frontend package manifest and lockfile: Next.js 14.2.35,
  React 18, and the previous ESLint, Vitest, Vite and PostCSS dependency tree.
- Removed upgrade overrides and restored the original route parameters,
  TypeScript configuration, and link changes made for upgrade compatibility.

Image and caption requests again use the existing authentication and brand
ownership checks, without a tester allowlist or new usage quota.

## Security audit and deployment

The previous zero-vulnerability result applied to the upgraded dependency tree
and is no longer a claim about this checkout. That superseded report was removed.
Dependency security upgrades are deferred by explicit request; the original
October 1 audit remains available for reference.

The retained application changes are local and require deployment. The database
security fix is already live. No paid generation requests were used for testing.

## Post-rollback verification

- Backend: **301 tests passed**, with four existing deprecation warnings.
- `npm ci` installed the original lockfile successfully. Installed versions are
  **Next.js 14.2.35**, **React 18.3.1**, and **React DOM 18.3.1**.
- Production dependency audit: **6 affected package entries** — 1 critical,
  4 high and 1 low. The fresh report is saved as
  `project-health-npm-audit-2026-10-02-rollback.json`. These findings are deferred
  as requested; the dependency files were not modified to resolve them.
- Frontend: **31 tests passed**. The production build on Next.js 14.2.35 passed,
  including lint and TypeScript validation. Existing React `act` test warnings,
  two raw-image lint warnings, and non-fatal webpack/Tailwind warnings remain.
