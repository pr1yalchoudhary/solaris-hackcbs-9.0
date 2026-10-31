# Solaris

Solaris is a HackCBS project exploring how housing societies can plan shared rooftop solar under Virtual Net Metering (VNM). The idea is to make the numbers and decisions easier for residents to understand, especially when project costs or membership change.

## Where things stand

This repository is an early foundation, not a finished solar-management platform. It currently includes:

- A small React/Vite page that checks whether the API is reachable.
- A FastAPI service with health and readiness checks, token-based user lookup, and basic role and community-access checks.
- MongoDB collection validators and indexes for the initial data model.
- An OR-Tools CP-SAT smoke example.
- A few tests covering the API foundation and schema setup.

Features such as project planning, bill reconciliation, provider workflows, and SmartExit are ideas for future work; they are not implemented end to end yet.

## Run locally

### Backend

Use Python 3.11 or newer. From the `Backend` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

The API listens on `http://127.0.0.1:8000`. Check `http://127.0.0.1:8000/api/health` to see whether it is running.

MongoDB and authentication settings are optional for starting the server, but required for readiness and protected routes. Copy `Backend/.env.example` to `Backend/.env` and set the values you need. The database setup script is explicit; it does not run when the API starts:

```powershell
python -m app.init_db
```

### Frontend

In a second terminal, from `Frontend`:

```powershell
npm install
npm run dev
```

Vite serves the page at `http://127.0.0.1:5173` and proxies `/api` requests to the local backend. To use another backend URL, set `DEV_API_TARGET` in the frontend environment.

## Checks

Run the backend tests from `Backend`:

```powershell
python -m pytest
```

Build the frontend from `Frontend`:

```powershell
npm run build
```

## API endpoints

- `GET /api/health` — confirms the API process is responding.
- `GET /api/ready` — checks that MongoDB is configured and reachable.
- `GET /api/me` — returns the authenticated user's ID and role.
- `GET /api/admin/access` — example platform-admin role check.
- `GET /api/communities/{community_id}/access` — checks for an active community membership.

Authentication uses an RS256 token verified with the configured public key and issuer. Roles are read from active user records in MongoDB, not trusted from token claims.

## Project direction

The longer-term goal is to help communities compare contribution plans, keep track of project information, and assess member exits without making automatic financial or ownership decisions. Any recommendations should remain subject to community review and the relevant DISCOM's approval.
