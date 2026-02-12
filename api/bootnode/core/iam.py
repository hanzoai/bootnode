"""Hanzo IAM integration for multi-tenant authentication.

Supports login via:
- hanzo.id (Hanzo org)
- zoo.id (Zoo Labs org)
- lux.id (Lux Network org)
- pars.id (Pars org)

Uses Casdoor-compatible OAuth2/OIDC flow.
"""

from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from pydantic import BaseModel

from bootnode.config import get_settings


class IAMUser(BaseModel):
    """User from Hanzo IAM."""

    id: str
    name: str
    email: str
    org: str  # hanzo, zoo, lux, pars
    avatar: str | None = None
    roles: list[str] = []
    permissions: list[str] = []
    created_at: datetime | None = None

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return "admin" in self.roles

    @property
    def can_create_projects(self) -> bool:
        """Check if user can create projects."""
        return "projects:write" in self.permissions or self.is_admin


class IAMClient:
    """Client for Hanzo IAM service."""

    def __init__(self):
        self.settings = get_settings()
        self._jwks_client: PyJWKClient | None = None

    @property
    def jwks_client(self) -> PyJWKClient:
        """Get JWKS client (lazy initialization)."""
        if self._jwks_client is None:
            jwks_url = f"{self.settings.iam_url}/.well-known/jwks.json"
            self._jwks_client = PyJWKClient(jwks_url)
        return self._jwks_client

    # All known IAM app client_ids — tokens from any of these are accepted.
    KNOWN_CLIENT_IDS = {"lux-web3", "pars-cloud", "zoo-cloud", "hanzo-cloud"}

    async def verify_token(self, token: str) -> IAMUser:
        """Verify JWT token from hanzo.id and return user."""
        try:
            # Get signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            # Accept tokens issued for any of our known IAM apps
            allowed_audiences = self.KNOWN_CLIENT_IDS | {self.settings.iam_client_id}

            # Decode and verify token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=list(allowed_audiences),
                # Lux IAM currently issues tokens with canonical issuer
                # (for example, https://hanzo.id) even when reached via branded domains.
                options={"verify_iss": False},
            )

            # Extract user info
            return IAMUser(
                id=payload.get("sub"),
                name=payload.get("name", ""),
                email=payload.get("email", ""),
                org=payload.get("org", "hanzo"),
                avatar=payload.get("avatar"),
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                created_at=datetime.fromtimestamp(
                    payload.get("iat", 0), tz=UTC
                ),
            )

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
            )

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        client_id: str | None = None,
    ) -> dict[str, Any]:
        """Exchange authorization code for tokens.

        Args:
            code: The authorization code from the OAuth callback.
            redirect_uri: Must match the redirect_uri used in the authorize request.
            client_id: IAM app client_id. Defaults to settings.iam_client_id.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.settings.iam_url}/api/login/oauth/access_token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": client_id or self.settings.iam_client_id,
                    "client_secret": self.settings.iam_client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to exchange code for token",
                )

            return response.json()


# Dependency injection
@lru_cache
def get_iam_client() -> IAMClient:
    """Get IAM client singleton."""
    return IAMClient()


# Security scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    iam: IAMClient = Depends(get_iam_client),
) -> IAMUser:
    """Get current authenticated user from hanzo.id token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await iam.verify_token(credentials.credentials)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    iam: IAMClient = Depends(get_iam_client),
) -> IAMUser | None:
    """Get current user if authenticated, None otherwise."""
    if credentials is None:
        return None

    try:
        return await iam.verify_token(credentials.credentials)
    except HTTPException:
        return None


def require_org(allowed_orgs: list[str]):
    """Dependency that requires user to be from specific org(s)."""
    async def _require_org(user: IAMUser = Depends(get_current_user)) -> IAMUser:
        if user.org not in allowed_orgs:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access restricted to orgs: {allowed_orgs}",
            )
        return user
    return _require_org


def require_permission(permission: str):
    """Dependency that requires user to have specific permission."""
    async def _require_permission(user: IAMUser = Depends(get_current_user)) -> IAMUser:
        if permission not in user.permissions and not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return user
    return _require_permission
