# Agile Feature Ticket List
## ShortcutAI — AI Content Hub

---

## 1. Epics Overview

### **Epic 1: Unified Video Cloning Engine (Phase 8)** `[STATUS: COMPLETED]`
Architecting the unified video cloning lifecycle, source video analysis, versioned clone/production blueprints, Project Bibles, PromptCompiler sanitization, QualityReviewer, and Canonical Generation Engine.

### **Epic 2: Production Hardening & Live Quality Consistency** `[STATUS: COMPLETED]`
Refining multi-scene visual consistency, character reference chaining, automated retry prompt enhancements, Visual Identity Merge, and comprehensive Security Remediation.

### **Epic 3: Unified Frontend Experience & Real-Time Telemetry** `[STATUS: IN PROGRESS]`
Consolidating the legacy cloner UI into a single flagship Video Cloner UI with interactive blueprint editing, real-time generation progress via SSE, and live frame review.

### **Epic 4: Monetization, Billing & Enterprise Readiness** `[STATUS: QUEUED]`
Integrating Stripe subscription billing, webhook event handlers, automated credit refill, and team workspace support.

### **Epic 5: CI/CD, Infrastructure & Security Hardening** `[STATUS: QUEUED]`
Automated GitHub Actions deployment to Cloud Run, custom domain mapping, security headers, and Cloud Tasks durable worker queues.

---

## 2. Completed Phase 8 Architectural Tickets

### ✅ Ticket 8A: Source Video Analysis Normalization
- **Status:** `COMPLETED`
- **Delivered:** `SourceAnalysis` with pacing, audio, and visual style extraction.

### ✅ Ticket 8B: Clone Blueprint Repository & Versioning
- **Status:** `COMPLETED`
- **Delivered:** Versioned Firestore documents (`cl_xxx_v1`, `cl_xxx_v2`).

### ✅ Ticket 8C: Production Director Transformation Engine
- **Status:** `COMPLETED`
- **Delivered:** Transforming `CloneBlueprint` -> `ProductionBlueprint` with Project Bible entity resolution.

### ✅ Ticket 8D: End-to-End Orchestration & Approval Gate
- **Status:** `COMPLETED`
- **Delivered:** Complete blueprint CRUD, manual approval state transitions, and background production execution.

### ✅ Ticket 8E: Canonical Generation Engine & Golden Path Migration
- **Status:** `COMPLETED`
- **Delivered:** Unifying single-scene Veo generation, ElevenLabs TTS, Gemini QualityReviewer, and LipSync across all workflows.

### ✅ Ticket 8E.2: Forensic Hardening & Live Production Acceptance
- **Status:** `COMPLETED`
- **Delivered:** CameraDirection enum normalization, adaptive retry engine with targeted Director's Notes, GenerationAttempt Firestore telemetry.

### ✅ Ticket 8F: Reference Conditioning & Visual Identity Merge
- **Status:** `COMPLETED`
- **Delivered:** Implementation of `VisualIdentityPack`, multi-angle character references, environment plates, and strict shot-aware reference URI binding in `ReferenceManager`.

### ✅ Ticket 8G: Security Remediation & Test Verification
- **Status:** `COMPLETED`
- **Delivered:** 100% cryptographic Firebase verification, strict CORS canonical origin allowlist, SSRF/Cloud Metadata filtering, and Firestore rule hardening. Verified with 138/138 backend tests passing.

---

## 3. Active Queue & Next Actionable Tickets

### 📌 Ticket 1: Implement Centralized ModelRoutingConfig & Complexity Router
- **Type:** Backend Architecture
- **Description:** Centralize all AI model routing logic in `backend/config.py`. Implement a complexity router that seamlessly transitions from Gemini 3.1 Flash to Anthropic Claude Sonnet 4.6 for highly complex scripts while maintaining Gemini 3.1 Flash-Lite for basic ingestion tasks.
- **Acceptance Criteria:**
  - Standardized `ModelRoutingConfig` class.
  - Cost-optimized routing function evaluating token limits and script complexity.

### 📌 Ticket 2: Real-Time Telemetry Streaming via Server-Sent Events (SSE)
- **Type:** Feature / UX
- **Description:** Replace client-side polling with Server-Sent Events (SSE) to stream real-time scene generation progress, QualityReviewer feedback, and Reference validation status to the UI.
- **Acceptance Criteria:**
  - Backend endpoint `GET /projects/{pid}/blueprints/{bid}/events` streaming live status updates.
  - Frontend Stage 6 production dashboard updates dynamically as each generation chunk completes.

### 📌 Ticket 3: Stripe Billing Integration & Credit Refill Webhook Handlers
- **Type:** Monetization
- **Description:** Integrate Stripe Checkout and webhook handlers (`checkout.session.completed`, `invoice.payment_succeeded`) to manage user subscription tiers and allocate credits securely in Firestore.
- **Acceptance Criteria:**
  - Stripe Checkout sessions for Starter, Creator, and Agency plans.
  - Secure webhook endpoint verifying Stripe signatures and updating user credits in `/users/{uid}`.

### 📌 Ticket 4: Cloud Tasks Asynchronous Worker Queue
- **Type:** DevOps / Infrastructure
- **Description:** Offload long-running Cloud Run background tasks (like multi-scene video generation and repurposer rendering) to Google Cloud Tasks to ensure durable execution, retry logic, and independent scaling.
- **Acceptance Criteria:**
  - Generation endpoints publish a payload to a Cloud Tasks queue.
  - Cloud Run worker endpoints ingest the payload and execute safely within timeout limits.
