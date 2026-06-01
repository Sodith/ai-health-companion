# 📸 AI Health Companion — Screenshots Guide

> This document describes every screenshot required for the final submission package.
> Follow the instructions for each screenshot to ensure evaluators can verify all features.

---

## How to Take Screenshots

- **Windows:** `Win + Shift + S` → select region → save as PNG
- **macOS:** `Cmd + Shift + 4` → select region → saved to Desktop
- **Linux:** `gnome-screenshot -a` or use Flameshot

**Storage location:** Place all screenshots in `docs/screenshots/`

```bash
mkdir -p docs/screenshots
```

---

## Screenshot 1 — Login Page

| Property | Value |
|----------|-------|
| **Filename** | `docs/screenshots/01_login.png` |
| **URL** | `http://YOUR_EC2_PUBLIC_IP/` or `http://localhost/` |

### What Must Be Visible
- [ ] Application title / logo ("AI Health Companion" or similar)
- [ ] Email input field
- [ ] Password input field (masked)
- [ ] "Login" or "Sign In" button
- [ ] Link to the Signup page ("Don't have an account? Register")
- [ ] The browser address bar showing the application URL
- [ ] Clean, professional Angular Material UI

### Why It Is Important
Demonstrates that the frontend is running, the Angular SPA is served correctly, and the authentication entry point is functional. Evaluators verify that the application is accessible via the public URL.

---

## Screenshot 2 — Signup Page

| Property | Value |
|----------|-------|
| **Filename** | `docs/screenshots/02_signup.png` |
| **URL** | `http://YOUR_EC2_PUBLIC_IP/signup` or `/register` |

### What Must Be Visible
- [ ] "Sign Up" or "Create Account" heading
- [ ] Email input field
- [ ] Password input field (masked)
- [ ] Confirm password field (if implemented)
- [ ] "Register" or "Create Account" submit button
- [ ] Link back to Login page
- [ ] Browser address bar

### Why It Is Important
Confirms that user registration is implemented and accessible. Evaluators verify the `/signup` route is protected and functional before authentication.

---

## Screenshot 3 — Dashboard

| Property | Value |
|----------|-------|
| **Filename** | `docs/screenshots/03_dashboard.png` |
| **URL** | `http://YOUR_EC2_PUBLIC_IP/dashboard` |

### What Must Be Visible
- [ ] User is logged in (name or email displayed in header/navbar)
- [ ] Navigation menu (links to: Upload, My Prescriptions, etc.)
- [ ] Welcome message or summary section
- [ ] "Upload Prescription" button or call-to-action
- [ ] No login form visible — authenticated state confirmed
- [ ] Browser address bar showing `/dashboard`

### Why It Is Important
Demonstrates that JWT authentication works end-to-end — the user is authenticated, the protected route is accessible, and the session is maintained. Evaluators verify that unauthenticated users cannot reach this page.

---

## Screenshot 4 — Upload Prescription

| Property | Value |
|----------|-------|
| **Filename** | `docs/screenshots/04_upload.png` |
| **URL** | `http://YOUR_EC2_PUBLIC_IP/prescriptions/upload` |

### What Must Be Visible
- [ ] File upload input / drag-and-drop area
- [ ] Accepted formats shown (PDF, JPG, PNG)
- [ ] File size limit shown (max 10 MB)
- [ ] Symptoms / notes text area
- [ ] "Upload" or "Submit" button
- [ ] **Bonus:** A prescription file already selected (filename visible in input)
- [ ] Browser address bar

### Why It Is Important
Demonstrates the core prescription upload feature — the primary data input mechanism of the application. Evaluators verify that the multipart form, file type restrictions, and symptom notes field are implemented.

---

## Screenshot 5 — Prescription List

| Property | Value |
|----------|-------|
| **Filename** | `docs/screenshots/05_prescription_list.png` |
| **URL** | `http://YOUR_EC2_PUBLIC_IP/prescriptions` |

### What Must Be Visible
- [ ] Table or card list showing previously uploaded prescriptions
- [ ] At least one prescription entry visible with:
  - Original filename
  - Upload date
  - File type (PDF / JPG / PNG)
  - Upload status badge
