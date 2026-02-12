#!/bin/bash
# Bootnode E2E Test Suite
# Tests all critical API endpoints and workflows

set -e

API_URL="${API_URL:-http://localhost:8100}"
TOKEN=""
PROJECT_ID=""
USER_ID=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    PASSED=$((PASSED + 1))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    echo -e "${RED}       Response: $2${NC}"
    FAILED=$((FAILED + 1))
}

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Test helper
test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    local expected_status="$5"

    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API_URL$endpoint" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $TOKEN" \
            -d "$data" 2>/dev/null)
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API_URL$endpoint" \
            -H "Authorization: Bearer $TOKEN" 2>/dev/null)
    fi

    status=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [ "$status" = "$expected_status" ]; then
        log_pass "$name (HTTP $status)"
        echo "$body"
    else
        log_fail "$name (expected $expected_status, got $status)" "$body"
        echo ""
    fi
}

echo "============================================"
echo "  BOOTNODE E2E TEST SUITE"
echo "============================================"
echo ""
echo "API URL: $API_URL"
echo ""

# ============================================
# 1. HEALTH CHECK
# ============================================
log_info "Testing Health Check..."
health_response=$(curl -s "$API_URL/health")
if echo "$health_response" | grep -q '"status":"healthy"'; then
    log_pass "Health check endpoint"
else
    log_fail "Health check endpoint" "$health_response"
    echo "API not running. Exiting."
    exit 1
fi
echo ""

# ============================================
# 2. AUTHENTICATION - REGISTER
# ============================================
log_info "Testing Authentication..."
TEST_EMAIL="e2e-test-$(date +%s)@bootno.de"
TEST_PASSWORD="testpass123"
TEST_NAME="E2E Test User"

register_response=$(curl -s -X POST "$API_URL/v1/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\",\"name\":\"$TEST_NAME\"}")

