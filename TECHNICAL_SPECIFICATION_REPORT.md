# Technical Specification Report
## AI Video SaaS Platform ("ShortcutsAI")
**Generated:** 2025-12-31 | **Status:** Production on Cloud Run + Vercel

---

## 1. Tech Stack & Configuration

### 1.1 Frontend Dependencies (`frontend/package.json`)

| Package | Version | Purpose |
|---------|---------|---------|
| **Next.js** | 15.1.9 | React framework with App Router |
| **React** | 19.0.1 | UI Library |
| **Firebase** | 12.6.0 | Authentication & Firestore Client |
| **Framer Motion** | 12.23.26 | Animations & Transitions |
| **TailwindCSS** | 4.x | Utility-first CSS |
| **Lucide React** | 0.559.0 | Icon library |
| **Sentry** | 10.32.1 | Error tracking |
| **PostHog** | 1.311.0 | Analytics |
| **react-dropzone** | 14.3.8 | File upload handling |
| **react-hot-toast / sonner** | 2.6.0 / 2.0.7 | Toast notifications |

### 1.2 Backend Dependencies (`backend/requirements.txt` + Base Image)

**Core Framework:**
- `fastapi` - API framework
- `uvicorn` - ASGI server
- `python-multipart` - File uploads
- `requests` - HTTP client
- `numpy < 2.0.0` - Numerical operations

**Google Cloud Services:**
- `google-cloud-aiplatform` - Vertex AI (Gemini models)
- `google-cloud-texttospeech` - TTS service
- `google-cloud-storage` - GCS file storage
- `google-cloud-translate` - Translation API
- `google-cloud-firestore` - Database client

**Firebase:**
- `firebase-admin` - Server-side Firebase SDK

**Pre-installed in Base Docker Image:**
- `moviepy 1.0.3` - Video editing
- `whisper` - Speech-to-text transcription
- `mediapipe` - Face detection
- `opencv-python (cv2)` - Image processing
- `yt_dlp` - YouTube download/transcript extraction

### 1.3 External Services

| Service | Usage |
|---------|-------|
| **Firebase Auth** | User authentication (email/password, Google) |
| **Firestore** | NoSQL database for users, projects, jobs |
| **Google Cloud Storage (GCS)** | Video/audio file storage |
| **Vertex AI (Gemini 2.0 Flash)** | Script generation, video analysis |
| **Google Cloud TTS** | Text-to-speech voiceovers |
| **Google Cloud Translate** | Translation for dubbing |
| **Cloud Run** | Backend deployment (containerized) |
| **Vercel** | Frontend deployment |
| **Pexels API** | Stock video footage search |
| **Replicate** | Lip sync service (optional) |

### 1.4 Environment Variables

**Backend (`.env` / Cloud Run Config):**
```
GOOGLE_CLOUD_PROJECT
GOOGLE_CLOUD_LOCATION
PEXELS_API_KEY
PORT
```

**Frontend (`.env.local` / Vercel Config):**
```
NEXT_PUBLIC_FIREBASE_API_KEY
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN
NEXT_PUBLIC_FIREBASE_PROJECT_ID
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID
NEXT_PUBLIC_FIREBASE_APP_ID
NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID
NEXT_PUBLIC_BACKEND_URL
```

---

## 2. Backend Architecture (`backend/`)

### 2.1 API Endpoints Structure (`main.py` - 2459 lines)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Health check |
| `/api/me` | GET | Get authenticated user profile with capabilities |
| `/system-config` | GET | Exposes plan limits, pricing, credit costs |

**Idea Studio (Script-to-Video):**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/brainstorm` | POST | Generate 4 viral content angles for a topic |
| `/generate-ideas` | POST | Generate 5 high-CTR video concepts |
| `/generate-script-preview` | POST | Generate script + visual plan preview |
| `/produce-video-assets` | POST | Generate script, visuals, and TTS audio |
| `/render-final` | POST | Full video render with credits deduction |
| `/render-video` | POST | Alternative render endpoint |
| `/save-project` | POST | Manual project save |

**Viral Repurposer (Video-to-Shorts):**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/get-upload-url` | POST/GET | Generate GCS signed URL for upload |
| `/analyze-file-gcs` | POST | AI analysis of uploaded video (Gemini 2.0) |
| `/repurpose-video` | POST | Cut, crop, caption video segment |
| `/analyze-video` | POST | YouTube URL transcript analysis |