- [ ] "Analyze" or "View Analysis" button/link per entry
- [ ] Browser address bar

### Why It Is Important
Demonstrates that prescription data is persisted to MySQL and retrieved correctly for the authenticated user. Evaluators verify data isolation (users only see their own prescriptions).

---

## Screenshot 6 — AI Analysis Result

| Property | Value |
|----------|-------|
| **Filename** | `docs/screenshots/06_analysis_result.png` |
| **URL** | `http://YOUR_EC2_PUBLIC_IP/analysis/{id}` |

### What Must Be Visible
- [ ] **Disease Detected** section with extracted condition(s)
- [ ] **Medicines** section showing:
  - Medicine name(s)
  - Dosage (e.g., "500mg")
  - Frequency (e.g., "2 times daily")
  - Duration (e.g., "30 days")
  - Notes (e.g., "Take after meals")
- [ ] **Doctor Advice** section (list of advice items)
- [ ] **Lifestyle Changes** section (list of recommendations)
- [ ] Analysis status: "completed"
- [ ] Browser address bar

### Why It Is Important
This is the **core value proposition** of the application. The screenshot demonstrates end-to-end functionality: file upload → Gemini AI analysis → structured data extraction → persistence → frontend display. This is the most critical screenshot for the evaluation.

---

## Screenshot 7 — My Medicines

| Property | Value |
|----------|-------|
| **Filename** | `docs/screenshots/07_my_medicines.png` |
| **URL** | `http://YOUR_EC2_PUBLIC_IP/medicines` |

### What Must Be Visible
- [ ] "My Medicines" toolbar title
- [ ] At least one medicine card showing:
  - Medicine name (e.g., "Amoxicillin 500mg")
  - Dosage (e.g., "500mg")
  - Frequency (e.g., "Twice daily")
  - Start date and end date
  - Duration in days
  - Active/Inactive status chip (green = active)
- [ ] "Details" and "Stop" buttons per card
- [ ] Navigation icons (Reminders bell, History clock)
- [ ] Browser address bar showing `/medicines`

### Why It Is Important
Demonstrates the medicine schedule feature — AI-extracted medicines automatically create trackable schedules. Evaluators verify that the `medicine_schedules` table is populated correctly after AI analysis.

---

## Screenshot 8 — Today's Reminders

| Property | Value |
|----------|-------|
| **Filename** | `docs/screenshots/08_todays_reminders.png` |
| **URL** | `http://YOUR_EC2_PUBLIC_IP/medicines/reminders` |

### What Must Be Visible
- [ ] "Today's Reminders" toolbar title
- [ ] Summary chips showing: Total, Pending, Taken, Skipped counts
- [ ] Filter toggle (All / Pending / Taken / Skipped)
- [ ] At least one reminder card showing:
  - Time (e.g., "8:00 AM")
  - Medicine name (e.g., "Amoxicillin 500mg")
  - Dosage
  - Status chip (orange = pending, green = taken, red = skipped)
  - ✓ Taken and ✕ Skip action buttons (for pending reminders)
- [ ] Browser address bar

### Why It Is Important
Demonstrates the lazy reminder generation system — reminders are auto-created when the endpoint is first called each day. Evaluators verify the full reminder workflow including marking doses.

---

## Screenshot 9 — Medication History

| Property | Value |
|----------|-------|
| **Filename** | `docs/screenshots/09_medication_history.png` |
| **URL** | `http://YOUR_EC2_PUBLIC_IP/medicines/history` |

### What Must Be Visible
- [ ] "Medication History" toolbar title
- [ ] "Last N Days" filter dropdown (7/14/30/90 days)
- [ ] At least one day group showing:
  - Date header (e.g., "Sunday, June 1, 2026")
  - Taken/skipped counts for that day
  - Individual reminder entries with:
    - Medicine name
    - Dosage and scheduled time
    - Status chip (Taken = green, Skipped = red)
    - Taken-at timestamp (if taken)
