# Product Requirements Document (PRD)
## ShortcutAI — AI Content Hub

---

## 1. Executive Summary & Product Vision

### 1.1 Product Description
**ShortcutAI** (AI Content Hub) is a comprehensive, cloud-native AI video production platform. It enables creators, social media agencies, educators, and businesses to generate high-retention vertical short-form videos (TikTok, YouTube Shorts, Instagram Reels) using generative video, automated repurposing, and structural cloning.

### 1.2 Core Product Pillars
1. **Flagship Video Cloner (Unified Engine):** A unified 6-stage creative workflow providing AI-powered video cloning and transformation that preserves a source video's visual language, character identity, narrative pacing, and production structure while allowing controlled story and dialogue transformation.
2. **Viral Repurposer (Long-to-Shorts):** Converts long-form YouTube videos, podcasts, and webinars into high-engagement vertical shorts with automatic facial tracking, split-screen layouts, and animated subtitles.
3. **Idea Studio (Idea-to-Video):** Transforms raw topic prompts into complete viral video concepts, structured multi-scene scripts, synthesized voiceovers, and rendered stock media.
4. **Global AI Dubber & Voice Lab:** Dubs video speech into 30+ languages with neural audio matching and AI lip synchronization.

---

## 2. Structural Video Cloning Principles & Fidelity Expectations

### 2.1 Structural Cloning vs. Story Transformation

```
┌────────────────────────────────────────────────────────┐
│                   STRUCTURAL CLONING                   │
├────────────────────────────┬───────────────────────────┤
│ WHAT WE CLONE (Structure)  │ WHAT WE TRANSFORM (New)   │
├────────────────────────────┼───────────────────────────┤
│ • Hook formula & timing    │ • Original storyline      │
│ • Narrative beat rhythm    │ • Character identities    │
│ • Camera motion & shot arc │ • Face, skin tone, hair   │
│ • Dialogue cadence/pacing  │ • Verbatim dialogue text  │
│ • Emotional intensity      │ • Background voice audio  │
│ • Call-to-action (CTA)     │ • Branded visuals & logos │
└────────────────────────────┴───────────────────────────┘
```

### 2.2 Visual Identity & Consistency Expectations
ShortcutAI is **designed to maximize visual consistency** across scenes, environments, wardrobe, camera language, and pacing.

> [!IMPORTANT]
> Generative video models (Google Veo) operate probabilistically. While our prompt architecture, character reference conditioning (`VisualIdentityPack`), and QualityReviewer guardrails maintain strong stylistic and character coherence, the system does not guarantee mathematically identical pixel reproduction between cuts.

---

## 3. Core Feature Requirements

### 3.1 Flagship Video Cloner: 6-Stage Creative Workflow
The legacy Trend Cloner and Video Cloner have been consolidated into a single flagship product with a 6-stage workflow:
1. **Source Ingestion:** File Upload or Social Media URL import via `yt-dlp`.
2. **Video DNA & Visual Treatment:** Gemini analysis extracts hook formula, pacing, art style, lighting, camera language, and mood.
3. **Visual Identity Pack:** Generates locked, multi-angle reference sheets once per character (front, three-quarter, closeup, full body) and persists them in Firestore to guarantee shot-aware reference consistency.
4. **Creative Transformation:** Applies story prompts, target language, and selects Audio Mode (Mode A vs. Mode B).
5. **Storyboard & Shot Planning:** Scene-by-scene script review, camera angle mapping, and timing generation.
6. **Production & Live Telemetry:** Asynchronous scene generation with live progress bars, QualityReviewer metrics, and final video preview.

### 3.2 Dual Lip-Sync Product Modes
To balance fidelity and reliability, the Video Cloner supports two audio/video synchronization modes:
- **Mode A (Voiceover Mode - Default):** `use_lip_sync = false`. High reliability, direct ElevenLabs canonical audio muxing, zero SyncLabs dependencies, zero watermarks. Subjects speak dynamically but are not strictly lip-synced.
- **Mode B (Talking Character Mode):** `use_lip_sync = true`. SyncLabs v2 integration with strict fail-closed error handling. Aligns subject mouth movements precisely to generated audio.

### 3.3 Model Routing Strategy
ShortcutAI uses cost-optimized model tiering to balance speed, intelligence, and expenditure:
- **Ingestion & Light NLP:** `gemini-3.1-flash-lite`
- **Blueprints & Heavy Reasoning:** `gemini-3.1-flash` with escalation to `us.anthropic.claude-sonnet-4-6` for complex script logic.
- **Visual Reference Generation:** `gemini-3.1-flash-image` (for Visual Identity Packs).
- **Video Generation:** `veo-3.1-fast-generate-001` (default) or `veo-3.1-generate-001` (premium).
- **Voice Synthesis:** `eleven_flash_v2_5` (speed/cost) or `eleven_v3` (premium quality).

### 3.4 Viral Repurposer Engine
- **Direct GCS Signed Uploads:** Direct client-to-bucket upload via V4 Signed URLs.
- **Dynamic Face-Tracking Layouts:** `podcast_stack`, `smart_solo`, `content_fit`.
- **Word-Level Animated Captions:** Styles include `bold_viral`, `hormozi_glow`, `podcast_clean`, `minimal_dark`, `neon_surge`.

### 3.5 Multi-Scene Orchestration
- Supports generating long-form shorts (30–60s) by chaining 2–8 logical scenes.
- Target Veo generation duration is dynamically determined: `max(5, ceil(audio_duration))`.
- Gemini QualityReviewer evaluates 4 extracted frames per scene, triggering an adaptive retry with `[DIRECTOR'S NOTE: ...]` if rejected.

---

## 4. User Roles & Subscription Tiers

| Tier | Monthly Price | Monthly Credits | Max Resolution | Max Upload Length | Watermark | Concurrent Renders |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Free** | $0 | 15 Credits (Trial) | 720p | 1 min (60s) | Yes | 1 job |
| **Starter** | $19 / mo | 500 Credits | 720p | 10 mins (600s) | Yes | 1 job |
| **Creator / Pro** | $49 / mo | 2,000 Credits | 1080p | 30 mins (1,800s) | No | 2 jobs |
| **Agency** | $199 / mo | 10,000 Credits | 4K (2160p) | 60 mins (3,600s) | No | 10 jobs |

---

## 5. Credit Consumption Rules

| Operation | Credit Cost | Description |
| :--- | :--- | :--- |
| **Repurposer Processing** | 10 Credits / min | Video cutting, face tracking, and caption rendering |
| **Global Dubbing** | 20 Credits / min | Translation, neural TTS voiceover, and audio muxing |
| **Idea Studio Script** | 5 Credits / script | Topic brainstorming and script generation |
| **Voice Clone Training** | 500 Credits (one-time) | Custom voice profile creation |
| **Video Cloner Base** | 10 Credits / job | Analysis, blueprinting, and audio muxing |
| **Visual Identity Pack** | 15 Credits / pack | Multi-angle character reference sheet generation |
| **Veo Scene Generation** | 25 Credits / scene | High-definition Veo video scene generation |
