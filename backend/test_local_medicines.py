"""
Local integration test for:
  - My Medicines   (GET /api/v1/medicines)
  - Today Reminders (GET /api/v1/reminders/today)
  - Medication History (GET /api/v1/medicines/history)

Inserts real test data directly into DB, tests all APIs, cleans up.
Run: py test_local_medicines.py
"""
import sys
import json
import uuid
from datetime import date, datetime, timedelta, timezone, time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# ─── Setup path ────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000/api/v1"
DB_URL = "mysql+pymysql://health_user:H3althP4ss@localhost:3306/health_companion"

import urllib.request
import urllib.error

def req(method, path, body=None, token=None):
    url = BASE_URL + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode()
        print(f"  HTTP {e.code} on {method} {path}: {body_txt[:300]}")
        return None

def ok(label, condition, detail=""):
    if condition:
        print(f"  ✅  {label}")
    else:
        print(f"  ❌  {label} {detail}")
    return condition

def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")

# ─── DB seed helpers ────────────────────────────────────────────────────────
engine = create_engine(DB_URL, echo=False)

def seed_data(user_id: str):
    """Insert test medicine schedules and reminders for the user."""
    with Session(engine) as db:
        today = date.today()
        yesterday = today - timedelta(days=1)

        # 1. Insert 2 active schedules
        db.execute(text("""
            INSERT IGNORE INTO medicine_schedules
              (user_id, medicine_name, dosage, frequency, duration_days, notes,
               start_date, end_date, is_active, created_at, updated_at)
            VALUES
              (:uid, 'Amoxicillin 500mg', '500mg', 'Twice daily (BID)', 7,
               'Take after food', :start, :end1, 1, NOW(), NOW()),
              (:uid, 'Paracetamol 650mg', '650mg', 'Three times daily', 5,
               'For fever', :start, :end2, 1, NOW(), NOW())
        """), {"uid": user_id, "start": today, "end1": today + timedelta(days=7),
               "end2": today + timedelta(days=5)})
        db.commit()

        # 2. Get the schedule IDs we just inserted
        rows = db.execute(text("""
            SELECT id, medicine_name FROM medicine_schedules
            WHERE user_id = :uid ORDER BY created_at DESC LIMIT 2
        """), {"uid": user_id}).fetchall()

        if not rows:
            print("  ⚠️  No schedules found after seed!")
            return []

        schedule_ids = [(r[0], r[1]) for r in rows]
        print(f"  Seeded schedules: {schedule_ids}")

        # 3. Insert today's reminders for first schedule (amoxicillin - BID = 2 per day)
        sid1 = schedule_ids[0][0]
        sid2 = schedule_ids[1][0]
        t8  = datetime.combine(today, time(8, 0), tzinfo=timezone.utc)
        t14 = datetime.combine(today, time(14, 0), tzinfo=timezone.utc)
        t20 = datetime.combine(today, time(20, 0), tzinfo=timezone.utc)

        # Amoxicillin: 8am (pending), 8pm (pending)
        # Paracetamol: 8am (taken), 2pm (pending), 8pm (pending)
        # Yesterday: taken+skipped for history
        y8  = datetime.combine(yesterday, time(8, 0), tzinfo=timezone.utc)
        y20 = datetime.combine(yesterday, time(20, 0), tzinfo=timezone.utc)

        db.execute(text("""
            INSERT IGNORE INTO reminders
              (schedule_id, user_id, reminder_time, status, taken_at, created_at, updated_at)
            VALUES
              (:s1, :uid, :t8,  'pending', NULL, NOW(), NOW()),
              (:s1, :uid, :t20, 'pending', NULL, NOW(), NOW()),
              (:s2, :uid, :t8,  'taken',   NOW(), NOW(), NOW()),
              (:s2, :uid, :t14, 'pending', NULL, NOW(), NOW()),
              (:s2, :uid, :t20, 'pending', NULL, NOW(), NOW()),
              (:s1, :uid, :y8,  'taken',   NOW(), NOW(), NOW()),
              (:s1, :uid, :y20, 'skipped', NULL, NOW(), NOW())
        """), {"s1": sid1, "s2": sid2, "uid": user_id,
               "t8": t8, "t14": t14, "t20": t20, "y8": y8, "y20": y20})
        db.commit()
        print(f"  Seeded reminders for today + yesterday")
        return schedule_ids

