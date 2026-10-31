# Solaris · HackCBS 2026

Shared solar investment planning and management for residential communities using Virtual Net Metering (VNM).

## Foundation status

React + Vite + TypeScript + Tailwind CSS frontend; Python + FastAPI backend;
MongoDB Atlas via backend-only PyMongo Async; local Google OR-Tools CP-SAT smoke model.
Gemini is planned for explanations only. No live AI integration, payment processing,
deployment, real financial data, or automatic ownership/allocation changes are present.

See [architecture and MVP order](docs/architecture.md) and [collection catalogue](docs/data-model.md).
This is an infrastructure foundation, not the completed domain MVP.

## Local prerequisites

- Node.js 22.12+ and pnpm 10+ (the lockfile was generated with pnpm 11).
- Python 3.11–3.12; verified with Python 3.12. Python 3.8/3.9 are too old.
- Atlas and Clerk credentials are optional to start the shell; required for data/auth functionality.

From the repository root, in PowerShell:

```powershell
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.lock.txt
Copy-Item backend/.env.example backend/.env
cd backend
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

Open http://localhost:5173. API docs: http://127.0.0.1:8000/docs.
Vite proxies `/api` to FastAPI. Use `localhost:5173` for the frontend so the
configured token authorised party matches. No frontend database driver or credentials.
If these ports are occupied, run Uvicorn with `--port 8010` and set
`$env:DEV_API_TARGET='http://127.0.0.1:8010'` before `pnpm dev` in the frontend terminal.
Vite prints its selected free port. Update backend CORS and auth authorised parties to
match the frontend origin before testing authenticated requests on a different port.
If `py -3.12` is missing, install Python 3.12 or invoke an existing 3.12 executable.
On macOS/Linux use `python3.12` and `.venv/bin/python` instead.

## Atlas setup (manual; no cloud resources provisioned)

1. Create/select an Atlas project and cluster; review its pricing before enabling paid resources.
2. Under Database Access create a dedicated app database user, limited to `readWrite`
   on `solaris`. Use a separate setup identity with collection/index-management privileges.
3. In Network Access allow your current development IP only. Avoid unrestricted IP access.
4. Use Connect → Drivers → Python to copy the TLS `mongodb+srv://` URI. URL-encode
   special characters in its password; save it only as `MONGODB_URI` in `backend/.env`.
5. Set `MONGODB_DATABASE=solaris`. From `backend`, run
   `.venv/Scripts/python.exe -m app.init_db` using the setup identity. This explicitly
   creates validators/indexes; startup itself never changes the database schema.
   Existing invalid records are not repaired by this command. Use an empty dev database first.
6. Switch back to the restricted application identity and restart FastAPI. `/api/ready`
   returns 200 after a successful ping; 503 means missing config or unavailable database.

No Atlas connection or schema application has been performed without your credentials.

## Authentication and roles

Recommended: Clerk for identity, FastAPI for authorisation. Configure a Clerk application
for `http://localhost:5173`. Put its issuer and PEM public key into backend `AUTH_ISSUER`
and `AUTH_PUBLIC_KEY` (literal `\n` in the PEM is supported). Review provider pricing
before enabling paid options. The public key needs rotation when Clerk rotates keys.

The backend validates RS256 signature, issuer, expiry, not-before, issued-at and authorised
party. Roles in a token or request are ignored. An operator must provision an active
`users` document keyed by Clerk `auth_subject`, and community-specific `memberships`.
IDs are UUID strings, timestamps BSON UTC dates, `schema_version` is 1; follow
`backend/app/schema.py`. No self-service role escalation or automatic first-user admin.
Send a Clerk session token as `Authorization: Bearer <token>` to `/api/me`.

`/api/admin/access` requires `platform_admin`; `/api/communities/{id}/access` requires
active membership in that community. Future resource endpoints must additionally filter
by community, ownership and membership role. The login UI and three dashboards are next
MVP work; they are not implemented in this foundation.

## Documents and secrets

Recommend private S3 object storage, with public access blocked and encryption enabled.
Backend-authorised short-lived signed URLs will handle uploads/downloads. Store metadata,
hash, ownership and opaque object key in MongoDB; never public bill URLs or file binaries.
Enforce PDF/JPEG/PNG, 10 MiB maximum, signature checks and quarantine/scan before access.
The upload adapter and OCR are deferred; no bucket is created here.

All credentials belong in ignored backend `.env` or backend environment variables.
`frontend/.env` may contain only public configuration: every `VITE_*` value is browser-visible.
`.env.example` files contain placeholders only. Gemini has no callable adapter yet;
the disabled `ENABLE_PAID_API_CALLS` setting is reserved for a future explicit approval gate.

## Verification

```powershell
cd backend
.venv/Scripts/python.exe -m pytest
cd ../frontend
pnpm build
```

Tests cover no-config startup, readiness, token validation, role enforcement, community
isolation, and a real local CP-SAT solve. Live Atlas, Clerk sign-in, S3, Gemini and domain
financial workflows require later integration validation. No commits or pushes are automatic.
See [verification results](docs/verification.md).

## Layout

```text
backend/app/          FastAPI, config, auth, Mongo validators and explicit setup
backend/tests/        Foundation security and solver checks
frontend/src/         React shell and API health connection
docs/                Architecture, data relationships and MVP boundaries
```
