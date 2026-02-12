"""OAuth callback endpoint for Hanzo IAM integration.

Supports multi-network OAuth: each white-label network (lux, pars, zoo, hanzo)
has its own IAM app with a distinct client_id.  The frontend sends the
redirect_uri it used for the authorize request so the backend can derive the
correct client_id for the token exchange.
"""

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from bootnode.config import get_settings
from bootnode.core.iam import IAMClient, IAMUser, get_current_user

router = APIRouter()
settings = get_settings()

# All cloud networks share the same IAM app (app-lux-web3, clientId=lux-web3)
# with redirect URIs for each network registered in IAM.
NETWORK_CLIENT_IDS: dict[str, str] = {
    "lux": "lux-web3",
    "pars": "lux-web3",
    "zoo": "lux-web3",
    "hanzo": "lux-web3",
}


def _network_from_redirect_uri(redirect_uri: str) -> str | None:
    """Extract network name from a redirect_uri like https://cloud.lux.network/…"""
    host = urlparse(redirect_uri).hostname or ""
    # cloud.lux.network → lux  |  cloud.hanzo.ai → hanzo
    parts = host.split(".")
    if len(parts) >= 3 and parts[0] == "cloud":
        return parts[1]
    # bootno.de special case → lux (primary brand)
    if "bootno.de" in host:
        return "lux"
    return None


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request."""

    code: str
    state: str
    redirect_uri: str = ""  # Frontend should send the redirect_uri it used


class OAuthCallbackResponse(BaseModel):
    """OAuth callback response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600


@router.post("/oauth/callback", response_model=OAuthCallbackResponse)
async def oauth_callback(request: OAuthCallbackRequest) -> OAuthCallbackResponse:
    """Handle OAuth callback from Hanzo IAM.

    The frontend MUST send redirect_uri so we can derive the correct IAM
    client_id for multi-network token exchange.
    """
    try:
        # Determine redirect_uri — prefer explicit, fall back to settings
        redirect_uri = request.redirect_uri or (
            f"{settings.frontend_url.rstrip('/')}/auth/callback"
        )

        # Derive network-specific client_id from the redirect_uri domain
        network = _network_from_redirect_uri(redirect_uri)
        client_id = NETWORK_CLIENT_IDS.get(network or "", settings.iam_client_id)

        iam_client = IAMClient()
        token_data = await iam_client.exchange_code(
            code=request.code,
            redirect_uri=redirect_uri,
            client_id=client_id,
        )

        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth token response missing access_token",
            )

        # Verify token and get user info
        user = await iam_client.verify_token(access_token)

        # Check if user's organization is allowed
        if user.org not in settings.allowed_orgs:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Organization '{user.org}' is not allowed",
            )

        return OAuthCallbackResponse(
            access_token=access_token,
            expires_in=token_data.get("expires_in", 3600),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange authorization code for token",
        )


@router.get("/me")
async def get_current_user_info(user: IAMUser = Depends(get_current_user)):
    """Get current authenticated user from Hanzo IAM."""
    return user
