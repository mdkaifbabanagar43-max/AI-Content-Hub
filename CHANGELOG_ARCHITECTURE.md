# ShortcutAI Architecture Evolution & Changelog

---

## 1. Phase 1–7: AI Content Hub & Trend Cloner Foundation

- **Initial SaaS Foundation:** Established full-stack architecture with Next.js frontend, Python FastAPI backend, Firebase Authentication, Google Cloud Firestore, and Google Cloud Storage (GCS) hosted on Google Cloud Run.
- **Viral Repurposer:** Ingested long-form videos via GCS signed URLs or `yt-dlp` social media downloads. Applied OpenCV Haar Cascades for facial detection, rendering dynamic 9:16 vertical layouts (`podcast_stack`, `smart_solo`, `content_fit`), and burned word-level animated subtitles via Whisper transcription.
- **Idea Studio:** Topic-to-video studio generating AI titles, hooks, multi-part scripts, Google Cloud TTS audio, and stock media compilation.
- **Global Dubber:** Multilingual speech translation and neural voiceover synthesis.
- **Early Trend Cloner Prototype:** Introduced generative video workflows using Google Vertex AI (Veo API) and ElevenLabs multi-voice audio.

---

## 2. Phase 8A: Source Analysis Normalization

- **Decoupled Ingestion:** Separated source video ingestion from immediate video generation.
- **Data Models:** Created `core/models/clone_blueprint.py` and `services/source_analyzer.py`.
- **Multimodal Video DNA Extraction:** Upgraded Gemini analysis to extract structured `SourceAnalysis` containing visual art style, character design, audio profiles, hook mechanisms, narrative conflicts, and logical scene beats.

---

## 3. Phase 8B: Clone Blueprint Architecture & Storage

- **Descriptive Source DNA:** Formalized `CloneBlueprint` (`cl_xxx_v1`) as the immutable structural formula of the source video without encoding user-specific characters or topics.
- **Versioned Persistence:** Built `core/repositories/clone_blueprint_repo.py` supporting multi-revision Firestore documents (`cl_xxx_v1`, `cl_xxx_v2`) under `/users/{user_id}/projects/{project_id}/clone_blueprints/`.

---

## 4. Phase 8C: Production Blueprint & Director Transformation Engine

- **Prescriptive Blueprint Model:** Introduced `ProductionBlueprint` (`core/models/blueprint.py`) specifying model-ready scene prompts, camera angles, emotions, lighting, and dialogue lines.
- **Creative Transformation Engine:** Created `core/services/production_director.py` transforming `CloneBlueprint` $\rightarrow$ `ProductionBlueprint` by binding user topics and Project Bibles (Characters, Voices, Styles, Locations, Props).
- **State Machine Enforcement:** Established strict blueprint lifecycle states (`DRAFT` $\rightarrow$ `READY_FOR_APPROVAL` $\rightarrow$ `APPROVED` $\rightarrow$ `IN_PRODUCTION` $\rightarrow$ `COMPLETED`).

---

## 5. Phase 8D: End-to-End Orchestration & Router Integration

- **Modular Routing:** Implemented `routers/video_cloner.py` and `routers/director.py` under the `/projects` prefix.
- **End-to-End Execution Loop:** Implemented `run_production_job` orchestrating scene prompt compilation, reference generation, model dispatch, and final concatenation.
- **Manual Approval Gate:** Enforced mandatory user approval (`READY_FOR_APPROVAL` $\rightarrow$ `APPROVED`) before executing paid compute.

---

## 6. Phase 8D Corrective Patch: Audio Duration Authority & Timeline Normalization

- **Elimination of 16s Default Inflation:** Fixed an architectural bug where single-chunk scenes were defaulting to 16 seconds.
- **Audio-First Duration Authority:** Re-architected the generation loop to synthesize ElevenLabs audio first and dynamically calculate target Veo duration:
  $$\text{target\_veo\_duration} = \max(5, \lceil\text{audio\_duration}\rceil)$$
- **Physical Timeline Normalization:** Upgraded `core/services/timeline_builder.py` with explicit FFmpeg subclip trimming (`atrim`/`trim` + `setpts`), eliminating duration drift between requested scene durations and raw video outputs.

---

## 7. Phase 8E: Golden Path Migration & Canonical Generation Engine

- **Elimination of Duplicate Generation Logic:** Consolidated disparate generation code into a single, unified `CanonicalGenerationEngine` (`core/services/canonical_generation_engine.py`).
- **Trend Cloner as Golden Path:** Reused the proven, hardened single-scene generation loop from Trend Cloner as the core engine powering the Video Cloner orchestration.
- **Standardized Scene Lifecycle:** Implemented `CanonicalGenerationRequest`, Gemini QualityReviewer frame evaluation, and attempt recording.

