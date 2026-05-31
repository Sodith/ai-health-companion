#!/bin/bash
# Full flow test script
BASE="http://localhost"

echo "=========================================="
echo " AI Health Companion - Full Flow Test"
echo "=========================================="

echo ""
echo "=== 1. Backend Health (direct) ==="
curl -s http://localhost:8000/health
echo ""

echo ""
echo "=== 2. Frontend reachable ==="
curl -s -o /dev/null -w "HTTP Status: %{http_code}" http://localhost/
echo ""

echo ""
echo "=== 3. Register new user ==="
REGISTER=$(curl -s -X POST $BASE/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"testuser@demo.com","password":"Test1234!","full_name":"Test User"}')
echo "$REGISTER"

echo ""
echo "=== 4. Login ==="
LOGIN=$(curl -s -X POST $BASE/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"testuser@demo.com","password":"Test1234!"}')
echo "$LOGIN"
TOKEN=$(echo "$LOGIN" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('data',{}).get('access_token','NO_TOKEN'))" 2>/dev/null)
echo "TOKEN: $TOKEN"

echo ""
echo "=== 5. Get Profile (auth required) ==="
curl -s $BASE/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
echo ""

echo ""
echo "=== 6. List Prescriptions (auth required) ==="
curl -s $BASE/api/v1/prescriptions \
  -H "Authorization: Bearer $TOKEN"
echo ""

echo ""
echo "=== API Docs URL ==="
echo "http://107.20.12.114/api/v1/docs"
echo "http://107.20.12.114/api/v1/redoc"

echo ""
echo "=========================================="
echo " Test Complete"
echo "=========================================="

