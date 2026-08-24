# SECURITY IMPACT REPORT — CLONEFRAME UNIVERSAL ENGINE

**Audited Systems:** Authentication, Authorization, SSRF Validator, Rate Limiting, OIDC, and Billing Atomic Locks.  
**Regression Test Target:** `backend/tests/test_security_audit.py` (15/15 PASS)  

---

## 1. Security Invariants & Protections

### A. Authentication & Multi-Tenant Authorization
* **Client Requests:** All `/projects/*` and `/api/*` routes strictly require a valid Firebase ID Token via `core.auth.get_current_user`.
* **Tenant Isolation:** Every Firestore query and GCS bucket folder is scoped to `{user_id}/{project_id}`. Cross-tenant access is rejected with `HTTP 403 Forbidden` / `HTTP 404 Not Found`.

### B. SSRF Protection on URL Ingestion
* The unified downloader (`core.video_downloader.py`) passes all URLs through strict pre-flight SSRF filters:
  - Blocks loopback (`127.0.0.1`, `localhost`).
  - Blocks private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
  - Blocks Cloud Metadata IP (`169.254.169.254`).
  - Restricts schemes strictly to `http` and `https`.

### C. Cloud Tasks OIDC Verification
* Background task execution workers verify Google Cloud OIDC tokens via `core.auth_oidc.verify_cloud_run_oidc_token`.
* Only the authorized Cloud Tasks Service Account (`shortcutai-backend@appspot.gserviceaccount.com`) is permitted to trigger execution webhooks.

### D. Atomic Credit Safety & Double-Spend Protection
* **Two-Phase Reservation:**
  1. `reserve_credits(user_id, cost)`: Freezes user credits before job dispatch.
  2. `commit_credits(user_id, job_id)`: Finalizes deduction upon successful render.
  3. `refund_credits(user_id, job_id)`: Automatically returns 100% of frozen credits upon pipeline failure or cancellation.
* **Deterministic Task Deduplication:** Cloud Tasks uses deterministic task IDs (`task_{job_id}_{attempt}`) preventing duplicate concurrent dispatches.

### E. Secret Hygiene
* No API keys, service account credentials, or signed URLs are ever written to stdout, logs, or client-facing responses.
* `GET /system-config` returns public limits and pricing structures only, with zero internal environment variables exposed.
