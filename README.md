# TRENDY AI

Multi-brand social image generator. Built with Next.js 14, FastAPI, PostgreSQL, and S3-compatible storage.

## Project overview

**TRENDY AI** is an Arabic-first brand studio for small businesses, creators, marketers, and agencies that need consistent, professional visual content for social media. Instead of asking users to write complex AI prompts from scratch, the product remembers each brand's identity and guides the user through a structured campaign brief. It then combines the brief, Brand Kit, platform requirements, logo rules, and selected AI provider to produce a platform-ready visual asset.

The product is designed around a simple idea: **the output should look like it belongs to the brand, not like a generic AI-generated image**. Each workspace can contain one or more brands, and every brand can have its own name, tagline, tone, audience, colors, logo, and visual directions to follow or avoid. This context is reused across generations so that the user does not have to repeat the same instructions for every campaign.

## The problem TRENDY AI solves

Many small businesses know what they want to communicate but do not have a designer, a prompt engineer, or a repeatable content-production process. Generic image-generation tools often produce inconsistent results because the prompt is incomplete, the brand identity is missing, and the final composition is not adapted to the target platform. TRENDY AI turns this open-ended task into a guided workflow that is easier to use, easier to repeat, and easier to scale.

## How the product works

1. The user signs in and creates or selects a brand workspace.
2. The user completes the Brand Kit with the brand identity, colors, logo, audience, tone, and visual rules.
3. The user starts a generation and answers a structured campaign questionnaire covering the campaign goal, target audience, content type, core idea, voice, platform format, and optional notes.
4. TRENDY AI validates the brief and shows the user a preview before generation.
5. The system compiles a provider-ready instruction that respects the campaign brief, Brand Kit, platform dimensions, safe areas, language, and logo mode.
6. The selected AI provider generates the visual, and TRENDY AI stores the result in the brand's history for later review and download.

## Main capabilities

| Capability | Description |
|---|---|
| Multi-brand workspaces | Manage several brands while keeping each brand's identity and generated assets separate. |
| Brand Kit | Store the brand name, tagline, tone, audience, colors, logo, and visual directions. |
| Structured generation brief | Guide the user through campaign goal, audience, content type, core idea, voice, and notes instead of relying on one vague prompt. |
| Platform-ready formats | Generate compositions for supported social platforms and aspect ratios, with dimensions and safe-area rules applied. |
| Logo controls | Choose whether the logo is omitted, included, or used as a watermark when a valid logo is available. |
| AI provider keys | Support provider credentials securely on the server side, with provider validation and key management. |
| Generation history | Keep generated assets associated with the correct brand for review and reuse. |
| Arabic-first experience | Prioritize Arabic content and RTL-friendly product behavior, with foundations for Arabic and English support. |
| Extensible architecture | Use a Next.js frontend, FastAPI backend, PostgreSQL database/S3 storage, and provider adapters that can grow over time. |

## Business model and API-key options

TRENDY AI is intended to become a commercial SaaS product. The cost of image generation is paid to the selected AI provider, so the product can offer two clear operating modes:

### 1. Managed generation credits

The customer pays TRENDY AI through a subscription or prepaid credit package. TRENDY AI manages the provider account, pays the provider usage cost, and deducts credits according to the model, resolution, and generation type. This is the simplest experience for customers who do not want to configure technical credentials.

Possible commercial tiers include a free trial with limited generations, a monthly plan for small businesses, a higher-volume plan for agencies, and a custom enterprise plan. Exact prices, limits, payment gateway, invoices, refunds, and tax handling are business decisions to be finalized before launch.

### 2. Bring Your Own API Key (BYOK)

Customers can connect their own supported provider API key from the Keys section. In this mode, the customer pays the AI provider directly, while TRENDY AI charges only for the product experience if the selected plan requires it. This option gives advanced users more control over provider billing, quotas, models, and usage limits.

API keys must never be exposed to the browser or stored as plain text. They should be validated server-side, encrypted with the application Fernet key, and used only for authorized generations belonging to the customer's brand. The interface should clearly show which provider is connected, whether the key is valid, and that provider charges are paid by the key owner.

| Mode | Who pays the AI provider? | Best for | TRENDY AI revenue |
|---|---|---|---|
| Managed credits | TRENDY AI | Beginners and customers who want a ready-to-use experience | Subscription and/or credit margin |
| BYOK | The customer | Technical users, agencies, and customers with an existing provider account | Product subscription, workspace fee, or optional usage fee |