**Global Dubber:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/dub-video` | POST | Translate & dub video to target language |
| `/generate-voiceover` | POST | Generate TTS voiceover |
| `/clone-voice` | POST | Voice cloning (mock implementation) |

**Utility:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/merge-video-audio` | POST | Combine video with new audio track |
| `/analyze-vision` | POST | Gemini 2.0 video analysis |
| `/my-projects/{user_id}` | GET | Fetch user's saved projects |

### 2.2 Core Logic: Video Generation Pipeline (`viral_editor.py` - 2183 lines)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    VIDEO GENERATION FLOW                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. INPUT: Script Text + Audio (base64)                            │
│       ↓                                                             │
│  2. SCENE ENGINE: Analyze script → Extract visual keywords          │
│       ↓                                                             │
│  3. VISUAL TRANSLATION: Abstract → Concrete search terms            │
│       "Inflation hurting savings" → "burning money pile fire"      │
│       ↓                                                             │
│  4. PEXELS FETCH: Parallel download of stock video clips            │
│       - batch_download_videos() → 4-6 clips                        │
│       - min_width enforcement (720p/1080p/4K)                      │
│       ↓                                                             │
│  5. VIDEO ASSEMBLY: MoviePy compositing                            │
│       - Trim clips to ~2.5s each                                   │
│       - Concatenate clips to match audio duration                  │
│       - Apply platform-specific aspect ratio (9:16)                │
│       ↓                                                             │
│  6. SUBTITLES: Whisper transcription → ASS captions                │
│       - Word-level timestamps                                      │
│       - Preset styles: bold_viral, podcast_clean, etc.             │
│       - Hook Boost (first 3s emphasis)                             │
│       ↓                                                             │
│  7. OUTPUT: MP4 upload to GCS → Signed/Public URL                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Functions:**
- `generate_turbo_video()` - Main orchestrator for Idea Studio
- `apply_smart_crop()` - Dispatcher for crop modes
- `process_podcast_stack()` - Dual-face stacked layout
- `process_dynamic_cut()` - Face-tracking center crop
- `process_content_fit()` - Blur background fit mode
- `FaceTracker` class - MediaPipe-based face detection & tracking
- `create_subtitles()` - Whisper → ASS caption generation

### 2.3 AI Models & Prompts

**Script Writing (ModelRoutingConfig-routed):**
```python
# Single source of truth: backend/config.py::ModelRoutingConfig
#   NORMAL_STORY  -> gemini-3.1-flash-lite           (Vertex AI, structured JSON)
#   COMPLEX_STORY -> us.anthropic.claude-sonnet-4-6  (AWS Bedrock)
# Complexity router:
#   core/services/production_director.py::determine_story_complexity
```
*Historical note: the earlier `get_best_model()` snippet (`gemini-2.0-flash-exp` /
`gemini-1.5-flash-001`, referenced as `main.py:350-367`) belonged to the legacy
viral_editor pipeline and no longer exists in the current `main.py`.*

**Prompt Strategy:**
- **Viral Hooks**: Curiosity gaps, negative urgency, listicles, stories
- **Style Rules**: Conversational tone, Grade 5 reading level, no "robot speak"
- **Forbidden Words**: 'realm', 'tapestry', 'delve', 'unleash', 'elevate'
- **Visual Bridge**: Abstract concepts → Concrete physical scenes

**Image Generation:** None (uses Pexels stock footage instead)

**Whisper Model:** `whisper.load_model("small")` for transcription

---

## 3. Frontend Architecture (`frontend/`)

### 3.1 Page Structure (`app/` directory)

| Path | Component | Description |
|------|-----------|-------------|
| `/` | `page.tsx` | Landing page |
| `/login` | `AuthPage.tsx` | Login form |
| `/signup` | `AuthPage.tsx` | Signup form |
| `/about` | `AboutPage.tsx` | About page |
| `/contact` | `ContactPage.tsx` | Contact form |
| `/terms` | `LegalPage.tsx` | Terms of service |
| `/privacy` | `LegalPage.tsx` | Privacy policy |
| `/refund-policy` | `RefundPolicy.tsx` | Refund policy |