def cleanup_data(user_id: str):
    with Session(engine) as db:
        db.execute(text("DELETE FROM reminders WHERE user_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM medicine_schedules WHERE user_id = :uid"), {"uid": user_id})
        db.commit()
    print("  Cleaned up test data")

# ─── Main test ──────────────────────────────────────────────────────────────
section("STEP 1 — Register & Login test user")
email = f"test{uuid.uuid4().hex[:8]}@gmail.com"
password = "TestPass123!"

reg = req("POST", "/auth/signup", {"email": email, "password": password})
ok("Register new user", reg and reg.get("success"))

# If signup returns a token directly, use it; otherwise login separately
token = None
if reg and reg.get("data", {}).get("access_token"):
    token = reg["data"]["access_token"]
    user_id = reg["data"].get("user", {}).get("id")
    ok("Got token from signup", bool(token))
else:
    login = req("POST", "/auth/login", {"email": email, "password": password})
    ok("Login success", login and login.get("data", {}).get("access_token"))
    if not login or not login.get("data", {}).get("access_token"):
        print("\n❌ Cannot proceed — login failed")
        sys.exit(1)
    token = login["data"]["access_token"]
    user_id = None

# Get user profile to get user_id
profile = req("GET", "/auth/me", token=token)
if profile and profile.get("data"):
    user_id = profile["data"].get("id") or user_id
ok("Got user_id", bool(user_id), f"(id={user_id})")

# ─── Seed real DB data ───────────────────────────────────────────────────────
section("STEP 2 — Seed test data into DB")
schedule_ids = seed_data(user_id)
if not schedule_ids:
    print("❌ Seed failed, aborting")
    cleanup_data(user_id)
    sys.exit(1)

# ─── Test My Medicines ───────────────────────────────────────────────────────
section("STEP 3 — My Medicines  (GET /medicines)")
meds = req("GET", "/medicines", token=token)
ok("Response success", meds and meds.get("success"))
ok("Returns list", isinstance(meds.get("data"), list) if meds else False)
ok("Has 2+ medicines", len(meds["data"]) >= 2 if meds else False,
   f"(got {len(meds['data']) if meds else 0})")

if meds and meds.get("data"):
    m = meds["data"][0]
    ok("Has medicine_name", "medicine_name" in m)
    ok("Has dosage", "dosage" in m)
    ok("Has frequency", "frequency" in m)
    ok("Has is_active", "is_active" in m)
    ok("Has start_date", "start_date" in m)
    ok("Has end_date", "end_date" in m)
    print(f"  Sample: {m.get('medicine_name')} | {m.get('dosage')} | {m.get('frequency')}")

# ─── Test Medicine Detail ────────────────────────────────────────────────────
section("STEP 4 — Medicine Detail  (GET /medicines/:id)")
first_id = schedule_ids[0][0]
detail = req("GET", f"/medicines/{first_id}", token=token)
ok("Response success", detail and detail.get("success"))
ok("Has reminders_today list", isinstance(detail.get("data", {}).get("reminders_today"), list) if detail else False,
   f"(got {detail['data'].get('reminders_today') if detail else 'N/A'})")

# ─── Test Today's Reminders ──────────────────────────────────────────────────
section("STEP 5 — Today's Reminders  (GET /reminders/today)")
today_r = req("GET", "/reminders/today", token=token)
ok("Response success", today_r and today_r.get("success"))
ok("Returns list", isinstance(today_r.get("data"), list) if today_r else False)
ok("Has 5 reminders today", len(today_r["data"]) >= 5 if today_r else False,
   f"(got {len(today_r['data']) if today_r else 0})")