The future billing layer can support both modes without changing the core generation flow. The generation record should retain the selected provider, billing mode, model, and usage metadata so that limits, reporting, and customer support can be implemented safely.

## Target customers and use cases

The initial market is Arabic-speaking small businesses and creators, especially brands in perfumes, clothing, abayas, cosmetics, retail, food, hospitality, and local services. Agencies can use the multi-brand workflow to manage several customer brands from one account. Typical use cases include product launches, promotional offers, seasonal campaigns, brand-awareness posts, lead-generation creatives, and social-proof content.

## Product status and roadmap boundary

The current project focuses on the brand workspace, Brand Kit, structured generation flow, provider-key management, image generation, storage, and history. Payments, subscriptions, invoices, credit accounting, and a production billing gateway are commercial roadmap items and should be implemented as a separate billing layer. The product description therefore treats managed credits and BYOK as the intended business model, not as a claim that a complete payment system is already enabled in this repository.

## Quick Start (Docker)

Install Docker with Compose, then run from the repository root:

```bash
docker compose up -d --build
```

Open http://127.0.0.1:3000. Compose starts PostgreSQL, MinIO, an idempotent bucket initializer, and the app. Database migrations run before the API starts. Local-only credentials are defaults; never expose this configuration publicly. Ports are bound to localhost (3000 app, 8000 API, 5432 database, 9000 S3, 9001 console). Set `APP_PORT` to change the app port and update `CORS_ORIGINS` accordingly. If changing `S3_PORT`, also set `S3_PUBLIC_BASE_URL` to that browser-facing URL before building.

With `SMTP_HOST` empty, read signup/reset codes in `docker compose logs app`. Set `ADMIN_EMAILS` before starting to grant the matching verified account admin access. Set `GENERATION_API_KEY` for real image generation. Use `docker compose logs -f` for logs and `docker compose down` to stop (without deleting data volumes).

For HTTPS production deployment, secrets, SMTP, DNS, backups, and all environment variables, see [Deploy on Coolify](docs/deploy-coolify.md).

## Local Development (without Docker for the app)

Use Node.js 20+, Python 3.13+, PostgreSQL, and an S3-compatible server. You can run only the infrastructure with:

```bash
docker compose up -d postgres minio minio-init
```

Copy `backend/.env.example` to `backend/.env` and `frontend/.env.local.example` to `frontend/.env.local`. Set DATABASE_URL to the local PostgreSQL credentials (Compose defaults: user/database `trendy`, password `trendy-local-password`). Set S3_ENDPOINT_URL and S3_PUBLIC_BASE_URL to `http://127.0.0.1:9000`, S3_ACCESS_KEY_ID to `trendy-local`, S3_SECRET_ACCESS_KEY to `trendy-local-storage-password`. Use the same explicit AUTH_JWT_SECRET in both env files; set AUTH_COOKIE_SECURE=false locally. Generate APP_ENCRYPTION_KEY using the Fernet command in the deployment guide. Set frontend NEXT_PUBLIC_STORAGE_PUBLIC_URL to the S3 public URL and NEXT_SERVER_API_URL to `http://127.0.0.1:8000` before building.

From backend/ (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.db.migrate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

From frontend/ in a second terminal:

```bash
npm ci
npm run dev
```

Use the frontend URL printed by Next.js. Browser API calls use the same-origin `/api` proxy, so no separate browser API origin is needed. If using independent PostgreSQL/S3 installations, create the database and all three buckets first; only brand-assets allows anonymous download. See the deployment guide for the equivalent MinIO setup and settings.

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make build` | Build Docker image |
| `make up` | Build and run container |
| `make down` | Stop and remove container |
| `make logs` | Tail container logs |
| `make restart` | Restart container |
| `make shell` | Shell into running container |
| `make health` | Check container health |
| `make clean` | Remove container and image |
| `make dev` | Show local dev instructions |
| `make dev-backend` | Run backend locally |
| `make dev-frontend` | Run frontend locally |
| `make lint` | Lint backend + frontend |
| `make test` | Run backend tests |

See [Deploy on Coolify](docs/deploy-coolify.md) for current production deployment details.
