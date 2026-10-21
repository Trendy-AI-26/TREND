# Deploy TRENDY AI on Coolify

## Prerequisites and DNS

The upstream `minio/*` images were withdrawn from Docker Hub; this bundle uses `pgsty/silo`, as does [Coolify's MinIO template](https://raw.githubusercontent.com/coollabsio/coolify/main/templates/compose/minio.yaml), and `pgsty/mc` for initialization, both pinned to `RELEASE.2026-10-18T00-00-00Z`.

Use a Coolify server with Docker Compose v2+, enough disk for PostgreSQL and MinIO, and enough RAM to build Next.js (4 GB or more recommended). Back up existing data before deploying. The application uses one image containing Next.js and FastAPI, plus PostgreSQL 17, MinIO, and an idempotent bucket-initialization job.

Point `app.example.com` and `s3.example.com` A/AAAA records at the Coolify proxy. Optionally point `console.example.com` there too. Open public ports 80/443, not 5432, 8000, 9000, or 9001. Remove an AAAA record if the server cannot serve IPv6. Wait for DNS before requesting HTTPS certificates.

## Create the resource

1. In the target Coolify project/environment, choose **New**, select the Git repository source, and authorize access if private.
2. Select the desired deployment branch. Changes must exist in the remote repository before Coolify can deploy them; local edits are not uploaded by this guide.
3. Choose **Docker Compose** (in newer UI: Build pipeline > Compose). Set Base Directory to `/` because TREND is its own repository. Set Docker Compose Location to `/docker-compose.coolify.yml`.
4. Save/load the definition, then set the Environment Variables below. Plain Compose variables are intentional: no generated-domain convention is required. Secrets belong in Coolify, never in Git. Do not change credentials on an existing data volume without first changing the database/storage account itself.
5. Under Domains add `https://app.example.com:3000` for service `app`, and `https://s3.example.com:9000` for service `minio`. Optionally add `https://console.example.com:9001` for `minio`. The suffix selects the internal port; browsers still use HTTPS port 443. Never route a domain to PostgreSQL or backend port 8000.

These steps and `${VAR}`, `${VAR:-default}`, `${VAR:?}` behavior follow the official [Coolify Docker Compose guide](https://coolify.io/docs/applications/builds/docker-compose), reached from the [documentation home](https://coolify.io/docs). Build/runtime scope is documented in [Environment Variables](https://coolify.io/docs/applications/configuration/environment-variables). The Compose definition, not undocumented magic variables, is authoritative here.

## Environment variables

Generate separate secrets:

```bash
openssl rand -hex 32  # POSTGRES_PASSWORD (URL-safe hex)
openssl rand -hex 32  # MINIO_ROOT_PASSWORD
openssl rand -hex 32  # AUTH_JWT_SECRET
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Run the Fernet command in an environment with `cryptography` installed, e.g. the backend virtualenv. Use only URL-safe alphanumeric PostgreSQL credentials because Compose inserts them directly into DATABASE_URL (otherwise percent-encode the URL password separately and adapt the manifest). Keep the encryption key backed up: losing it makes stored provider keys unreadable.

Every editable variable in the production manifest is listed below. Variables with defaults need no override. Empty generation keys disable real provider calls; they do not block account/brand setup.

| Variable | What to enter / default |
|---|---|
| `POSTGRES_DB` | `trendy`; database name, simple identifier |
| `POSTGRES_USER` | `trendy`; database user, simple identifier |
| `POSTGRES_PASSWORD` | Required independent random hex secret |
| `MINIO_ROOT_USER` | Required private admin/access-key name, e.g. `trendy-storage-admin` |
| `MINIO_ROOT_PASSWORD` | Required independent random secret, at least 8 characters |
| `MINIO_BROWSER_REDIRECT_URL` | Empty unless console is exposed; then `https://console.example.com` |
| `S3_PUBLIC_BASE_URL` | Required `https://s3.example.com`, no bucket/path or trailing slash; also feeds build arg `NEXT_PUBLIC_STORAGE_PUBLIC_URL` |
| `S3_REGION` | `us-east-1` |
| `STORAGE_BUCKET` | `brand-assets`; anonymous download only |
| `AVATARS_BUCKET` | `avatars`; private |
| `PRODUCT_ASSETS_BUCKET` | `product-assets`; private; all three names must differ |
| `AVATAR_MAX_BYTES` | `2097152` |
| `PRODUCT_ASSET_MAX_BYTES` | `10485760` |
| `AUTH_JWT_SECRET` | Required random secret; same environment reaches backend and Next middleware; never use a NEXT_PUBLIC prefix |
| `AUTH_SESSION_TTL_SECONDS` | `604800` (seven days) |
| `AUTH_REQUIRE_EMAIL_VERIFICATION` | `true` (default) requires the emailed code at sign-up and login; `false` = instant sign-up/login without email (use until SMTP works). Switching back to `true` asks unverified users to verify on their next login |
| `APP_ENCRYPTION_KEY` | Required generated Fernet key, not an arbitrary password |
| `ADMIN_EMAILS` | Comma-separated admin addresses, compared case-insensitively |
| `CORS_ORIGINS` | Required exact app origin, e.g. `https://app.example.com` (no :3000); comma-separated if several |
| `SMTP_HOST` | SMTP server hostname; empty logs verification/reset codes, development only |
| `SMTP_PORT` | `587` |
| `SMTP_USERNAME` | SMTP account username, or empty if relay needs none |
| `SMTP_PASSWORD` | SMTP account password, or empty if relay needs none |
| `SMTP_FROM` | Verified sender, e.g. `TRENDY AI <no-reply@example.com>` |
| `SMTP_STARTTLS` | `true`; STARTTLS on port 587 (implicit TLS/465 is not supported by this setting) |
| `GENERATION_PROVIDER` | `openai` |
| `GENERATION_MODEL` | `gpt-image-2` (image model) |
| `GENERATION_API_KEY` | Server-only real provider key when generation is needed |
| `IMAGE_PROVIDER` | `openai`; compatibility fallback |
| `TEXT_PROVIDER` | `openai` |
| `OPENAI_API_KEY` | Empty; compatibility key fallback |
| `OPENAI_IMAGE_MODEL` | `gpt-image-2`; compatibility model fallback |
| `OPENAI_TEXT_MODEL` | `gpt-4o-mini` |
| `MANAGED_PROVIDER` | Empty; legacy compatibility override |
| `MANAGED_API_KEY` | Empty; legacy compatibility override |
| `MANAGED_MODEL` | Defaults to `OPENAI_TEXT_MODEL` (`gpt-4o-mini`); legacy caption-model override; must not be empty because an empty override masks the text-model fallback |
| `GENERATION_CREDIT_COST` | `1` |
| `FREE_TRIAL_DAYS` | `14` |
| `DAILY_GENERATION_LIMIT` | `3` |
| `CAPTION_CREDIT_COST` | `0` |
| `GENERATION_RATE_LIMIT` | `5` |
| `GENERATION_RATE_WINDOW_SECONDS` | `60` |
| `GENERATION_LOCK_TTL_SECONDS` | `180` |
| `ALLOWED_IMAGE_TYPES` | `image/png,image/jpeg,image/webp` |
| `NEXT_SERVER_API_URL` | Leave `http://127.0.0.1:8000`; both processes share a container; used at build and runtime |

Fixed/derived container configuration: `DATABASE_URL=postgresql+psycopg://<POSTGRES_USER>:<POSTGRES_PASSWORD>@postgres:5432/<POSTGRES_DB>`, `S3_ENDPOINT_URL=http://minio:9000`, `S3_ACCESS_KEY_ID=MINIO_ROOT_USER`, `S3_SECRET_ACCESS_KEY=MINIO_ROOT_PASSWORD`, `APP_ENV=production`, `AUTH_COOKIE_SECURE=true`, `RUN_MIGRATIONS_ON_STARTUP=false`, `BACKEND_HOST=127.0.0.1`, `BACKEND_PORT=8000`, `FRONTEND_PORT=3000`. HOST/PORT from the backend example are local-development settings, not container controls. The entrypoint always runs migrations, so a second API startup migration is unnecessary. Next inherits `AUTH_JWT_SECRET` unchanged. No secret is supplied as a Docker build arg.

## First deploy, admin, and SMTP

Deploy and inspect Deployment/Runtime Logs. PostgreSQL and MinIO become healthy, then minio-init creates buckets and explicitly applies anonymous download only to brand-assets (private policies to the other two). Keep bucket names distinct. The app waits for all three dependencies. Before starting uvicorn, its entrypoint runs `python -m app.db.migrate` from `/app/backend`; any migration error stops startup. SQL files ship in the image. Advisory locking, checksums, and the migration ledger make repeated runs safe, not destructive.

Set `ADMIN_EMAILS` before deployment, sign up that exact address, and verify its emailed code. This makes the first admin; no database role editing is needed. For production configure SMTP and a verified sender first, then test verification and password reset. Empty SMTP_HOST writes codes to logs: never leave it empty for public production use or expose those logs.

Verify signup, emailed verification, dashboard, logo upload/public image access, logout, and password reset. Test the app from HTTPS, not the internal HTTP address. Check MinIO private buckets deny unsigned access. Keep the MinIO console unexposed unless required; its credentials are privileged. This baseline shares MinIO root credentials with the backend; a hardened installation should provision a least-privilege application storage account before changing that wiring.

## Backups and restores

Back up daily to encrypted off-server storage. A named Docker volume is persistence, not a backup. Take a logical database backup (run on the server in the deployed Compose context):

```bash
docker compose -f docker-compose.coolify.yml exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > trendy.dump
```

Use the resource's actual Compose project/context in Coolify's server terminal. Also back up the entire MinIO data volume with a filesystem snapshot while MinIO is stopped, or use a versioned external MinIO mirror/backup tool. Coordinate database and object snapshots to avoid dangling references. Preserve Coolify env/secrets separately, especially APP_ENCRYPTION_KEY. Test restoration into isolated volumes: restore PostgreSQL with `pg_restore`, restore MinIO data, apply original credentials and encryption key, then check image URLs and login. Do not run `docker compose down -v` on live data.

## Updating

Back up first, review new SQL/checksums, deploy the desired remote revision through Coolify, and inspect logs. Never edit an already-applied SQL migration; add a new one. Redeploy rebuilds Next.js: changing the S3 public domain or backend rewrite requires a rebuild, not just restarting the process. Data volumes persist across normal redeploys. A code rollback does not roll back the database; plan compatible migrations or restore a tested backup.

## Troubleshooting

- Cookie not set/sent: confirm HTTPS and `AUTH_COOKIE_SECURE=true`; plain HTTP development needs false. Use one hostname throughout and inspect Set-Cookie on the `/api/auth/verify-email` response.
- Images not loading: check browser-reachable `S3_PUBLIC_BASE_URL`, matching build-time `NEXT_PUBLIC_STORAGE_PUBLIC_URL`, S3 domain routing to 9000, bucket existence, and anonymous download policy on brand-assets only. Signed URLs must use the public domain without rewriting their path/host.
- 401 loops/dashboard redirects: confirm identical AUTH_JWT_SECRET for backend and Next; invalidate stale cookies after secret rotation and check clock synchronization.
- Startup failure: inspect migration output, PostgreSQL health/credentials and persisted-volume credentials. Missing required env fails before processes start. Do not delete volumes as a workaround.
- minio-init failure: check MinIO credentials, distinct valid bucket names, and healthcheck; rerun the idempotent job after correction.
- SMTP errors/no mail: verify STARTTLS/587, credentials, verified sender and provider SPF/DKIM settings; review backend logs without exposing codes or passwords.

## Compose syntax checks without a daemon

From TREND/, the exact PowerShell commands used with non-production placeholders are:

```powershell
$env:POSTGRES_PASSWORD='placeholder-postgres-password'; $env:MINIO_ROOT_USER='placeholder-minio-user'; $env:MINIO_ROOT_PASSWORD='placeholder-minio-password'; $env:AUTH_JWT_SECRET='placeholder-auth-secret-32-characters'; $env:APP_ENCRYPTION_KEY='MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA='; $env:S3_PUBLIC_BASE_URL='https://s3.example.com'; $env:CORS_ORIGINS='https://app.example.com'; docker compose -f docker-compose.coolify.yml config -q
```

In a fresh shell (no variables required for local defaults):

```powershell
docker compose -f docker-compose.yml config -q
```

Syntax validation does not prove image builds, image availability, service healthchecks, or actual Coolify routing. A real Docker deployment is still required before production.
