#!/bin/bash
echo "=== Creating demo users ==="

# User 1
R1=$(curl -s -X POST http://localhost/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"user1@test.com","password":"Pass1234!"}')
echo "user1@test.com / Pass1234! => $(echo $R1 | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["success"], d["message"])')"

# User 2
R2=$(curl -s -X POST http://localhost/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@ai-health.com","password":"Demo5678@"}')
echo "demo@ai-health.com / Demo5678@ => $(echo $R2 | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["success"], d["message"])')"

# User 3 - evaluator account
R3=$(curl -s -X POST http://localhost/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"evaluator@demo.com","password":"Eval1234!"}')
echo "evaluator@demo.com / Eval1234! => $(echo $R3 | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["success"], d["message"])')"

echo ""
echo "=== All users in DB ==="
docker exec ai-health-mysql mysql -u health_user \
  -pbiz1G7vOLG74ClXYiM5ssVXm2LrTXMuXiQu7Bur70Cs \
  health_companion \
  -e "SELECT email, is_active, created_at FROM users;" 2>/dev/null

echo ""
echo "=== Test Login for testuser@demo.com ==="
curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"testuser@demo.com","password":"Test1234!"}' | python3 -c "import json,sys; d=json.load(sys.stdin); print('Login OK:', d['success'])"