---

## 8. Phase 8E.1: Production Fidelity & Timeline Corrections

- **Timeline Verification:** Hardened multi-scene timeline reconciliation and verified physical file durations on local disk before calling FFmpeg concat.
- **Lip-Sync Pipeline:** Verified SyncLabs lip-sync integration when dialogue is present.

---

## 9. Phase 8E.2: Forensic Hardening & Live Production Acceptance

- **Camera Direction Enum Safety:** Implemented `normalize_enum_val()` in `core/services/prompt_compiler.py`, safely resolving Pydantic `CameraDirection` enum objects and eliminating `AttributeError: 'CameraDirection' object has no attribute 'lower'`.
- **ReferenceManager Robustness:** Eliminated unsafe `.lower()` calls and added `GenerationContext` reference cache management.
- **Visual Style Profile Propagation:** Added `visual_style_profile`, `authoritative_art_style`, and `authoritative_character_design` across `CloneBlueprint`, `ProductionBlueprint`, and `ProductionDirector`.
- **Elimination of Silent Prompt Fallback:** Removed silent fallback to `scene.action` in `routers/video_cloner.py`, ensuring prompt compiler errors fail fast and visibly.
- **Adaptive Retry Engine:** QualityReviewer rejections dynamically construct targeted `[DIRECTOR'S NOTE: ...]` prompt modifiers detailing detected flaws (e.g. missing padlock heads, UI text distortions) with a strictly enforced 1-retry cap.
- **Forensic Telemetry Logging:** Persisted every generation attempt, prompt, reference URI, score, and rejection reason in Firestore under `users/{uid}/projects/{pid}/generation_attempts/{attempt_id}`.
- **Live Acceptance Test on Cloud Run (`ai-video-backend-00116-n7n`):**
  - Executed full 5-scene production test on `lock.mp4`.
  - **Source Duration:** `19.120s` $\rightarrow$ **Output Master Video:** `19.200s` (19.160s physical timeline across 5 clips: `2.600s`, `2.330s`, `7.500s`, `2.700s`, `4.030s`).
  - **Scene 3 Prompt Integrity:** Staging, 35mm lens, dolly camera, bright daylight, and front porch environment accepted on Attempt 1 (Score: `7.75`).
  - **Scene 5 Adaptive Retry:** Attempt 1 rejected (Score: `6.50`) $\rightarrow$ Targeted Director's Note applied $\rightarrow$ Attempt 2 accepted (Score: `7.25`).
  - Master video delivered: `https://storage.googleapis.com/shortcutai-user-uploads-2026/final_videos/proj_lock_acceptance_8e2/10bfa160-62d5-4771-8a63-11f6c605ec0b.mp4`.

---

## 10. Current Architecture: The Unified Generation Layer

```
                 SHORTCUTAI VIDEO GENERATION
                              |
                              v
                   Unified Generation Layer
                              |
             +----------------+----------------+
             |                                 |
       Trend Cloner                      Video Cloner
     UX / Entry Point                  UX / Entry Point
             |                                 |
             +----------------+----------------+
                              |
                              v
                 Canonical Generation Engine
                              |
          +-------------------+-------------------+
          |                   |                   |
     Google Gemini       Google Veo 3.1       ElevenLabs
   analysis / director   video generation       audio
                              |
                       Quality Reviewer
                              |
                       TimelineBuilder
                              |
                           Lip Sync
                              |
                        Final Assembly
                              |
                              v
                    Google Cloud Storage (GCS)
                              |
                              v
                      FinalVideoRecord
```

---

## 11. Known Limitations & Boundaries

1. **Frontend Tab Coexistence:** `TrendCloner.tsx` (tab `'trend-cloner'`) and `VideoCloner.tsx` (tab `'video-cloner'`) currently coexist in the frontend UI pending planned consolidation into a single unified Video Cloner experience.
2. **Generative Consistency:** Generative AI video (Google Veo) is probabilistic. The system is designed to **maximize visual consistency** using authoritative prompt prefixes, reference assets, frame chaining, and QualityReviewer guardrails, but cannot guarantee mathematically identical pixel reproduction.
3. **Task Queue Architecture:** Asynchronous generation jobs currently run in-process via FastAPI `BackgroundTasks` on Cloud Run. High-volume enterprise concurrency will benefit from a dedicated distributed queue (e.g. Google Cloud Tasks or Celery).
4. **Third-Party Provider Latency:** End-to-end multi-scene generation time (typically 5–10 minutes for 5 scenes) is bounded by Google Veo queue processing times and SyncLabs lip-sync rendering.