- [ ] Browser address bar

### Why It Is Important
Demonstrates medication adherence tracking over time. Evaluators verify the history query groups reminders by date and that the taken/skipped status flow works end-to-end.

---

## Screenshot 10 — Docker Containers Running

| Property | Value |
|----------|-------|
| **Filename** | `docs/screenshots/10_docker_containers.png` |
| **Source** | EC2 terminal or local terminal |

### Command to Run

```bash
docker compose -f docker-compose.prod.yml ps
```

Or for a more visually complete view:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### What Must Be Visible
- [ ] Terminal window open (on EC2 or local)
- [ ] All three containers listed:
  - `ai-health-frontend` — Status: Up (healthy)
  - `ai-health-backend` — Status: Up (healthy)
  - `ai-health-mysql` — Status: Up (healthy)
- [ ] Port mappings visible (`:80`, `:8000`, `:3306`)
- [ ] All containers show `healthy` status

### Why It Is Important
Demonstrates that the Docker Compose stack is operational in production.

---

## Screenshot 11 — EC2 Deployment

| Property | Value |
|----------|-------|
| **Filename** | `docs/screenshots/11_ec2_deployment.png` |
| **Source** | AWS Console — EC2 Dashboard |

### What Must Be Visible
- [ ] AWS EC2 Console open in browser
- [ ] Instance named `ai-health-companion` (or similar)
- [ ] Instance state: **Running** (green dot)
- [ ] Instance type visible (e.g., t2.micro)
- [ ] **Public IPv4 address** visible
- [ ] AWS region visible in top-right corner

### Why It Is Important
Proves the application is deployed on actual AWS infrastructure.

---

## Screenshot 12 — Public URL Working

| Property | Value |
|----------|-------|
| **Filename** | `docs/screenshots/12_public_url.png` |
| **URL** | `http://YOUR_EC2_PUBLIC_IP/` |

### What Must Be Visible
- [ ] Browser address bar showing the **EC2 public IP address** (not `localhost`)
- [ ] The Angular application is fully loaded
- [ ] No error messages
- [ ] The browser's tab title shows the application name

### Why It Is Important
Definitive proof the application is publicly accessible on AWS EC2.

---

## Optional / Bonus Screenshots

### Screenshot 13 — Swagger API Documentation

| Property | Value |
|----------|-------|
| **Filename** | `docs/screenshots/13_swagger_docs.png` |
| **URL** | `http://YOUR_EC2_PUBLIC_IP/docs` |

**What to show:** The FastAPI Swagger UI with all endpoint groups expanded — `/auth`, `/prescriptions`, `/analysis`, `/medicines`, `/reminders`.

---

## Screenshot Checklist

| # | Screenshot | Filename | Taken |
|---|-----------|----------|-------|
| 1 | Login Page | `01_login.png` | ☐ |
| 2 | Signup Page | `02_signup.png` | ☐ |
| 3 | Dashboard | `03_dashboard.png` | ☐ |
| 4 | Upload Prescription | `04_upload.png` | ☐ |
| 5 | Prescription List | `05_prescription_list.png` | ☐ |
| 6 | AI Analysis Result | `06_analysis_result.png` | ☐ |
| 7 | My Medicines | `07_my_medicines.png` | ☐ |
| 8 | Today's Reminders | `08_todays_reminders.png` | ☐ |
| 9 | Medication History | `09_medication_history.png` | ☐ |
| 10 | Docker Containers Running | `10_docker_containers.png` | ☐ |
| 11 | EC2 Deployment (AWS Console) | `11_ec2_deployment.png` | ☐ |
| 12 | Public URL Working | `12_public_url.png` | ☐ |
| 13 | Swagger API Docs (bonus) | `13_swagger_docs.png` | ☐ |

---

*AI Health Companion — Screenshots Guide v2.0*

| Property | Value |
|----------|-------|
| **Filename** | `docs/screenshots/07_docker_containers.png` |
| **Source** | EC2 terminal or local terminal |

### Command to Run

```bash
docker compose -f docker-compose.prod.yml ps
```