### 3.2 Key Components (`components/`)

**Main Tools (Dashboard Tabs):**

| Component | Lines | Description |
|-----------|-------|-------------|
| `IdeaStudio.tsx` | 903 | Text-to-Video wizard (5 steps) |
| `ViralRepurposer.tsx` | 1202 | Video-to-Shorts wizard (6 steps) |
| `GlobalDubber.tsx` | ~36K bytes | Video dubbing/translation tool |
| `AIVoiceArtist.tsx` | ~16K bytes | TTS voiceover generator |
| `VoiceLab.tsx` | ~18K bytes | Voice testing/preview |

**Layout & Navigation:**

| Component | Description |
|-----------|-------------|
| `Layout.tsx` | Main dashboard wrapper |
| `Sidebar.tsx` | Navigation sidebar with tabs |
| `DashboardHome.tsx` | Dashboard overview with projects |

**Shared UI:**

| Component | Description |
|-----------|-------------|
| `ui/CreditConfirmationModal.tsx` | Credit deduction confirmation |
| `payment/LowBalanceModal.tsx` | Low credits warning |
| `VoiceCloningModal.tsx` | Voice clone upload UI |

### 3.3 IdeaStudio Workflow (`IdeaStudio.tsx`)

```
STEP 1: Topic Input
   │  User enters topic, selects platform/mood/duration
   │  handleBrainstorm() → POST /brainstorm
   ↓
STEP 2: Concept Selection
   │  Display 4 AI-generated angles
   │  User picks one → previewScript()
   │  POST /generate-script-preview
   ↓
STEP 2.5: Script Review (Modal)
   │  Editable script preview
   │  User confirms → generateScriptAndVisuals()
   │  POST /produce-video-assets
   ↓
STEP 3: Director's Studio
   │  Preview audio, edit script
   │  handleRender() → POST /render-final
   ↓
STEP 4: Rendering
   │  Loading state with progress simulation
   ↓
STEP 5: Success
   │  Video player + Download/Save buttons
```

**State Management:**
- `useState` for all local state
- Loading states: `isLoading`, `isRendering`, `isSaving`
- Error handling: try/catch with toast notifications

### 3.4 ViralRepurposer Workflow (`ViralRepurposer.tsx`)

```
STEP 1: Content Identity
   │  Select content type (Podcast/Gaming/Vlog/etc.)
   │  Animated card selection
   ↓
STEP 2: Video Upload
   │  Drag-drop or click to upload
   │  Direct GCS upload via signed URL
   ↓
STEP 3: AI Analysis
   │  POST /analyze-file-gcs
   │  Gemini 2.0 analyzes video for viral moments
   ↓
STEP 4: Clip Selection
   │  Display 3-5 suggested clips with timestamps
   │  User selects one
   ↓
STEP 5: Export Settings
   │  Layout mode (Podcast Stack/Content Fit/Smart Solo)
   │  Subtitle preset, resolution, hook boost
   ↓
STEP 6: Generation
   │  POST /repurpose-video
   │  Display final video with download
```

---

## 4. Data Models & Storage

### 4.1 Firestore Structure

```
firestore/
├── users/
│   └── {userId}/
│       ├── email: string
│       ├── credits: number
│       ├── plan: "starter" | "creator" | "agency" | "free"
│       ├── subscription_status: string
│       ├── created_at: Timestamp
│       │
│       ├── projects/
│       │   └── {projectId}/
│       │       ├── topic: string
│       │       ├── script: string (max 500 chars)
│       │       ├── video_url: string
│       │       ├── thumbnail_url: string
│       │       ├── platform: "tiktok" | "youtube"
│       │       ├── mood: string
│       │       ├── type: "generated" | "repurpose"
│       │       └── created_at: Timestamp
│       │
│       └── jobs/
│           └── {jobId}/
│               ├── id: string
│               ├── type: "idea_studio_script" | "repurpose_video" | "dubbing"
│               ├── status: "processing" | "completed" | "failed"
│               ├── credits_deducted: boolean
│               ├── metadata: object
│               ├── error: string (optional)
│               └── created_at: Timestamp
│
└── projects/ (legacy root collection)
    └── {projectId}/...
```

