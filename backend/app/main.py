from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

from app.auth import Principal, community_member, current_user, require_roles
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    client = None
    if settings.mongodb_uri.get_secret_value():
        client = AsyncMongoClient(settings.mongodb_uri.get_secret_value(), serverSelectionTimeoutMS=3000)
    app.state.db = client[settings.mongodb_database] if client is not None else None
    try:
        yield
    finally:
        if client is not None:
            await client.close()


app = FastAPI(title="Solaris API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins,
                   allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "solaris-api"}


@app.get("/api/ready")
async def ready(request: Request):
    if request.app.state.db is None:
        raise HTTPException(503, "Database is not configured")
    try:
        await request.app.state.db.command("ping")
    except PyMongoError:
        raise HTTPException(503, "Database is unavailable") from None
    return {"status": "ready"}


@app.get("/api/me")
async def me(user: Annotated[Principal, Depends(current_user)]):
    return user


@app.get("/api/admin/access")
async def admin_access(user: Annotated[Principal, Depends(require_roles("platform_admin"))]):
    return {"authorized": True}


@app.get("/api/communities/{community_id}/access")
async def community_access(membership: Annotated[dict, Depends(community_member)]):
    return membership
