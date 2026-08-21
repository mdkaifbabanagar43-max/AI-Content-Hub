# AI Content Hub / ShortcutAI — API Documentation

This document outlines the complete REST API endpoints currently implemented in the FastAPI backend (`backend/main.py` and `backend/routers/`).

> [!IMPORTANT]
> All protected endpoints require a `Bearer <token>` HTTP Authorization header containing a valid Firebase Authentication ID Token, which is cryptographically verified by the `get_current_user` dependency in `core/auth.py`.

---

## Architecture Overview

The backend uses a modular FastAPI router architecture:
- **System (`/`)**: Health checks, user profile capabilities, system config, job status polling.
- **Video Cloner (`/projects`)**: Flagship structural video cloning, source analysis, clone blueprints, visual identity packs, creative transformation, approval gate, and asynchronous canonical production generation.
- **AI Production Director (`/projects`)**: Script-to-blueprint generation, blueprint versioning, and state transition management.
- **Trend Cloner (`/api/trend-cloner`)**: Legacy viral video analysis and multi-scene generation.
- **Viral Repurposer (`/`)**: Direct GCS signed URL generation, Gemini video analysis, face tracking, and 9:16 vertical video repurposing.
- **Idea Studio (`/`)**: AI idea brainstorming, script generation, audio synthesis, and final rendering.
- **Global Dubber (`/`)**: Multilingual translation, voiceover generation, voice cloning, and audio/lip sync.
- **Projects (`/`)**: User project persistence, retrieval, and deletion.
- **URL Import (`/`)**: Video downloading via `yt-dlp` from social media platforms.

> [!NOTE]
> AI-heavy endpoints (generation, analysis, synthesis) enforce strict sliding-window rate limiting. If limits are exceeded, the API returns `429 Too Many Requests` with a `Retry-After` header.

---

## 1. System & Common Endpoints (`backend/routers/system.py` & `backend/main.py`)

### `GET /`
System health and readiness check.
- **Auth:** Not required.
- **Response (200 OK):**
  ```json
  {
    "status": "online",
    "service": "AI Content Hub API",
    "version": "2.0.0"
  }
  ```

### `GET /api/me`
Fetches authenticated user profile, plan tier, remaining credits balance, and backend feature access capabilities.
- **Auth:** Required (`Bearer <token>`).
- **Response (200 OK):**
  ```json
  {
    "user_id": "user_abc123",
    "email": "creator@example.com",
    "plan": "creator",
    "credits": 1850,
    "capabilities": {
      "idea_studio": true,
      "script_generation": true,
      "repurposer_basic": true,
      "repurposer_smart_crop": true,
      "dubbing": true,
      "premium_voices": true,
      "watermark_free": true,
      "max_video_minutes": 30,
      "max_resolution": "1080p",
      "priority_rendering": true,
      "bulk_upload": false,
      "concurrent_jobs": 2
    }
  }
  ```

### `GET /system-config`
Returns system pricing tiers, credit costs, and feature matrices.
- **Auth:** Not required.
- **Response (200 OK):**
  ```json
  {
    "pricing_tiers": { ... },
    "credit_costs": {
      "idea_studio_script": 5,
      "repurposer_per_minute": 10,
      "dubbing_per_minute": 20,
      "voice_clone_training": 500,
      "trend_cloner_base": 10,
      "trend_cloner_veo_per_scene": 25,
      "visual_identity_pack": 15
    },
    "plan_features": { ... }
  }
  ```

### `GET /api/jobs/{job_id}`
Polls the live execution status of an asynchronous background job stored in Firestore under `/users/{user_id}/jobs/{job_id}`.
- **Auth:** Required (`Bearer <token>`).
- **Response (200 OK):**
  ```json
  {
    "job_id": "job_9f8e7d",
    "status": "completed",
    "progress": "Generation complete",
    "result_url": "https://storage.googleapis.com/shortcutai-user-uploads-2026/...",
    "created_at": "2026-08-15T18:22:04Z"
  }
  ```

---

## 2. Video Cloner (`backend/routers/video_cloner.py` — Prefix: `/projects`)

### `POST /projects/{project_id}/source-videos`
Ingests a source video file via direct upload to GCS.
- **Auth:** Required (`Bearer <token>`).
- **Request:** `multipart/form-data` with `file: UploadFile`.
- **Response (200 OK):** SourceVideoRecord JSON.

### `POST /projects/{project_id}/source-videos/from-url`
Ingests a source video directly from a social media URL via `yt-dlp`.
- **Auth:** Required (`Bearer <token>`).
- **Request Body (JSON):** `{"url": "https://www.tiktok.com/..."}`
- **Response (200 OK):** SourceVideoRecord JSON.

### `POST /projects/{project_id}/source-videos/{source_video_id}/analyze`
Triggers Gemini multimodal analysis on the source video to extract structural DNA, pacing, dialogue, and authoritative visual styling.
- **Auth:** Required (`Bearer <token>`).
- **Response (200 OK):** `SourceAnalysis` model JSON.

### `POST /projects/{project_id}/clone-blueprints`
Generates a structured `CloneBlueprint` from a completed `SourceAnalysis`.
- **Auth:** Required (`Bearer <token>`).
- **Request Body (JSON):** `{"analysis_id": "sa_1a2b3c4d"}`
- **Response (200 OK):** `CloneBlueprint` model JSON (versioned document `cl_xxx_v1`).

