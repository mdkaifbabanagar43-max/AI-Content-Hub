# MODEL COMPATIBILITY MATRIX — CLONEFRAME

**Configuration Source of Truth:** `backend/config.py` (`ModelRoutingConfig`)  
**Enforcement:** Static AST verification via `backend/tests/test_model_routing.py`  

---

## 1. Canonical Category Mapping

| Routing Category | Model ID | Provider | API Protocol / Method | Primary Function |
| :--- | :--- | :--- | :--- | :--- |
| `SOURCE_ANALYSIS` | `gemini-3.1-flash-lite` | Google Vertex AI | `genai.Client.models.generate_content` (Structured JSON Schema) | Video media decoding, transcript, and 9-channel DNA extraction. |
| `TREND_ANALYSIS` | `gemini-3.1-flash-lite` | Google Vertex AI | `genai.Client.models.generate_content` (Structured JSON Schema) | Viral hook and audience psychology pattern analysis. |
| `NORMAL_STORY` | `gemini-3.1-flash-lite` | Google Vertex AI | `genai.Client.models.generate_content` (Structured JSON Schema) | Standard duration (≤30s, ≤3 chars) creative transformation. |
| `COMPLEX_STORY` | `us.anthropic.claude-sonnet-4-6` | Anthropic on Vertex AI | `AnthropicVertex.messages.create` | Complex narrative (>30s or >3 characters) storyboarding. |
| `REFERENCE_IMAGE` | `imagen-3.0-generate-002` | Google Vertex AI | `genai.Client.models.generate_images` | Multi-angle character sheet and style reference generation. |
| `VIDEO_DEFAULT` | `veo-3.1-generate-001` | Google Vertex AI | `veo.generate_video` (Long-running async operation) | Prescriptive 1080p generative video rendering with reference image. |
| `VIDEO_FAST` | `veo-3.1-fast-generate-001` | Google Vertex AI | `veo.generate_video` (Long-running async operation) | Fast iteration video clip generation. |
| `VIDEO_PREMIUM` | `veo-3.1-generate-001` | Google Vertex AI | `veo.generate_video` (High quality parameterization) | 4K/60fps master scene video rendering. |
| `QUALITY_REVIEW` | `gemini-3.1-flash-lite` | Google Vertex AI | `genai.Client.models.generate_content` (Vision Multimodal) | Automated scene review: continuity, artifacts, style match. |
| `QUALITY_REVIEW_ESCALATE` | `gemini-1.5-pro` | Google Vertex AI | `genai.Client.models.generate_content` (Vision Deep Multimodal) | Disputed or low-confidence quality evaluations. |
| `VOICE_DEFAULT` | `eleven_multilingual_v2` | ElevenLabs | `elevenlabs.generate` / `text_to_speech` | Character and narrator dialogue synthesis with timestamps. |
| `VOICE_PREMIUM` | `eleven_turbo_v2_5` | ElevenLabs | `elevenlabs.generate` | Ultra-low latency conversational voice generation. |
| `VOICE_LONGFORM` | `eleven_multilingual_v2` | ElevenLabs | `elevenlabs.generate` (Chunked longform) | Narration tracks exceeding 60 seconds. |
| `LIPSYNC` | `sync-1.7.1` | SyncLabs | `synclabs.generate` (Async task polling) | Neural lip-synchronization for character dialogue tracks. |

---

## 2. Fail-Closed & Fallback Invariants

```
+-------------------------------------------------------------------------------+
|                       MODEL FAIL-CLOSED ARCHITECTURE                          |
+------------------------------------+------------------------------------------+
| AI Generation Calls                | Strict Fail-Closed (NO silent fallback)  |
|                                    | If Veo fails -> Job fails -> Full Refund |
+------------------------------------+------------------------------------------+
| Voiceover Calls                    | Strict Fail-Closed (NO silent fallback)  |
|                                    | If ElevenLabs fails -> Job fails         |
+------------------------------------+------------------------------------------+
| LipSync Calls                      | Explicit Fallback Policy:                |
|                                    | - Default: Fail-Closed                   |
|                                    | - If `allow_lip_sync_fallback=True`:     |
|                                    |   Use native un-synced Veo video clip    |
+------------------------------------+------------------------------------------+
| Quality Review                     | Escalation Strategy:                     |
|                                    | - Level 1: `gemini-3.1-flash-lite`       |
|                                    | - Level 2: `gemini-1.5-pro`              |
|                                    | - Max retries: 1 per scene               |
+------------------------------------+------------------------------------------+
```

---

## 3. Provider Adapter Hierarchy

Business logic modules **never** invoke raw third-party SDK clients directly:

```
[UniversalCreativeDirector / CanonicalGenerationEngine]
                          │
                          ▼
              [core.services.ModelRouter]
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
[GeminiProvider]  [ClaudeProvider]  [VeoProvider]
 (Google GenAI)    (Anthropic API)  (Vertex Veo)
         │                │                │
         ▼                ▼                ▼
[ElevenLabsProvider] [SyncLabsProvider]
```
