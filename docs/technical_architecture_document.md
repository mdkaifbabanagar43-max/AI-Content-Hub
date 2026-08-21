# Technical Architecture Document
## ShortcutAI — AI Content Hub

---

## 1. High-Level Target Architecture

ShortcutAI is engineered as a decoupled, cloud-native SaaS comprising a Next.js frontend, a Python FastAPI backend hosted on Google Cloud Run, Firebase Auth & Firestore data layers, and Google Cloud Storage (GCS) asset management.

### 1.1 Unified Video Generation Architecture

ShortcutAI operates a **single, unified Video Cloner pipeline**. The 6-stage unified workflow generates a `VisualIdentityPack` before compiling prescriptive blueprints to drive the Canonical Generation Engine:

```mermaid
graph TD
    subgraph UX [User-Facing Entry Points]
        VC[Unified Video Cloner UI]
    end

    VC --> UGL[Unified Generation Layer]
    UGL --> VIP[Visual Identity Pack Generator]
    VIP --> CGE[Canonical Generation Engine]

    subgraph CGE_FLOW [Canonical Generation Engine]
        direction TB
        CGE --> Audio[1. ElevenLabs TTS - Audio First]
        Audio --> DurCalc[2. Target Veo Duration: max(5, ceil(t))]
        DurCalc --> PC[3. PromptCompiler - Animated Token Sanitization]
        PC --> RM[4. ReferenceManager - Shot-Aware Selection]
        RM --> Veo[5. Google Veo 3.1 I2V Generation]
        Veo --> QR{6. Gemini QualityReviewer}
        QR -->|Score < 7.0 & Attempt 1| Retry[7. Adaptive Retry with Director's Note]
        Retry --> Veo
        QR -->|Score >= 7.0 or Attempt 2| TB[8. TimelineBuilder - Subclip & Normalization]
        
        TB --> DualAudio{9. Dual-Mode Audio Pipeline}
        DualAudio -->|Mode A| MuxA[10A. Canonical Audio Muxing]
        DualAudio -->|Mode B| LipB[10B. SyncLabs Lip-Sync]
        
        MuxA --> Concat[11. FFmpeg Timeline Concatenation]
        LipB --> Concat
    end

    Concat --> GCS[(Google Cloud Storage)]
    GCS --> FVR[FinalVideoRecord & Telemetry in Firestore]
```

---

## 2. End-to-End Golden Path Lifecycle (24 Steps)

The complete end-to-end video cloning and generation lifecycle executes the following sequence:

```
[SOURCE VIDEO INGESTION & DNA]
  1. Ingest source video via direct GCS upload or yt-dlp URL import.
  2. Perform multimodal visual analysis with Gemini 3.1 Flash.
  3. Extract authoritative visual style (art_style) and character design (character_design).
  4. Decompose video into logical narrative scenes (pacing, camera, emotion, action).
  5. Build descriptive CloneBlueprint (cl_xxx_v1) capturing the source video DNA.

[VISUAL IDENTITY & CREATIVE TRANSFORMATION]
  6. Ingest user transformation inputs (topic, character, visual style, voice, language).
  7. Generate VisualIdentityPack (multi-angle locked character turnarounds via Gemini 3.1 Flash Image) and persist to Firestore.
  8. ProductionDirector resolves Project Bibles against the new VisualIdentityPack.
  9. Compile prescriptive ProductionBlueprint (bp_xxx_v1) with Audio Mode selection and status READY_FOR_APPROVAL.
  10. Enforce Manual Approval Gate: Transition blueprint status to APPROVED.

[CANONICAL SCENE GENERATION LOOP]
  11. Compile scene prompt via PromptCompiler: [Authoritative Style] + [Scene Dynamics] + [Cinematography]. Automatically strips contradictory photorealistic tokens on animated art styles.
  12. Execute Shot-Aware Reference Selection in ReferenceManager:
      - CLOSE_UP -> closeup_ref_uri
      - WIDE -> full_body_ref_uri
      - MEDIUM -> three_quarter_left_uri
  13. If dialogue is present: Generate canonical voiceover via ElevenLabs and measure exact duration.
  14. Calculate target Veo generation duration: target_veo_duration = max(5, ceil(audio_duration)).
  15. Submit raw generation request to Google Veo.
  16. Extract 4 representative frames (10%, 40%, 70%, 95%) and evaluate with Gemini QualityReviewer.
  17. If rejected on Attempt 1: Construct targeted adaptive [DIRECTOR'S NOTE: ...] modifier and re-generate.
  18. Persist GenerationAttempt telemetry (including reference_telemetry) in Firestore.

[TIMELINE RECONCILIATION & ASSEMBLY]
  19. Truncate/normalize accepted video chunk to exact blueprint duration via TimelineBuilder.
  20. Dual-Mode Audio Pipeline Check:
      - Mode A: Replace raw Veo audio track with clean canonical ElevenLabs audio directly (Mux).
      - Mode B: Apply SyncLabs lip-sync alignment.
  21. Validate timing across all scene clips and execute timeline normalization.
  22. Stitch normalized scene clips into master MP4 using FFmpeg (h264/aac, 30fps).
  23. Upload final master MP4 to GCS and persist FinalVideoRecord in Firestore.
  24. Clean up ephemeral temporary storage in `/tmp`.
```