### `POST /projects/{project_id}/visual-identity-pack`
Generates and locks the Visual Identity Pack for a project (multi-angle character turnarounds, environment maps) via Gemini 3.1 Flash Image.
- **Auth:** Required (`Bearer <token>`).
- **Request Body (JSON):** `{"characters": ["CHAR_001"], "environments": ["ENV_001"]}`
- **Response (200 OK):** `VisualIdentityPack` JSON.

### `GET /projects/{project_id}/visual-identity-pack`
Retrieves the active Visual Identity Pack for a project.
- **Auth:** Required (`Bearer <token>`).
- **Response (200 OK):** `VisualIdentityPack` JSON.

### `POST /projects/{project_id}/clone-blueprints/{clone_blueprint_id}/transform`
Transforms a descriptive `CloneBlueprint` into a prescriptive `ProductionBlueprint` using user transformation inputs.
- **Auth:** Required (`Bearer <token>`).
- **Request Body (JSON):**
  ```json
  {
    "new_topic": "Padlock couple forgets their house keys",
    "character_id": "CHAR_001",
    "visual_style_id": "STYLE_001",
    "voice_id": "VOICE_001",
    "target_duration_seconds": 19.12,
    "language": "en",
    "use_lip_sync": false
  }
  ```
- **Response (200 OK):** `ProductionBlueprint` model JSON with status `"READY_FOR_APPROVAL"`.

### `POST /projects/{project_id}/production-blueprints/{production_blueprint_id}/approve`
**Manual Approval Gate:** Transitions blueprint status from `READY_FOR_APPROVAL` -> `APPROVED`.
- **Auth:** Required (`Bearer <token>`).
- **Response (200 OK):** `{"status": "APPROVED"}`

### `POST /projects/{project_id}/production-blueprints/{production_blueprint_id}/generate`
Queues the asynchronous end-to-end production generation loop executing the Canonical Generation Engine.
- **Auth:** Required (`Bearer <token>`).
- **Response (200 OK):** `{"message": "Job queued successfully", "blueprint_id": "bp_abc123"}`

---

## 3. AI Production Director (`backend/routers/director.py` — Prefix: `/projects`)

### `POST /projects/{project_id}/blueprint`
Generates a new `ProductionBlueprint` from a raw idea string and target duration using Project Bibles.
- **Auth:** Required (`Bearer <token>`).
- **Request Body (JSON):** `{"user_idea": "Two animated padlocks solving a mystery", "target_duration_seconds": 30.0}`
- **Response (200 OK):** `ProductionBlueprint` model JSON.

### `PUT /projects/{project_id}/blueprints/{blueprint_id}/status`
Updates blueprint status with strict state machine validation.
- **Auth:** Required (`Bearer <token>`).
- **Response (200 OK):** Status update confirmation.

---

## 4. Viral Repurposer (`backend/routers/repurposer.py`)

### `POST /get-upload-url` (and `GET /get-upload-url`)
Issues a secure GCS V4 Signed PUT URL via IAM Credentials API for direct client-to-bucket upload.
- **Auth:** Required (`Bearer <token>`).
- **Response (200 OK):** `{"upload_url": "https://storage.googleapis.com/...", "gcs_path": "uploads/video_uuid.mp4"}`

### `POST /analyze-file-gcs`
Runs multimodal moment analysis and virality scoring on a GCS-hosted video.
- **Auth:** Required (`Bearer <token>`).
- **Response (200 OK):** List of candidate viral clips.

### `POST /repurpose-video`
Triggers an asynchronous background job to crop, face-track, and burn captions.
- **Auth:** Required (`Bearer <token>`).
- **Response (200 OK):** `{"status": "processing", "job_id": "job_rep_123"}`

---

## 5. Idea Studio (`backend/routers/idea_studio.py`)

### `POST /generate-ideas`
Generates high-CTR video concepts based on a topic prompt.
- **Auth:** Required (`Bearer <token>`).
- **Response (200 OK):** List of structured idea concepts.

### `POST /produce-video-assets`
Generates an audio voiceover via TTS and a visual plan containing stock footage search terms.
- **Auth:** Required (`Bearer <token>`).
- **Response (200 OK):** Script, base64 audio snippet, and search query keywords.

### `POST /render-final`
Assembles the stock video clips, audio voiceover, and captions into a final rendered video.
- **Auth:** Required (`Bearer <token>`).
- **Response (200 OK):** `{"video_url": "https://storage.googleapis.com/..."}`

---

## 6. Global Dubber (`backend/routers/dubbing.py`)

### `POST /dub-video`
Translates and dubs a video into a target language.
- **Auth:** Required (`Bearer <token>`).
- **Response (200 OK):** `{"status": "success", "video_url": "https://...", "audio_url": "https://..."}`

---

## 7. Projects & Media (`backend/routers/projects.py`)

### `GET /my-projects` (and `GET /api/projects`)
Retrieves all completed project videos and generation records for the authenticated user.
- **Auth:** Required (`Bearer <token>`).
- **Response (200 OK):** `{"projects": [...]}`

### `DELETE /api/projects/{project_id}`
Deletes a project and its associated metadata.
- **Auth:** Required (`Bearer <token>`).
- **Response (200 OK):** `{"status": "success", "deleted_project_id": "proj_123"}`