Or for a more visually complete view:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### What Must Be Visible
- [ ] Terminal window open (on EC2 or local)
- [ ] All three containers listed:
  - `ai-health-frontend` — Status: Up (healthy)
  - `ai-health-backend` — Status: Up (healthy)
  - `ai-health-mysql` — Status: Up (healthy)
- [ ] Port mappings visible (`:80`, `:8000`, `:3306`)
- [ ] All containers show `healthy` status

### Why It Is Important
Demonstrates that the Docker Compose stack is operational in production. Evaluators verify containerisation skills and that all three services are running as expected.

---

## Screenshot 8 — EC2 Deployment

| Property | Value |
|----------|-------|
| **Filename** | `docs/screenshots/08_ec2_deployment.png` |
| **Source** | AWS Console — EC2 Dashboard |

### What Must Be Visible
- [ ] AWS EC2 Console open in browser
- [ ] Instance named `ai-health-companion` (or similar)
- [ ] Instance state: **Running** (green dot)
- [ ] Instance type visible (e.g., t3.small)
- [ ] **Public IPv4 address** or **Public IPv4 DNS** visible
- [ ] AWS region visible in top-right corner

### Why It Is Important
Proves the application is deployed on actual AWS infrastructure, not just running locally. Evaluators verify cloud deployment skills and that a real public-facing instance is configured.

---

## Screenshot 9 — Public URL Working

| Property | Value |
|----------|-------|
| **Filename** | `docs/screenshots/09_public_url.png` |
| **URL** | `http://YOUR_EC2_PUBLIC_IP/` |

### What Must Be Visible
- [ ] Browser address bar showing the **EC2 public IP address** (not `localhost`)
- [ ] The Angular application is fully loaded (login or dashboard page)
- [ ] No error messages (no "This site can't be reached", no 502/404)
- [ ] The browser's tab title shows the application name

### Why It Is Important
This is the definitive proof that the application is publicly accessible on AWS EC2. It ties together the frontend deployment, Nginx configuration, Docker networking, and EC2 Security Group configuration. Evaluators can paste this URL into their own browser to verify.

---

## Optional / Bonus Screenshots

### Screenshot 10 — Swagger API Documentation

| Property | Value |
|----------|-------|
| **Filename** | `docs/screenshots/10_swagger_docs.png` |
| **URL** | `http://YOUR_EC2_PUBLIC_IP:8000/docs` |

**What to show:** The FastAPI Swagger UI with all endpoints expanded — `/auth`, `/prescriptions`, `/analysis`.

**Why:** Demonstrates professional API documentation and that the backend is running correctly on port 8000.

---

### Screenshot 11 — Running Tests

| Property | Value |
|----------|-------|
| **Filename** | `docs/screenshots/11_test_results.png` |
| **Source** | Terminal (local or EC2) |

**Command:**
```bash
docker compose exec backend pytest tests/ -v
```

**What to show:** All test results with pass/fail indicators.

**Why:** Demonstrates test coverage and engineering quality standards.

---

## Screenshot Checklist

| # | Screenshot | Filename | Taken |
|---|-----------|----------|-------|
| 1 | Login Page | `01_login.png` | ☐ |
| 2 | Signup Page | `02_signup.png` | ☐ |
| 3 | Dashboard | `03_dashboard.png` | ☐ |
| 4 | Upload Prescription | `04_upload.png` | ☐ |
| 5 | Prescription List | `05_prescription_list.png` | ☐ |
| 6 | AI Analysis Result | `06_analysis_result.png` | ☐ |
| 7 | Docker Containers Running | `07_docker_containers.png` | ☐ |
| 8 | EC2 Deployment (AWS Console) | `08_ec2_deployment.png` | ☐ |
| 9 | Public URL Working | `09_public_url.png` | ☐ |
| 10 | Swagger API Docs (bonus) | `10_swagger_docs.png` | ☐ |
| 11 | Test Results (bonus) | `11_test_results.png` | ☐ |

---

*AI Health Companion — Screenshots Guide v1.0*

