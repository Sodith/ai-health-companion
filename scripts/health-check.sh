#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  scripts/health-check.sh
#  Verify all AI Health Companion services are alive
#
#  Usage:
#    chmod +x scripts/health-check.sh
#    ./scripts/health-check.sh
#
#  Exit codes:  0 = all healthy,  1 = one or more unhealthy
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

PASS=0
FAIL=0

check() {
  local name="$1"
  local url="$2"
  local expected="${3:-200}"

  http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" || echo "000")
  if [[ "$http_code" == "$expected" ]]; then
    echo "  ✅  ${name} → HTTP ${http_code}  (${url})"
    ((PASS++)) || true
  else
    echo "  ❌  ${name} → HTTP ${http_code}  (expected ${expected})  (${url})"
    ((FAIL++)) || true
  fi
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  AI Health Companion – Service Health Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Frontend (nginx serves Angular SPA)
check "Frontend  (Angular/nginx)"  "http://localhost/"              200

# Backend health endpoint
check "Backend   (FastAPI /health)" "http://localhost:8000/health"  200

# API docs (only available when APP_DEBUG=true; skip in strict prod)
# check "API Docs  (Swagger UI)"      "http://localhost:8000/docs"    200

# MySQL container state
MYSQL_STATE=$(docker inspect --format='{{.State.Health.Status}}' ai-health-mysql 2>/dev/null || echo "not found")
if [[ "$MYSQL_STATE" == "healthy" ]]; then
  echo "  ✅  MySQL container → ${MYSQL_STATE}"
  ((PASS++)) || true
else
  echo "  ❌  MySQL container → ${MYSQL_STATE}  (expected: healthy)"
  ((FAIL++)) || true
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Results: ${PASS} passed, ${FAIL} failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

[[ $FAIL -eq 0 ]]

