from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.config import get_settings

bearer = HTTPBearer(auto_error=False)


class Principal(BaseModel):
    id: str
    role: str


async def current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal:
    if credentials is None:
        raise HTTPException(401, "Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    settings = get_settings()
    if not settings.auth_public_key or not settings.auth_issuer:
        raise HTTPException(503, "Authentication is not configured")
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.auth_public_key.replace("\\n", "\n"),
            algorithms=["RS256"],
            issuer=settings.auth_issuer,
            options={"require": ["exp", "nbf", "iat", "iss", "sub", "azp"], "verify_aud": False},
        )
        if claims["azp"] not in settings.auth_authorized_parties or not isinstance(claims["sub"], str):
            raise jwt.InvalidTokenError()
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid or expired token") from None
    db = request.app.state.db
    if db is None:
        raise HTTPException(503, "Database is not configured")
    # Roles are provisioned by an operator; no automatic admin or token-role trust.
    user = await db.users.find_one({"auth_subject": claims["sub"], "status": "active"})
    if not user or user["role"] not in {"resident", "community_admin", "solar_provider", "platform_admin"}:
        raise HTTPException(403, "Active membership required")
    return Principal(id=user["_id"], role=user["role"])


async def community_member(
    community_id: str, request: Request,
    user: Annotated[Principal, Depends(current_user)],
):
    membership = await request.app.state.db.memberships.find_one(
        {"community_id": community_id, "user_id": user.id, "status": "active"}
    )
    if not membership:
        raise HTTPException(403, "Active community membership required")
    return {"user_id": user.id, "community_id": community_id, "role": membership["role"]}


def require_roles(*roles: str):
    async def check(user: Annotated[Principal, Depends(current_user)]) -> Principal:
        if user.role not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return check
