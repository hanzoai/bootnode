"""API dependencies."""

import hashlib
import logging
import uuid
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bootnode.config import get_settings
from bootnode.core.cache import redis_client
from bootnode.db.models import ApiKey, Project, User
from bootnode.db.session import get_db

logger = logging.getLogger(__name__)
settings = get_settings()


async def verify_api_key_or_token(
    x_api_key: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> tuple[ApiKey | None, User | None, Project | None]:
    """Verify API key or JWT token from header.

    Returns tuple of (api_key, user, project).
    At least one of api_key or user will be set on success.
    """
    # Extract credential from headers
    credential = x_api_key
    is_bearer = False

    if not credential and authorization:
        if authorization.startswith("Bearer "):
            credential = authorization[7:]
            is_bearer = True

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Use X-API-Key header or Authorization: Bearer <token>",
        )

    # Try JWT token first (if it looks like a JWT)
    if is_bearer or credential.count('.') == 2:
        try:
            payload = jwt.decode(
                credential,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
            user_id = payload.get("sub")
            if user_id:
                result = await db.execute(
                    select(User).where(User.id == uuid.UUID(user_id))
                )
                user = result.scalar_one_or_none()
                if user:
                    # For JWT auth, get user's default project or first project
                    proj_result = await db.execute(
                        select(Project).where(Project.owner_id == user.id).limit(1)
                    )
                    project = proj_result.scalar_one_or_none()
                    return None, user, project
        except jwt.InvalidTokenError as e:
            logger.debug("JWT verification failed: %s", e)
            # Not a valid JWT, try as API key

    # Try API key
    key_hash = hashlib.sha256(
        f"{credential}{settings.api_key_salt}".encode()
    ).hexdigest()

    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active)
    )
    db_key = result.scalar_one_or_none()

    if not db_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key or token",
        )

    # Check rate limit for API key
    rate_key = f"rate:{db_key.id}"
    allowed, remaining = await redis_client.rate_limit_check(
        rate_key, db_key.rate_limit
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"X-RateLimit-Remaining": "0", "Retry-After": "60"},
        )

    # Get project for API key
    proj_result = await db.execute(
        select(Project).where(Project.id == db_key.project_id)
    )
    project = proj_result.scalar_one_or_none()

    return db_key, None, project


async def verify_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    """Verify API key from header (backwards compatible)."""
    api_key, user, project = await verify_api_key_or_token(
        x_api_key, authorization, db
    )

    if api_key:
        return api_key

    # For JWT auth, create a virtual API key with user permissions
    if user:
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No project found. Create a project first.",
            )
        virtual_key = ApiKey(
            id=uuid.uuid4(),
            project_id=project.id,
            name=f"User: {user.email}",
            key_hash="jwt-auth",
            key_prefix="jwt_",
            rate_limit=1000,
            compute_units_limit=10000,
            is_active=True,
        )
        return virtual_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API key required",
    )


async def get_project_from_key(
    x_api_key: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Get project from API key or JWT token."""
    api_key, user, project = await verify_api_key_or_token(
        x_api_key, authorization, db
    )

    if project:
        return project

    # If no project found, return error
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No project found. Create a project first in Settings.",
    )


# Type aliases for dependency injection
ApiKeyDep = Annotated[ApiKey, Depends(verify_api_key)]
ProjectDep = Annotated[Project, Depends(get_project_from_key)]
DbDep = Annotated[AsyncSession, Depends(get_db)]