if today_r and today_r.get("data"):
    r = today_r["data"][0]
    ok("Has medicine_name (not Unknown)", r.get("medicine_name") != "Unknown", f"got={r.get('medicine_name')}")
    ok("Has reminder_time", "reminder_time" in r)
    ok("Has status", r.get("status") in ["pending", "taken", "skipped"])
    ok("Has dosage", "dosage" in r)
    pending = [x for x in today_r["data"] if x["status"] == "pending"]
    taken   = [x for x in today_r["data"] if x["status"] == "taken"]
    print(f"  Summary: {len(pending)} pending, {len(taken)} taken, {len(today_r['data'])} total")

# ─── Test Mark Taken ─────────────────────────────────────────────────────────
section("STEP 6 — Mark Reminder as Taken")
pending_ids = [x["id"] for x in today_r["data"] if x["status"] == "pending"] if today_r else []
if pending_ids:
    taken_r = req("PATCH", f"/reminders/{pending_ids[0]}/taken", token=token)
    ok("Mark taken success", taken_r and taken_r.get("success"))
    ok("Status = taken", taken_r["data"]["status"] == "taken" if taken_r else False)
    ok("taken_at is set", taken_r["data"].get("taken_at") is not None if taken_r else False)

    # Try to mark again — should fail
    duplicate = req("PATCH", f"/reminders/{pending_ids[0]}/taken", token=token)
    ok("Double-mark returns error (idempotency guard)", not (duplicate and duplicate.get("success")))

# ─── Test Mark Skipped ───────────────────────────────────────────────────────
if len(pending_ids) > 1:
    skipped_r = req("PATCH", f"/reminders/{pending_ids[1]}/skipped", token=token)
    ok("Mark skipped success", skipped_r and skipped_r.get("success"))
    ok("Status = skipped", skipped_r["data"]["status"] == "skipped" if skipped_r else False)

# ─── Test Medication History ──────────────────────────────────────────────────
section("STEP 7 — Medication History  (GET /medicines/history)")
hist = req("GET", "/medicines/history?days=7", token=token)
ok("Response success", hist and hist.get("success"))
ok("Returns list", isinstance(hist.get("data"), list) if hist else False)
ok("Has at least 1 day of history", len(hist["data"]) >= 1 if hist else False,
   f"(got {len(hist['data']) if hist else 0} days)")

if hist and hist.get("data"):
    day = hist["data"][0]
    ok("Day has 'date' field", "date" in day)
    ok("Day has 'reminders' list", isinstance(day.get("reminders"), list))
    if day.get("reminders"):
        r = day["reminders"][0]
        ok("Reminder has medicine_name", r.get("medicine_name") not in [None, "Unknown"])
        ok("Reminder status is taken/skipped", r.get("status") in ["taken", "skipped"])
    print(f"  Days returned: {[d['date'] for d in hist['data']]}")

# ─── Test history with days filter ─────────────────────────────────────────
hist30 = req("GET", "/medicines/history?days=30", token=token)
ok("History 30 days works", hist30 and hist30.get("success"))

# ─── Test Deactivate Medicine ─────────────────────────────────────────────
section("STEP 8 — Deactivate Medicine")
sid_to_deactivate = schedule_ids[1][0]
deact = req("PATCH", f"/medicines/{sid_to_deactivate}/deactivate", token=token)
ok("Deactivate success", deact and deact.get("success"))

# Re-fetch medicines — should show inactive
meds2 = req("GET", "/medicines", token=token)
deactivated = next((m for m in meds2["data"] if m["id"] == sid_to_deactivate), None) if meds2 else None
ok("Medicine shows is_active=False after deactivate",
   deactivated and not deactivated["is_active"])

# ─── Cleanup & Summary ──────────────────────────────────────────────────────
section("STEP 9 — Cleanup")
cleanup_data(user_id)

print("\n" + "="*55)
print("  ✅  All tests completed!")
print("="*55 + "\n")



