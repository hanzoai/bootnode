"""
Hanzo KMS Client for Bootnode

Fetches secrets from Hanzo KMS at startup using the official SDK.
Supports multiple auth methods: universal auth, K8s auth, AWS IAM.

Usage:
    from bootnode.core.kms import get_secret, get_secrets, inject_secrets

    # Get single secret
    db_url = get_secret("DATABASE_URL")

    # Get all secrets for environment
    secrets = get_secrets()

    # Inject all secrets at startup
    inject_secrets()

Environment Variables:
    HANZO_KMS_URL: KMS API URL (default: https://kms.hanzo.ai)
    HANZO_KMS_CLIENT_ID: Universal auth client ID
    HANZO_KMS_CLIENT_SECRET: Universal auth client secret
    HANZO_KMS_PROJECT: Project ID or slug
    HANZO_KMS_ENV: Environment (development, staging, production)

In Kubernetes, secrets are synced via the KMS Operator (KMSSecret CRD).
The operator automatically injects secrets as environment variables.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# KMS Configuration
KMS_URL = os.getenv("HANZO_KMS_URL", "https://kms.hanzo.ai")
KMS_ORG = os.getenv("HANZO_KMS_ORG", "hanzo")
KMS_CLIENT_ID = os.getenv("HANZO_KMS_CLIENT_ID", "")
KMS_CLIENT_SECRET = os.getenv("HANZO_KMS_CLIENT_SECRET", "")
KMS_PROJECT = os.getenv("HANZO_KMS_PROJECT", "bootnode")
KMS_ENV = os.getenv("HANZO_KMS_ENV", "production")

# Singleton client
_client = None


def _get_client():
    """Get or create KMS client singleton."""
    global _client
    if _client is not None:
        return _client

    # Skip if no credentials (K8s operator handles secrets)
    if not KMS_CLIENT_ID or not KMS_CLIENT_SECRET:
        logger.debug("No KMS credentials, secrets managed by K8s operator or env vars")
        return None

    try:
        from hanzo_kms import (
            KMSClient,
            ClientSettings,
            AuthenticationOptions,
            UniversalAuthMethod,
        )

        _client = KMSClient(ClientSettings(
            site_url=KMS_URL,
            organization=KMS_ORG,
            auth=AuthenticationOptions(
                universal_auth=UniversalAuthMethod(
                    client_id=KMS_CLIENT_ID,
                    client_secret=KMS_CLIENT_SECRET,
                )
            )
        ))
        logger.info("KMS client initialized", extra={"url": KMS_URL, "org": KMS_ORG, "project": KMS_PROJECT})
        return _client

    except ImportError:
        logger.warning("hanzo-kms not installed, using environment variables only")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize KMS client: {e}")
        return None


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a secret from KMS or environment.

    Args:
        key: Secret name
        default: Default value if not found

    Returns:
        Secret value or default
    """
    # First check environment (may be set by K8s operator)
    env_value = os.getenv(key)
    if env_value is not None:
        return env_value

    # Try KMS client
    client = _get_client()
    if client:
        try:
            return client.get_value(
                project_id=KMS_PROJECT,
                environment=KMS_ENV,
                secret_name=key,
                default=default,
            )
        except Exception as e:
            logger.warning(f"Failed to get secret {key} from KMS: {e}")

    return default


def get_secrets() -> dict[str, str]:
    """Get all secrets from KMS.

    Returns:
        Dictionary of secret key -> value
    """
    client = _get_client()
    if not client:
        return {}

    try:
        secrets = client.list_secrets(
            project_id=KMS_PROJECT,
            environment=KMS_ENV,
        )
        return {s.secret_key: s.secret_value for s in secrets}
    except Exception as e:
        logger.error(f"Failed to list secrets from KMS: {e}")
        return {}


def inject_secrets() -> None:
    """Inject KMS secrets into environment at startup.

    Secrets already in environment (e.g., from K8s operator) are not overwritten.
    """
    client = _get_client()
    if not client:
        # This is expected in K8s — External Secrets Operator handles injection
        has_jwt = bool(os.getenv("JWT_SECRET"))
        has_db = bool(os.getenv("DATABASE_URL"))
        if has_jwt and has_db:
            logger.info("Secrets loaded from environment (K8s External Secrets)")
        else:
            logger.warning(
                "KMS client not available and core secrets missing from env. "
                "Set HANZO_KMS_CLIENT_ID/SECRET for direct KMS access, "
                "or ensure External Secrets Operator is syncing to bootnode-secrets."
            )
        return

    try:
        count = client.inject_env(
            project_id=KMS_PROJECT,
            environment=KMS_ENV,
            overwrite=False,  # Don't overwrite existing env vars
        )
        logger.info(f"Injected {count} secrets from KMS")
    except Exception as e:
        logger.error(f"Failed to inject secrets from KMS: {e}")
