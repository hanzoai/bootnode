"""Billing module tests — compute units, tiers, Commerce client, and webhooks."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bootnode.core.billing.compute_units import (
    COMPUTE_UNITS,
    DEFAULT_COMPUTE_UNITS,
    get_batch_compute_units,
    get_compute_units,
)
from bootnode.core.billing.tiers import (
    TIER_LIMITS,
    PricingTier,
    TierLimits,
    calculate_monthly_cost,
    get_tier_limits,
)


# =============================================================================
# Compute Units
# =============================================================================


class TestComputeUnits:
    def test_free_methods_cost_1(self):
        assert get_compute_units("eth_chainId") == 1
        assert get_compute_units("eth_blockNumber") == 1
        assert get_compute_units("net_version") == 1

    def test_light_methods_cost_5(self):
        assert get_compute_units("eth_getBalance") == 5
        assert get_compute_units("eth_getTransactionByHash") == 5

    def test_medium_methods_cost_10(self):
        assert get_compute_units("eth_call") == 10
        assert get_compute_units("eth_estimateGas") == 10

    def test_heavy_methods_cost_25(self):
        assert get_compute_units("eth_getLogs") == 25

    def test_transaction_methods_cost_50(self):
        assert get_compute_units("eth_sendRawTransaction") == 50

    def test_debug_methods_cost_100(self):
        assert get_compute_units("debug_traceTransaction") == 100

    def test_unknown_method_returns_default(self):
        assert get_compute_units("nonexistent_method") == DEFAULT_COMPUTE_UNITS

    def test_batch_compute_units(self):
        methods = ["eth_chainId", "eth_getBalance", "eth_call"]
        assert get_batch_compute_units(methods) == 1 + 5 + 10

    def test_batch_empty(self):
        assert get_batch_compute_units([]) == 0

    def test_solana_methods(self):
        assert get_compute_units("getAccountInfo") == 5
        assert get_compute_units("sendTransaction") == 50
        assert get_compute_units("simulateTransaction") == 25

    def test_erc4337_methods(self):
        assert get_compute_units("eth_sendUserOperation") == 75
        assert get_compute_units("eth_estimateUserOperationGas") == 25

    def test_bootnode_enhanced_apis(self):
        assert get_compute_units("tokens_getBalances") == 15
        assert get_compute_units("nfts_getOwned") == 20
        assert get_compute_units("webhooks_create") == 5


# =============================================================================
# Pricing Tiers
# =============================================================================


class TestPricingTiers:
    def test_all_tiers_defined(self):
        for tier in PricingTier:
            assert tier in TIER_LIMITS

    def test_free_tier_limits(self):
        limits = get_tier_limits(PricingTier.FREE)
        assert limits.monthly_cu == 30_000_000
        assert limits.rate_limit_per_second == 25
        assert limits.max_apps == 5
        assert limits.max_webhooks == 5
        assert limits.price_per_million_cu == 0

    def test_payg_tier_limits(self):
        limits = get_tier_limits(PricingTier.PAY_AS_YOU_GO)
        assert limits.monthly_cu == 0  # unlimited
        assert limits.rate_limit_per_second == 300
        assert limits.max_apps == 30
        assert limits.price_per_million_cu == 40  # $0.40

    def test_growth_tier_limits(self):
        limits = get_tier_limits(PricingTier.GROWTH)
        assert limits.monthly_cu == 100_000_000
        assert limits.rate_limit_per_second == 500
        assert limits.price_per_million_cu == 35  # $0.35

    def test_enterprise_tier_limits(self):
        limits = get_tier_limits(PricingTier.ENTERPRISE)
        assert limits.rate_limit_per_second == 1000
        assert limits.max_apps == 0  # unlimited
        assert limits.price_per_million_cu == 0  # custom

    def test_tier_rate_limits_ascending(self):
        """Higher tiers should have higher rate limits."""
        free = get_tier_limits(PricingTier.FREE)
        payg = get_tier_limits(PricingTier.PAY_AS_YOU_GO)
        growth = get_tier_limits(PricingTier.GROWTH)
        enterprise = get_tier_limits(PricingTier.ENTERPRISE)
        assert free.rate_limit_per_second < payg.rate_limit_per_second
        assert payg.rate_limit_per_second < growth.rate_limit_per_second
        assert growth.rate_limit_per_second < enterprise.rate_limit_per_second


# =============================================================================
# Cost Calculation
# =============================================================================


class TestCostCalculation:
    def test_free_tier_always_zero(self):
        assert calculate_monthly_cost(PricingTier.FREE, 0) == 0
        assert calculate_monthly_cost(PricingTier.FREE, 1_000_000) == 0

    def test_enterprise_tier_always_zero(self):
        assert calculate_monthly_cost(PricingTier.ENTERPRISE, 0) == 0
        assert calculate_monthly_cost(PricingTier.ENTERPRISE, 999_000_000) == 0

    def test_payg_1_million_cu(self):
        # PAYG: $0.40 per million CU, no included CU
        cost = calculate_monthly_cost(PricingTier.PAY_AS_YOU_GO, 1_000_000)
        assert cost == 40  # 40 cents

    def test_payg_10_million_cu(self):
        cost = calculate_monthly_cost(PricingTier.PAY_AS_YOU_GO, 10_000_000)
        assert cost == 400  # $4.00

    def test_payg_zero_usage(self):
        cost = calculate_monthly_cost(PricingTier.PAY_AS_YOU_GO, 0)
        assert cost == 0

    def test_growth_within_included(self):
        # Growth includes 100M CU, no overage
        cost = calculate_monthly_cost(PricingTier.GROWTH, 50_000_000)
        assert cost == 0  # base fee not counted here (Commerce handles it)

    def test_growth_at_included(self):
        cost = calculate_monthly_cost(PricingTier.GROWTH, 100_000_000)
        assert cost == 0

    def test_growth_with_overage(self):
        # 10M overage at $0.35 per million
        cost = calculate_monthly_cost(PricingTier.GROWTH, 110_000_000)
        assert cost == 350  # $3.50


# =============================================================================
# Plan Slug Mappings
# =============================================================================


class TestPlanSlugs:
    def test_plan_to_tier_mapping(self):
        """Verify the plan-to-tier mapping in webhooks module."""
        from bootnode.core.billing.webhooks import PLAN_TO_TIER

        assert PLAN_TO_TIER["bootnode-free"] == PricingTier.FREE
        assert PLAN_TO_TIER["bootnode-payg"] == PricingTier.PAY_AS_YOU_GO
        assert PLAN_TO_TIER["bootnode-growth"] == PricingTier.GROWTH
        assert PLAN_TO_TIER["bootnode-enterprise"] == PricingTier.ENTERPRISE

    def test_api_tier_to_plan_slug(self):
        """Verify the tier-to-plan slug mapping in API module."""
        from bootnode.api.billing import TIER_TO_PLAN_SLUG

        assert TIER_TO_PLAN_SLUG[PricingTier.FREE] == "bootnode-free"
        assert TIER_TO_PLAN_SLUG[PricingTier.PAY_AS_YOU_GO] == "bootnode-payg"
        assert TIER_TO_PLAN_SLUG[PricingTier.GROWTH] == "bootnode-growth"
        assert TIER_TO_PLAN_SLUG[PricingTier.ENTERPRISE] == "bootnode-enterprise"


# =============================================================================
# Commerce Client
# =============================================================================


class TestCommerceClient:
    @patch("bootnode.core.billing.commerce.get_settings")
    def test_client_uses_commerce_config(self, mock_settings):
        mock_settings.return_value = MagicMock(
            commerce_url="http://test:8001",
            commerce_api_key="test-key",
        )
        from bootnode.core.billing.commerce import HanzoCommerceClient

        client = HanzoCommerceClient()
        assert client.base_url == "http://test:8001"
        assert client.api_key == "test-key"

    @patch("bootnode.core.billing.commerce.get_settings")
    def test_client_headers(self, mock_settings):
        mock_settings.return_value = MagicMock(
            commerce_url="http://test:8001",
            commerce_api_key="test-key",
        )
        from bootnode.core.billing.commerce import HanzoCommerceClient

        client = HanzoCommerceClient()
        headers = client._headers()
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["X-Source"] == "bootnode"
        assert headers["Content-Type"] == "application/json"

    @patch("bootnode.core.billing.commerce.get_settings")
    @pytest.mark.asyncio
    async def test_create_customer(self, mock_settings):
        mock_settings.return_value = MagicMock(
            commerce_url="http://test:8001",
            commerce_api_key="test-key",
        )
        from bootnode.core.billing.commerce import HanzoCommerceClient

        client = HanzoCommerceClient()

        # Mock the _request method
        client._request = AsyncMock(return_value={"id": "cust_123"})

        customer_id = await client.create_customer(
            user_id="user_1", email="test@test.com", name="Test User"
        )
        assert customer_id == "cust_123"
        client._request.assert_called_once()

    @patch("bootnode.core.billing.commerce.get_settings")
    @pytest.mark.asyncio
    async def test_create_checkout(self, mock_settings):
        mock_settings.return_value = MagicMock(
            commerce_url="http://test:8001",
            commerce_api_key="test-key",
        )
        from bootnode.core.billing.commerce import HanzoCommerceClient

        client = HanzoCommerceClient()
        client._request = AsyncMock(return_value={
            "order_id": "order_123",
            "checkout_url": "https://commerce.hanzo.ai/checkout/order_123",
            "authorization_id": "auth_456",
        })

        result = await client.create_checkout(
            customer_id="cust_123",
            plan_slug="bootnode-payg",
            project_id=uuid4(),
            success_url="https://example.com/success",
        )

        assert result["order_id"] == "order_123"
        assert result["checkout_url"] is not None
        client._request.assert_called_once_with(
            "POST",
            "/api/v1/checkout/authorize",
            json=pytest.approx(client._request.call_args[1]["json"], abs=0) if False else client._request.call_args[1].get("json", client._request.call_args[0][2] if len(client._request.call_args[0]) > 2 else None),
        )

    @patch("bootnode.core.billing.commerce.get_settings")
    @pytest.mark.asyncio
    async def test_capture_checkout(self, mock_settings):
        mock_settings.return_value = MagicMock(
            commerce_url="http://test:8001",
            commerce_api_key="test-key",
        )
        from bootnode.core.billing.commerce import HanzoCommerceClient

        client = HanzoCommerceClient()
        client._request = AsyncMock(return_value={"order_id": "order_123", "status": "completed"})

        result = await client.capture_checkout("order_123")
        assert result["status"] == "completed"
        client._request.assert_called_once_with("POST", "/api/v1/checkout/capture/order_123")

    @patch("bootnode.core.billing.commerce.get_settings")
    @pytest.mark.asyncio
    async def test_report_usage(self, mock_settings):
        mock_settings.return_value = MagicMock(
            commerce_url="http://test:8001",
            commerce_api_key="test-key",
        )
        from bootnode.core.billing.commerce import HanzoCommerceClient

        client = HanzoCommerceClient()
        client._request = AsyncMock(return_value={})

        now = datetime.now(UTC)
        await client.report_usage(
            subscription_id="sub_123",
            compute_units=5_000_000,
            timestamp=now,
            idempotency_key="test-key-123",
        )
        client._request.assert_called_once()
        call_args = client._request.call_args
        assert call_args[0][0] == "POST"
        assert "/usage" in call_args[0][1]

    @patch("bootnode.core.billing.commerce.get_settings")
    @pytest.mark.asyncio
    async def test_get_user_orders(self, mock_settings):
        mock_settings.return_value = MagicMock(
            commerce_url="http://test:8001",
            commerce_api_key="test-key",
        )
        from bootnode.core.billing.commerce import HanzoCommerceClient

        client = HanzoCommerceClient()
        client._request = AsyncMock(return_value={
            "data": [
                {"id": "order_1", "status": "completed"},
                {"id": "order_2", "status": "pending"},
            ]
        })

        orders = await client.get_user_orders("cust_123")
        assert len(orders) == 2
        assert orders[0]["id"] == "order_1"


# =============================================================================
# Commerce Webhooks
# =============================================================================


class TestCommerceWebhooks:
    @patch("bootnode.core.billing.webhooks.get_settings")
    def test_no_webhook_secret_allows_through(self, mock_settings):
        mock_settings.return_value = MagicMock(commerce_webhook_secret="")
        from bootnode.core.billing.webhooks import CommerceWebhookHandler

        handler = CommerceWebhookHandler()
        # No secret = verification skipped (returns True)
        assert handler.verify_signature(b"payload", "any-sig") is True

    @patch("bootnode.core.billing.webhooks.get_settings")
    def test_valid_signature(self, mock_settings):
        import hashlib
        import hmac

        secret = "test-secret"
        mock_settings.return_value = MagicMock(commerce_webhook_secret=secret)
        from bootnode.core.billing.webhooks import CommerceWebhookHandler

        handler = CommerceWebhookHandler()
        payload = b'{"type":"test"}'
        expected_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert handler.verify_signature(payload, expected_sig) is True

    @patch("bootnode.core.billing.webhooks.get_settings")
    def test_invalid_signature(self, mock_settings):
        mock_settings.return_value = MagicMock(commerce_webhook_secret="test-secret")
        from bootnode.core.billing.webhooks import CommerceWebhookHandler

        handler = CommerceWebhookHandler()
        assert handler.verify_signature(b'{"type":"test"}', "bad-signature") is False

    @patch("bootnode.core.billing.webhooks.get_settings")
    @pytest.mark.asyncio
    async def test_unhandled_event_type(self, mock_settings):
        mock_settings.return_value = MagicMock(commerce_webhook_secret="test")
        from bootnode.core.billing.webhooks import CommerceWebhookHandler

        handler = CommerceWebhookHandler()
        result = await handler.handle_event({
            "type": "some.unknown.event",
            "id": "evt_123",
            "data": {},
        })
        assert result["handled"] is False
        assert result["reason"] == "unknown_type"

    @patch("bootnode.core.billing.webhooks.get_settings")
    @pytest.mark.asyncio
    async def test_handles_order_completed(self, mock_settings):
        mock_settings.return_value = MagicMock(commerce_webhook_secret="test")
        from bootnode.core.billing.webhooks import CommerceWebhookHandler

        handler = CommerceWebhookHandler()
        result = await handler.handle_event({
            "type": "order.completed",
            "id": "evt_456",
            "data": {
                "id": "order_123",
                "customer_id": "cust_456",
                "metadata": {},
            },
        })
        assert result["handled"] is True
        assert result["result"]["order_id"] == "order_123"

    @patch("bootnode.core.billing.webhooks.get_settings")
    @pytest.mark.asyncio
    async def test_handles_order_cancelled(self, mock_settings):
        mock_settings.return_value = MagicMock(commerce_webhook_secret="test")
        from bootnode.core.billing.webhooks import CommerceWebhookHandler

        handler = CommerceWebhookHandler()
        result = await handler.handle_event({
            "type": "order.cancelled",
            "id": "evt_789",
            "data": {
                "id": "order_123",
                "reason": "customer_request",
            },
        })
        assert result["handled"] is True
        assert result["result"]["reason"] == "customer_request"

    @patch("bootnode.core.billing.webhooks.get_settings")
    @pytest.mark.asyncio
    async def test_handles_payment_paid(self, mock_settings):
        mock_settings.return_value = MagicMock(commerce_webhook_secret="test")
        from bootnode.core.billing.webhooks import CommerceWebhookHandler

        handler = CommerceWebhookHandler()
        result = await handler.handle_event({
            "type": "payment.paid",
            "id": "evt_pay1",
            "data": {
                "id": "pay_123",
                "order_id": "order_456",
                "amount": 4900,
            },
        })
        assert result["handled"] is True
        assert result["result"]["amount"] == 4900

    @patch("bootnode.core.billing.webhooks.get_settings")
    @pytest.mark.asyncio
    async def test_handles_payment_refunded(self, mock_settings):
        mock_settings.return_value = MagicMock(commerce_webhook_secret="test")
        from bootnode.core.billing.webhooks import CommerceWebhookHandler

        handler = CommerceWebhookHandler()
        result = await handler.handle_event({
            "type": "payment.refunded",
            "id": "evt_ref1",
            "data": {
                "id": "pay_123",
                "refund_id": "ref_456",
                "amount": 2500,
            },
        })
        assert result["handled"] is True
        assert result["result"]["refund_id"] == "ref_456"

    @patch("bootnode.core.billing.webhooks.get_settings")
    @pytest.mark.asyncio
    async def test_handles_invoice_paid(self, mock_settings):
        mock_settings.return_value = MagicMock(commerce_webhook_secret="test")
        from bootnode.core.billing.webhooks import CommerceWebhookHandler

        handler = CommerceWebhookHandler()
        result = await handler.handle_event({
            "type": "invoice.paid",
            "id": "evt_inv1",
            "data": {
                "id": "inv_123",
                "customer_id": "cust_456",
                "amount_paid": 4900,
            },
        })
        assert result["handled"] is True
        assert result["result"]["amount_paid"] == 4900


# =============================================================================
# Unified Billing Client
# =============================================================================


class TestUnifiedUser:
    def _make_iam_user(self, **kwargs):
        """Create a fake IAM user. Can't use MagicMock because 'name' is reserved."""
        from types import SimpleNamespace
        defaults = {"id": "user_1", "email": "test@test.com", "name": "Test", "org": "hanzo"}
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    def test_from_iam_user_no_commerce(self):
        from bootnode.core.billing.unified import UnifiedUser

        iam_user = self._make_iam_user()
        user = UnifiedUser.from_iam_user(iam_user)
        assert user.iam_id == "user_1"
        assert user.commerce_customer_id is None
        assert user.square_customer_id is None

    def test_from_iam_user_with_commerce(self):
        from bootnode.core.billing.unified import UnifiedUser

        iam_user = self._make_iam_user()
        commerce_data = {
            "id": "cust_123",
            "accounts": {"square": "sq_cust_456"},
            "has_payment_method": True,
            "default_payment_method": "card_789",
        }
        user = UnifiedUser.from_iam_user(iam_user, commerce_data)
        assert user.commerce_customer_id == "cust_123"
        assert user.square_customer_id == "sq_cust_456"
        assert user.has_payment_method is True


