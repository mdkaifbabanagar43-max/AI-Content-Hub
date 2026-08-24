# IMPLEMENTATION PLAN — CLONEFRAME UNIVERSAL ENGINE UPGRADE

**Milestone Timeline:** M1 through M12  
**Constraint:** Strict freeze until user review & approval. Zero production deployment or paid generation during planning.  

---

## 1. Milestones Overview

```
[M1: Audit & Schemas] (Completed)
         │
         ▼
[M2: Canonical Schemas (CloneIntent, PreservationProfile)]
         │
         ▼
[M3: Decoupled Source DNA Extraction (9 Channels)]
         │
         ▼
[M4: UniversalCreativeDirector Boundary]
         │
         ▼
[M5: Explicit Character & Environment Creation Engine]
         │
         ▼
[M6: Frontend Universal Preservation UI (Checkboxes + Presets)]
         │
         ▼
[M7: Multi-Dimensional Originality & Compliance Validator]
         │
         ▼
[M8: Trend Cloner Adapter (Legacy Route Bridge)]
         │
         ▼
[M9: Golden Test Suite (Tests A through H)]
         │
         ▼
[M10: Cloud Run Canary Deployment (--no-traffic)]
         │
         ▼
[M11: Controlled Zero-Credit Canary Validation]
         │
         ▼
[M12: Production Traffic Promotion & Final Sign-Off]
```

---

## 2. Component Modification Plan

### Backend Layer
1. **`backend/core/models/clone_intent.py` [NEW]:** Defines `CloneIntent`, `PreservationProfile`, `CharacterMode`, `EnvironmentMode`, `StoryMode`.
2. **`backend/core/models/source_dna.py` [NEW]:** Defines independent 9-channel DNA models (`VisualStyleDNA`, `CharacterDNA`, `EnvironmentDNA`, `CameraDNA`, `PacingDNA`, `EditingDNA`, `AudioDNA`, `NarrativeStructureDNA`, `TrendDNA`).
3. **`backend/services/source_analyzer.py` [MODIFY]:** Refactor `run_source_analysis` to populate independent DNA models cleanly.
4. **`backend/core/services/universal_creative_director.py` [NEW]:** Single canonical transformation boundary implementing dynamic `TransformationContext` prompt assembly and multi-dimensional validation.
5. **`backend/core/services/originality_validator.py` [MODIFY]:** Add preservation compliance checks (assert no source characters when `preserve_characters=False`).
6. **`backend/routers/trend_cloner.py` [MODIFY]:** Delegate legacy `/api/trend-cloner/*` routes to `UniversalCreativeDirector` using `story_mode=TREND_INSPIRED`.
7. **`backend/routers/video_cloner.py` [MODIFY]:** Update `/projects/{project_id}/.../transform` endpoint to accept `CloneIntent`.

### Frontend Layer
1. **`frontend/components/VideoCloner.tsx` [MODIFY]:**
   - Implement "What Should We Preserve?" interactive checkbox panel.
   - Add 5 preservation presets (*Style Clone, Character Clone, Style + Characters, Full Visual Clone, Trend Inspired*).
   - Update creative intent form with explicit topic/story fields.
   - Display dynamic "Clone Recipe" preview prior to generation approval.

---

## 3. Verification & Regression Plan

1. **Automated Unit Tests:**
   - `pytest tests/test_originality_validator.py -v`
   - `pytest tests/test_production_director.py -v`
   - `pytest tests/test_model_routing.py -v`
   - `pytest tests/test_security_audit.py -v`
   - `pytest tests/test_trend_cloner_regression.py -v`
   - `pytest tests/ -q` (All 186+ tests must pass).
2. **Golden Regression Matrix:**
   - Run Tests A through H in `test_universal_clone_golden.py` using canonical fixture `videos/WhatsApp Video 2026-08-17 at 11.36.14 PM.mp4`.
3. **Frontend Validation:**
   - `npx tsc --noEmit` (0 type errors).
   - `npm run build` (Clean production bundle build).
4. **Canary Validation Gate:**
   - Deploy revision to Cloud Run with `--no-traffic`.
   - Run end-to-end transformation test (0 paid generation, 0 Cloud Tasks).
   - Verify originality score < 0.40.