---

## 3. Core Engine Components & Services

| Service | File Path | Primary Responsibility |
| :--- | :--- | :--- |
| **`CanonicalGenerationEngine`** | `core/services/canonical_generation_engine.py` | Single-scene generation loop, audio-first duration targeting, adaptive retry handling, and attempt recording. |
| **`PromptCompiler`** | `core/services/prompt_compiler.py` | Prompt sanitization, contradictory photorealism removal, CameraDirection enum normalization, and authoritative style prefixing. |
| **`ReferenceManager`** | `core/services/reference_manager.py` | Shot-Aware Character reference image resolution using `VisualIdentityPack` uris, and reference cache management. |
| **`QualityReviewer`** | `core/services/quality_reviewer.py` | Multi-frame inspection using Gemini 3.1 Flash across character consistency, scene adherence, visual quality, and continuity. |
| **`TimelineBuilder`** | `core/services/timeline_builder.py` | Subclip trimming (`atrim`/`trim` + `setpts`), freeze-frame padding, timing reconciliation, and Dual-Mode Audio selection. |
| **`ProductionDirector`** | `core/services/production_director.py` | Blueprint synthesis, `CloneBlueprint` -> `ProductionBlueprint` transformation, and Project Bible / VisualIdentityPack binding. |

---

## 4. AI Models & Provider Architecture (2026 Baseline)

ShortcutAI utilizes a centralized Cost-Optimized Model Routing strategy:

| Provider | Configured Model ID | Role in System |
| :--- | :--- | :--- |
| **Google Vertex AI** | `gemini-3.1-flash-lite` | Video ingestion, metadata extraction, light NLP parsing. |
| **Google Vertex AI** | `gemini-3.1-flash` | Multimodal video analysis, QualityReviewer frame evaluation. |
| **Anthropic (AWS/GCP)**| `us.anthropic.claude-sonnet-4-6` | Complex blueprint script reasoning (Escalation tier). |
| **Google Vertex AI** | `gemini-3.1-flash-image` | High-fidelity character turnaround / VisualIdentityPack generation. |
| **Google Vertex AI** | `veo-3.1-fast-generate-001` | Default video chunk generation (720x1280, 9:16 vertical). |
| **Google Vertex AI** | `veo-3.1-generate-001` | Premium high-fidelity video generation. |
| **ElevenLabs** | `eleven_flash_v2_5` | High-speed, cost-effective TTS voiceover synthesis. |
| **ElevenLabs** | `eleven_v3` | Premium conversational voiceover synthesis. |
| **SyncLabs** | SyncLabs API v2 | Video lip synchronization (Mode B). |

---

## 5. Visual Identity & Consistency Strategy

ShortcutAI guarantees visual consistency through the **`VisualIdentityPack`**:
1. **Pre-Generation Locking:** Before video generation begins, Gemini 3.1 Flash Image generates a complete `VisualIdentityPack` providing multi-angle references for all characters.
2. **Shot-Aware Reference Selection:** The `ReferenceManager` dynamically selects the exact `VisualIdentityPack` URI based on the scene's camera shot type (e.g. `CLOSE_UP` -> `closeup_ref_uri`, `WIDE` -> `full_body_ref_uri`).
3. **Contradictory Token Elimination:** The `PromptCompiler` actively sanitizes Veo prompts to strip contradictory realism tokens ("photorealistic", "live action") when animated styles are detected.
4. **Authoritative Style Prefix:** Every scene prompt is prefixed with the source video's extracted `art_style` and `character_design`.

---

## 6. Multi-Scene 30–60 Second Video Support

ShortcutAI architecturally supports videos longer than a single 5–8s Veo generation chunk:
- **Decomposition:** Long videos are broken down into logical narrative scenes (2–8 scenes).
- **Per-Scene Targeting:** Each scene requests only the duration it needs (`max(5, ceil(t))`).
- **Physical Normalization:** TimelineBuilder trims accepted raw clips to their exact sub-second blueprint duration.
- **Concatenation:** FFmpeg stitches the normalized clips into a continuous master timeline.

---

## 7. GCP Cloud Run Production Environment

- **GCP Project:** `shortcutai-backend`
- **Region:** `us-central1`
- **Container Service:** `ai-video-backend`
- **Authentication:** Application Default Credentials (ADC) via Cloud Run Service Account.
- **GCS Signed URLs:** V4 Signed URLs generated using `google.auth.iam.Signer` via the IAM Credentials API.
- **Memory & Storage Management:** Container uses local `/tmp` (tmpfs) for ephemeral video processing with strict post-job cleanup routines to prevent memory leaks and OOM errors.