### 4.2 User Object Schema

```typescript
interface User {
  email: string;
  credits: number;              // Current credit balance
  plan: "starter" | "creator" | "agency" | "free";
  subscription_status?: string;
  created_at: Timestamp;
  
  // Injected by /api/me endpoint:
  capabilities: {
    idea_studio: boolean;
    script_generation: boolean;
    repurposer_basic: boolean;
    repurposer_smart_crop: boolean;
    dubbing: boolean;
    premium_voices: boolean;
    watermark_free: boolean;
    max_video_minutes: number;
    max_resolution: "720p" | "1080p" | "4k";
    priority_rendering: boolean;
    bulk_upload: boolean;
    concurrent_jobs: number;
  }
}
```

### 4.3 Pricing & Credits Configuration (`config.py`)

```python
CREDIT_COSTS = {
    'idea_studio_script': 5,        # Per script
    'repurposer_per_minute': 10,    # Per minute of input
    'dubbing_per_minute': 20,       # Per minute of dubbing
    'voice_clone_training': 500     # One-time fee
}

PRICING_TIERS = {
    'starter': { 'price': 1900, 'credits': 500 },   # $19
    'creator': { 'price': 4900, 'credits': 2000 },  # $49
    'agency':  { 'price': 19900, 'credits': 10000 } # $199
}
```

---

## 5. Current Status & Known Issues

### 5.1 Fully Working Features ✅

Based on code analysis and conversation history:

- **Idea Studio**: Full pipeline (brainstorm → script → render → save)
- **Viral Repurposer - Center Crop Mode**: Working end-to-end
- **GCS Upload/Download**: Signed URL flow working
- **Firebase Authentication**: Login/signup/token verification
- **Google Cloud TTS**: Voiceover generation
- **Whisper Subtitles**: Word-level captions with presets
- **Credit System**: Deduction, balance checks, job tracking
- **Plan Limits**: Resolution/watermark enforcement

### 5.2 Incomplete or Partially Working ⚠️

| Feature | Status | Notes |
|---------|--------|-------|
| **Podcast Stack Mode** | Partial | Face tracking works but occasional aspect ratio issues |
| **Voice Cloning** | Mock | Returns mock voice_id, no real clone training |
| **Lip Sync** | External | Depends on Replicate API (`lipsync_service.py` is stub) |
| **YouTube URL Analysis** | Limited | Requires Chrome cookies, may fail on some videos |
| **Premium Voices Check** | Mock | `premium_voices` gate exists but voice metadata not validated |

### 5.3 Code Comments & TODOs

```python
# From main.py:
# "RELAXED FOR MVP: Allow frontend to update credits/plan (mock payment)"
# "Logic check: we don't have video_duration here yet"
# "In real app: Call ElevenLabs /clone → Get Voice ID → Save to DB"

# From viral_editor.py:
# "LAZY LOADING GLOBALS" - Whisper model loaded on first use
# FaceTracker has fallback when MediaPipe fails
```

### 5.4 Known Technical Debt

1. **Duplicate Endpoints**: Some endpoints defined twice (e.g., `/get-upload-url`)
2. **Hardcoded Bucket Names**: GCS buckets hardcoded in multiple places
3. **Scene Engine Coupling**: Optional dependency with fallback logic
4. **Retry Logic**: Gemini API has manual retry, could use tenacity library
5. **Cleanup Race Conditions**: Temp file cleanup in `finally` blocks may fail

---

## Appendix: File Summary

| File | Lines | Purpose |
|------|-------|---------|
| `backend/main.py` | 2459 | All API endpoints |
| `backend/viral_editor.py` | 2183 | Video processing engine |
| `backend/config.py` | 117 | Pricing, plans, features |
| `backend/firebase_utils.py` | 200 | Firestore helpers |
| `backend/dubbing_service.py` | ~400 | Translation + TTS dubbing |
| `backend/tts_service.py` | ~100 | Google Cloud TTS wrapper |
| `frontend/components/IdeaStudio.tsx` | 903 | Text-to-Video UI |
| `frontend/components/ViralRepurposer.tsx` | 1202 | Video-to-Shorts UI |
| `frontend/components/GlobalDubber.tsx` | ~1000 | Dubbing UI |