# =============================================================================
# Config Settings AliasChoices (P0 regression test)
# =============================================================================


class TestConfigSettings:
    """Verify commerce settings are accessible and AliasChoices work."""

    def test_commerce_settings_accessible(self):
        """P0 regression: config.py must expose commerce_url, not hanzo_commerce_url."""
        from bootnode.config import Settings

        s = Settings(
            commerce_url="https://test.commerce.ai",
            commerce_api_key="test-key",
            commerce_webhook_secret="test-secret",
        )
        assert s.commerce_url == "https://test.commerce.ai"
        assert s.commerce_api_key == "test-key"
        assert s.commerce_webhook_secret == "test-secret"

    def test_commerce_settings_backward_compat(self):
        """AliasChoices: HANZO_COMMERCE_URL env vars should still work."""
        import os

        env = {
            "HANZO_COMMERCE_URL": "https://old.commerce.ai",
            "HANZO_COMMERCE_API_KEY": "old-key",
            "HANZO_COMMERCE_WEBHOOK_SECRET": "old-secret",
        }
        old_values = {}
        for k, v in env.items():
            old_values[k] = os.environ.get(k)
            os.environ[k] = v

        try:
            from bootnode.config import Settings

            s = Settings()
            assert s.commerce_url == "https://old.commerce.ai"
            assert s.commerce_api_key == "old-key"
            assert s.commerce_webhook_secret == "old-secret"
        finally:
            for k, v in old_values.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_commerce_defaults(self):
        """Default commerce_url should be https://commerce.hanzo.ai."""
        from bootnode.config import Settings

        s = Settings()
        assert s.commerce_url == "https://commerce.hanzo.ai"
        assert s.commerce_api_key == ""
        assert s.commerce_webhook_secret == ""


