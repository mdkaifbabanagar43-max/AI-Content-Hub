# MASTER ARCHITECTURE AUDIT — CLONEFRAME UNIVERSAL ENGINE

**Date:** 2026-08-23  
**Status:** Read-Only Audit (Freeze State)  
**Target:** Video Cloner & Trend Cloner Convergence  

---

## 1. Executive Summary & Forensic Comparison

The platform currently operates two parallel video creation/cloning pipelines:
1. **Legacy Trend Cloner (`/api/trend-cloner/*`):** Proven, viral-intelligence oriented pipeline that extracts concepts/hooks and generates short-form videos with Veo, ElevenLabs, and SyncLabs.
2. **Video Cloner (`/projects/{project_id}/...`):** Full 14-stage blueprint-driven pipeline that reverse-engineers source media into `SourceAnalysis`, creates `CloneBlueprint`, locks `VisualIdentityPack`, transforms via `ProductionDirector`, and orchestrates generation through Cloud Tasks and `CanonicalGenerationEngine`.

### Comparative Matrix

| Capability / Attribute | Trend Cloner (Legacy) | Video Cloner (Current) | Unified Target Architecture |
| :--- | :--- | :--- | :--- |
| **Ingestion** | URL download / file upload | GCS upload + URL downloader | Unified Secure Video Ingest (`core.video_downloader`) |
| **Source Understanding** | `TrendAnalyzer` (Gemini Vision) | `SourceAnalyzer` (Multi-stage Gemini Vision) | Universal Source DNA Extractor (9 independent DNA channels) |
| **Preservation Controls** | Hardcoded niche remix | Rigid all-or-nothing visual style | **User Preservation Profile (`CloneIntent`)** |
| **Character Handling** | Ad-hoc `character_refs` prefix | `VisualIdentityPack` + Project Bible | Explicit Policy: `PRESERVE`, `CREATE_NEW`, `MIXED` |
| **Environment Handling** | None (embedded in prompts) | Prompt-directed location context | Explicit Policy: `PRESERVE`, `CREATE_NEW`, `ADAPT` |
| **Narrative Control** | Topic Remix | Prompt injection + Originality gate | Explicit Policy: `NEW_STORY`, `STRUCTURE_INSPIRED`, `TREND_INSPIRED` |
| **Generation Engine** | In-router background worker | Cloud Tasks + `CanonicalGenerationEngine` | Headless, Provider-Agnostic `CanonicalGenerationEngine` |
| **Model Routing** | Partial routing | Centralized `ModelRoutingConfig` | AST-enforced, Category-based `ModelRoutingConfig` |
| **Billing & Credits** | Upfront credit deduction | Pre-flight reservation + atomic commit | Strictly Atomic Reservation & Commit Gate |

---

## 2. Forensic Audit by Subsystem

### A. Legacy Trend Cloner
* **What Worked:**
  - Fast, direct viral hook and concept extraction.
  - Natural comedic timing and viral pacing formulas.
  - Simple single-prompt or 3-scene beat structure.
* **What Broke / Needs Unification:**
  - Duplicate downloader code (`download_video_yt_dlp` wrapper in `trend_cloner.py` vs `core.video_downloader`).
  - Ad-hoc character saving (`core.character_refs` dict storage vs Firestore Project Bible).
  - Background task worker executes directly inside router process rather than standardized Cloud Tasks worker.

### B. Current Video Cloner
* **What Worked:**
  - Comprehensive reverse-engineering (`SourceAnalysis` with 10+ granular attributes).
  - Strict Pydantic models for `CloneBlueprint` and `ProductionBlueprint`.
  - Immutable blueprint versioning and single-flight job isolation.
  - Multi-angle character reference generation and visual identity locking.
  - Originality validation gate preventing verbatim story cloning.
* **What Broke / Needs Unification:**
  - Prompt construction previously passed full story context; now isolated, but lacks explicit user checkboxes for what to preserve (e.g. style vs characters vs environment).
  - Frontend sent field names (`target_topic`, `target_niche`) that differed from backend expectations (`topic`, `niche`), requiring alias validators.
  - Missing fine-grained character generation policies (e.g. creating brand new characters in the same art style).

### C. Shared Services
* **Downloader:** `core.video_downloader.py` provides SSRF protection, platform detection, and yt-dlp execution. Legacy Trend Cloner has an unnecessary wrapper.
* **Storage:** `core.storage_client.py` reliably handles GCS uploads, signed URLs, and bucket isolation.
* **Project Bible:** `core.services.bible_loader.py` securely scopes characters, styles, voices, and locations by user and project.

### D. Generation Engine
* `CanonicalGenerationEngine` is decoupled and operates purely on `ProductionBlueprint`.
* Provider calls (Veo, ElevenLabs, SyncLabs) are isolated with clear failure boundaries and non-silent fallbacks.

### E. Model Routing & Compatibility
* `ModelRoutingConfig` centralizes all model aliases.
* No hardcoded model string literals remain in active services.
* AST regression tests enforce model routing discipline.

### F. Security & Identity
* Firebase ID Token verification via `core.auth.get_current_user`.
* Cloud Tasks OIDC token validation via `core.auth_oidc.verify_cloud_run_oidc_token`.
* SSRF validation blocks private IP ranges, loopback, and cloud metadata (`169.254.169.254`).

---

## 3. Duplication and Technical Debt Inventory

1. **Downloader Logic:** `backend/routers/trend_cloner.py:72` duplicates `core.video_downloader.py`.
2. **Character Storage:** Trend Cloner uses file-based/legacy `core.character_refs` instead of Firestore-backed `VisualIdentityPack` / Project Bibles.
3. **Execution Workers:** Trend Cloner has an internal `run_trend_cloner_job` function with its own MoviePy/FFmpeg assembly loop, while Video Cloner uses `CanonicalGenerationEngine` and Cloud Tasks orchestration.
4. **Preservation Coupling:** Video Cloner previously coupled character identity and art style into one visual identity pack without letting the user generate *new* characters inside the *cloned* art style.

---

## 4. Preservation & Migration Imperatives

- **Rule 1:** The legacy Trend Cloner routes (`/api/trend-cloner/*`) must remain 100% operational during refactoring.
- **Rule 2:** The unified `UniversalCreativeDirector` will accept `CloneIntent` and produce a standard `ProductionBlueprint` for both Trend Cloner and Video Cloner workflows.
- **Rule 3:** The generation backend (`CanonicalGenerationEngine`) will remain untouched and provider-agnostic.
