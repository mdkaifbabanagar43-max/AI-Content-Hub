# Security & Access Control Document
## ShortcutAI — AI Content Hub

---

## 1. Executive Summary & Security Model

ShortcutAI enforces a **Zero-Trust Backend Security Model**. Every client request attempting to mutate data, upload media, access blueprints, or trigger AI rendering pipelines must present a cryptographically verified Firebase Authentication JSON Web Token (JWT). The system enforces strict multi-tenant project isolation and role-based entitlement gating.

---

## 2. Authentication & Identity Verification

### 2.1 Identity Provider & Token Verification
- **Identity Provider:** Firebase Authentication (OAuth 2.0 / OpenID Connect).
- **Client Header:** All protected API requests must transmit:
  ```http
  Authorization: Bearer <FIREBASE_ID_TOKEN>
  ```
- **Backend Verification Dependency (`core/auth.py`):**
  - The `get_current_user` FastAPI dependency intercepts incoming requests.
  - The token is cryptographically validated using `firebase_admin.auth.verify_id_token(token)`.
  - The authenticated `user_id` is derived **strictly from verified JWT claims** (`decoded_token['uid']`).
  - Request parameters cannot spoof or override the authenticated `user_id`.

---

## 3. Verified Zero-Vulnerability Audit Baseline (Security Remediation Record)

ShortcutAI has undergone a rigorous security remediation pass to establish a zero-vulnerability baseline:

- **Authentication Integrity:** Total removal of all `test_token` and `dev_token` development bypasses. 100% cryptographic Firebase Admin SDK verification is enforced in `core/auth.py` with no exceptions.
- **SSRF & Cloud Metadata Filtering:** `core/security.py` implements a robust URL validator blocking loopback, link-local, and cloud metadata IP ranges (`169.254.0.0/16`, `127.0.0.0/8`, `10.0.0.0/8`, `::1`, etc.). All outbound web requests perform hop-by-hop redirect re-validation to prevent DNS rebinding and SSRF bypasses.
- **CORS Allowlist:** Strict canonical origin allowlist enforced, eliminating all wildcard (`*`) subdomains. Allowed origins: `https://cloneframe.com`, `https://app.cloneframe.com`, `https://shortcutsai.vercel.app`.
- **Firestore Rules Hardening:** Firebase Security Rules employ a `notUpdatingProtectedFields()` check, strictly protecting `credits`, `plan`, `subscription_status`, and `role` from client-side mutation.
- **Rate Limiting:** A sliding-window rate limiter is implemented in `core/rate_limiter.py` to protect AI endpoints from abuse and brute-force resource exhaustion.
- **Production API Docs:** Swagger UI and OpenAPI schemas are disabled in production environments (`docs_url=None`, `redoc_url=None`) to prevent endpoint enumeration.

---

## 4. Multi-Tenant Project Isolation & Anti-IDOR

To eliminate **Insecure Direct Object Reference (IDOR)** risks:
1. **Firestore Path Scoping:** All repositories (`SourceVideoRepository`, `BlueprintRepository`, etc.) scope database operations strictly under `/users/{user_id}/projects/{project_id}/...`.
2. **Cross-Tenant Access Denial:** Even if an attacker guesses a valid `project_id` or `blueprint_id` belonging to another user, queries automatically restrict document lookups to the caller's verified `user_id`.
3. **Attempt Quarantine:** Raw video clips from rejected generation attempts are stored in `GenerationAttempt` records with status `"REJECTED"` and are strictly excluded from downstream timeline assembly.

---

## 5. Entitlement Gating, Credits & Approval Gate Security

### 5.1 Plan Entitlement Matrix
Features and operational limits are gated by user subscription tiers (`free`, `starter`, `creator`, `agency`):
- `max_resolution`: 720p (Free/Starter), 1080p (Creator), 4K (Agency).
- `max_video_minutes`: 1 min (Free), 10 mins (Starter), 30 mins (Creator), 60 mins (Agency).
- `concurrent_jobs`: Rate-limited per tier to prevent resource exhaustion.

### 5.2 Pre-Flight Credit Verification
- Before dispatching expensive AI workloads (Veo generation, ElevenLabs TTS, Dubbing), the backend verifies that the user possesses sufficient credits.
- If credits are insufficient, the operation halts immediately with `HTTP 402 / 403 Payment Required`.

### 5.3 Production Approval Gate Security
To prevent accidental or unauthorized credit burn on generative video:
- A `ProductionBlueprint` is synthesized in the `READY_FOR_APPROVAL` state.
- The generation endpoint strictly enforces that `blueprint.status == "APPROVED"`.
- Attempting to generate a blueprint in `DRAFT` or `READY_FOR_APPROVAL` status returns `HTTP 400 Bad Request`.

---

## 6. Cloud Infrastructure & Secrets Protection

### 6.1 Server-Side Secret Isolation
- All third-party provider credentials (Google Cloud Service Account, ElevenLabs, SyncLabs, Pexels) are stored exclusively in Cloud Run environment variables or Secret Manager.
- No API keys are ever exposed to the client-side bundle.

### 6.2 IAM Signed URLs for Google Cloud Storage
- Video uploads use **Google Cloud Storage V4 Signed PUT URLs**.
- Signed URLs are generated server-side using `google.auth.iam.Signer` via the IAM Credentials API, bound to the Cloud Run service account.
- Upload URLs expire automatically after 15 minutes and restrict uploads to specific project folders.
- GCS buckets are private with public access denied by default.