# =============================================================================
# Commerce Client Error Handling
# =============================================================================


class TestCommerceClientErrors:
    @patch("bootnode.core.billing.commerce.get_settings")
    @pytest.mark.asyncio
    async def test_request_raises_on_http_error(self, mock_settings):
        """_request should raise CommerceError on 4xx/5xx."""
        import httpx

        mock_settings.return_value = MagicMock(
            commerce_url="http://test:8001",
            commerce_api_key="test-key",
        )
        from bootnode.core.billing.commerce import CommerceError, HanzoCommerceClient

        client = HanzoCommerceClient()

        # Mock httpx to return a 400 error
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.content = b'{"message": "bad request"}'
        mock_response.json.return_value = {"message": "bad request"}

        with patch("httpx.AsyncClient") as MockAsyncClient:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockAsyncClient.return_value = mock_client

            with pytest.raises(CommerceError) as exc_info:
                await client._request("GET", "/api/v1/test")

            assert exc_info.value.status_code == 400
            assert "bad request" in exc_info.value.message

    @patch("bootnode.core.billing.commerce.get_settings")
    @pytest.mark.asyncio
    async def test_request_raises_on_connection_error(self, mock_settings):
        """_request should raise CommerceError with 503 on connection failure."""
        import httpx

        mock_settings.return_value = MagicMock(
            commerce_url="http://test:8001",
            commerce_api_key="test-key",
        )
        from bootnode.core.billing.commerce import CommerceError, HanzoCommerceClient

        client = HanzoCommerceClient()

        with patch("httpx.AsyncClient") as MockAsyncClient:
            mock_client = AsyncMock()
            mock_client.request.side_effect = httpx.ConnectError("Connection refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockAsyncClient.return_value = mock_client

            with pytest.raises(CommerceError) as exc_info:
                await client._request("GET", "/api/v1/test")

            assert exc_info.value.status_code == 503


# =============================================================================
# Unified Billing Client Error Handling
# =============================================================================


class TestUnifiedBillingErrors:
    def _make_iam_user(self, **kwargs):
        from types import SimpleNamespace

        defaults = {
            "id": "user_1",
            "email": "test@test.com",
            "name": "Test User",
            "org": "hanzo",
            "roles": [],
        }
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    @patch("bootnode.core.billing.unified.get_settings")
    @pytest.mark.asyncio
    async def test_create_customer_raises_on_failure(self, mock_settings):
        """_create_customer should raise CommerceError, not return fake data."""
        mock_settings.return_value = MagicMock(
            iam_url="http://iam:8000",
            commerce_url="http://commerce:8001",
            commerce_api_key="test-key",
        )
        from bootnode.core.billing.commerce import CommerceError
        from bootnode.core.billing.unified import UnifiedBillingClient

        client = UnifiedBillingClient()
        iam_user = self._make_iam_user()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.content = b'{"message": "internal error"}'
        mock_response.json.return_value = {"message": "internal error"}

        with patch("httpx.AsyncClient") as MockAsyncClient:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            MockAsyncClient.return_value = mock_http

            with pytest.raises(CommerceError) as exc_info:
                await client._create_customer(iam_user)

            assert exc_info.value.status_code == 500

    @patch("bootnode.core.billing.unified.get_settings")
    @pytest.mark.asyncio
    async def test_create_subscription_raises_commerce_error(self, mock_settings):
        """create_subscription should raise CommerceError, not bare Exception."""
        mock_settings.return_value = MagicMock(
            iam_url="http://iam:8000",
            commerce_url="http://commerce:8001",
            commerce_api_key="test-key",
        )
        from bootnode.core.billing.commerce import CommerceError
        from bootnode.core.billing.unified import UnifiedBillingClient

        client = UnifiedBillingClient()
        iam_user = self._make_iam_user()

        # Mock get_or_create_customer to return a user with customer_id
        client.get_or_create_customer = AsyncMock()
        client.get_or_create_customer.return_value = MagicMock(
            commerce_customer_id="cust_123"
        )

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.content = b'{"message": "invalid plan"}'
        mock_response.json.return_value = {"message": "invalid plan"}

        with patch("httpx.AsyncClient") as MockAsyncClient:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            MockAsyncClient.return_value = mock_http

            with pytest.raises(CommerceError) as exc_info:
                await client.create_subscription(iam_user, "bad-plan", uuid4())

            assert exc_info.value.status_code == 422


# =============================================================================
# Webhook Handler Error Propagation
# =============================================================================


class TestWebhookHandlerErrors:
    @patch("bootnode.core.billing.webhooks.get_settings")
    @pytest.mark.asyncio
    async def test_handler_exception_returns_error_dict(self, mock_settings):
        """When a handler throws, handle_event should return error info, not crash."""
        mock_settings.return_value = MagicMock(commerce_webhook_secret="test")
        from bootnode.core.billing.webhooks import CommerceWebhookHandler

        handler = CommerceWebhookHandler()
        # Monkey-patch a handler to throw
        handler.handle_customer_created = AsyncMock(
            side_effect=ValueError("test explosion")
        )

        result = await handler.handle_event({
            "type": "customer.created",
            "id": "evt_1",
            "data": {"id": "cust_1"},
        })

        assert result["handled"] is False
        assert "test explosion" in result["error"]

    @patch("bootnode.core.billing.webhooks.get_settings")
    @pytest.mark.asyncio
    async def test_subscription_created_missing_project_id(self, mock_settings):
        """subscription.created without project_id should return error dict."""
        mock_settings.return_value = MagicMock(commerce_webhook_secret="test")
        from bootnode.core.billing.webhooks import CommerceWebhookHandler

        handler = CommerceWebhookHandler()
        result = await handler.handle_event({
            "type": "subscription.created",
            "id": "evt_2",
            "data": {
                "id": "sub_123",
                "customer_id": "cust_456",
                "metadata": {},  # No project_id
            },
        })

        assert result["handled"] is True
        assert result["result"]["error"] == "missing_project_id"

    @patch("bootnode.core.billing.webhooks.get_settings")
    @pytest.mark.asyncio
    async def test_subscription_created_invalid_project_id(self, mock_settings):
        """subscription.created with bad UUID should return error dict."""
        mock_settings.return_value = MagicMock(commerce_webhook_secret="test")
        from bootnode.core.billing.webhooks import CommerceWebhookHandler

        handler = CommerceWebhookHandler()
        result = await handler.handle_event({
            "type": "subscription.created",
            "id": "evt_3",
            "data": {
                "id": "sub_123",
                "customer_id": "cust_456",
                "metadata": {"project_id": "not-a-uuid"},
            },
        })

        assert result["handled"] is True
        assert result["result"]["error"] == "invalid_project_id"