if echo "$register_response" | grep -q '"access_token"'; then
    log_pass "User registration"
    TOKEN=$(echo "$register_response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    USER_ID=$(echo "$register_response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
else
    log_fail "User registration" "$register_response"
fi

# ============================================
# 3. AUTHENTICATION - LOGIN
# ============================================
login_response=$(curl -s -X POST "$API_URL/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}")

if echo "$login_response" | grep -q '"access_token"'; then
    log_pass "User login"
    TOKEN=$(echo "$login_response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
else
    log_fail "User login" "$login_response"
fi

# ============================================
# 4. AUTHENTICATION - GET ME
# ============================================
me_response=$(curl -s "$API_URL/v1/auth/me" \
    -H "Authorization: Bearer $TOKEN")

if echo "$me_response" | grep -q '"email"'; then
    log_pass "Get current user (/auth/me)"
else
    log_fail "Get current user (/auth/me)" "$me_response"
fi
echo ""

# ============================================
# 5. CREATE PROJECT
# ============================================
log_info "Testing Project Management..."
project_response=$(curl -s -X POST "$API_URL/v1/auth/projects" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{\"name\":\"E2E Test Project\",\"owner_id\":\"$USER_ID\"}")

if echo "$project_response" | grep -q '"id"'; then
    log_pass "Create project"
    PROJECT_ID=$(echo "$project_response" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
else
    log_fail "Create project" "$project_response"
fi
echo ""

# ============================================
# 6. API KEYS
# ============================================
log_info "Testing API Keys..."

# Create API Key
key_response=$(curl -s -X POST "$API_URL/v1/auth/keys" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{\"project_id\":\"$PROJECT_ID\",\"name\":\"E2E Test Key\"}")

if echo "$key_response" | grep -q '"id"'; then
    log_pass "Create API key"
    KEY_ID=$(echo "$key_response" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
    API_KEY=$(echo "$key_response" | grep -o '"key":"[^"]*"' | cut -d'"' -f4)
else
    log_fail "Create API key" "$key_response"
fi

# List API Keys
list_keys_response=$(curl -s "$API_URL/v1/auth/keys?project_id=$PROJECT_ID" \
    -H "Authorization: Bearer $TOKEN")

if echo "$list_keys_response" | grep -q 'E2E Test Key'; then
    log_pass "List API keys"
else
    log_fail "List API keys" "$list_keys_response"
fi
echo ""

# ============================================
# 7. TEAM MANAGEMENT
# ============================================
log_info "Testing Team Management..."

# Invite Team Member
invite_response=$(curl -s -X POST "$API_URL/v1/team" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"email":"e2e-invite@bootno.de","role":"developer"}')

if echo "$invite_response" | grep -q '"id"'; then
    log_pass "Invite team member"
    MEMBER_ID=$(echo "$invite_response" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
else
    log_fail "Invite team member" "$invite_response"
fi

# List Team Members
list_team_response=$(curl -s "$API_URL/v1/team" \
    -H "Authorization: Bearer $TOKEN")

if echo "$list_team_response" | grep -q '"members"'; then
    log_pass "List team members"
else
    log_fail "List team members" "$list_team_response"
fi

# Update Team Member
if [ -n "$MEMBER_ID" ]; then
    update_response=$(curl -s -X PATCH "$API_URL/v1/team/$MEMBER_ID" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d '{"role":"admin"}')

    if echo "$update_response" | grep -q '"role":"admin"'; then
        log_pass "Update team member role"
    else
        log_fail "Update team member role" "$update_response"
    fi

    # Delete Team Member
    delete_member_response=$(curl -s -X DELETE "$API_URL/v1/team/$MEMBER_ID" \
        -H "Authorization: Bearer $TOKEN" \
        -w "\n%{http_code}")

    delete_status=$(echo "$delete_member_response" | tail -1)
    if [ "$delete_status" = "204" ]; then
        log_pass "Remove team member"
    else
        log_fail "Remove team member" "$delete_member_response"
    fi
fi
echo ""

# ============================================
# 8. WEBHOOKS
# ============================================
log_info "Testing Webhooks..."

# Create Webhook
webhook_response=$(curl -s -X POST "$API_URL/v1/webhooks" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"name":"E2E Test Webhook","url":"https://httpbin.org/post","chain":"ethereum","event_type":"ADDRESS_ACTIVITY"}')

if echo "$webhook_response" | grep -q '"id"'; then
    log_pass "Create webhook"
    WEBHOOK_ID=$(echo "$webhook_response" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
else
    log_fail "Create webhook" "$webhook_response"
fi

# List Webhooks
list_webhooks_response=$(curl -s "$API_URL/v1/webhooks" \
    -H "Authorization: Bearer $TOKEN")

if echo "$list_webhooks_response" | grep -q 'E2E Test Webhook'; then
    log_pass "List webhooks"
else
    log_fail "List webhooks" "$list_webhooks_response"
fi

# Update Webhook
if [ -n "$WEBHOOK_ID" ]; then
    update_webhook_response=$(curl -s -X PATCH "$API_URL/v1/webhooks/$WEBHOOK_ID" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d '{"name":"E2E Updated Webhook"}')

    if echo "$update_webhook_response" | grep -q 'E2E Updated Webhook'; then
        log_pass "Update webhook"
    else
        log_fail "Update webhook" "$update_webhook_response"
    fi

    # Delete Webhook
    delete_webhook_response=$(curl -s -X DELETE "$API_URL/v1/webhooks/$WEBHOOK_ID" \
        -H "Authorization: Bearer $TOKEN" \
        -w "\n%{http_code}")

    delete_webhook_status=$(echo "$delete_webhook_response" | tail -1)
    if [ "$delete_webhook_status" = "204" ] || [ "$delete_webhook_status" = "200" ]; then
        log_pass "Delete webhook"
    else
        log_fail "Delete webhook" "$delete_webhook_response"
    fi
fi
echo ""

# ============================================
# 9. CHAINS
# ============================================
log_info "Testing Chains API..."

chains_response=$(curl -s "$API_URL/v1/chains" \
    -H "Authorization: Bearer $TOKEN")

if echo "$chains_response" | grep -q 'ethereum\|Ethereum'; then
    log_pass "List chains"
else
    log_fail "List chains" "$chains_response"
fi
echo ""

# ============================================
# 10. CLEANUP - Delete API Key
# ============================================
log_info "Cleaning up..."

if [ -n "$KEY_ID" ]; then
    delete_key_response=$(curl -s -X DELETE "$API_URL/v1/auth/keys/$KEY_ID" \
        -H "Authorization: Bearer $TOKEN" \
        -w "\n%{http_code}")

    delete_key_status=$(echo "$delete_key_response" | tail -1)
    if [ "$delete_key_status" = "204" ] || [ "$delete_key_status" = "200" ]; then
        log_pass "Delete API key (cleanup)"
    else
        log_fail "Delete API key (cleanup)" "$delete_key_response"
    fi
fi

echo ""
echo "============================================"
echo "  TEST RESULTS"
echo "============================================"
echo -e "  ${GREEN}Passed: $PASSED${NC}"
echo -e "  ${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
