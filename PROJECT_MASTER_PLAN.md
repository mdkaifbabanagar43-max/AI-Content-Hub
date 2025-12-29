# PROJECT MASTER PLAN: "AI Content Factory"
# PROJECT ID: leafy-oxide-480614-m4

## 1. Project Vision
We are building a comprehensive "All-in-One AI Content Studio" SaaS. The goal is to allow creators to go from zero to viral video in minutes using Google Cloud AI. The app has a Dashboard with a Sidebar containing 4 core operational sections.

## 2. Tech Stack (Strict)
* **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS, Lucide React (Icons), Framer Motion (Animations).
* **Backend:** Python FastAPI.
* **AI/ML:** Google Vertex AI (Gemini 1.5 Pro), Google Cloud Text-to-Speech, Google Cloud Translation API.
* **Storage:** Google Cloud Storage (Bucket: ai-studio-user-uploads, Region: us-central1).
* **Database:** Firebase Firestore (Users, Credits, Project History).
* **Auth:** Firebase Authentication.
* **Infrastructure:** Google Cloud Run (Target deployment).

## 3. The 4 Core Sidebar Sections (Features)

### SECTION 1: The Creator Studio (Idea-to-Video)
* **Workflow:**
    1.  User inputs a raw topic (e.g., "History of Bitcoin").
    2.  AI (Gemini) generates 5 viral titles/hooks. User selects one.
    3.  AI generates: Video Script, Audio Script, Thumbnail Prompt.
    4.  AI generates Audio (TTS).
    5.  Backend stitches Stock Footage or AI Video (Imagen/Veo) with Audio.
    6.  **Output:** A complete ready-to-download video + Title + Hashtags.

### SECTION 2: The Viral Repurposer (Long-to-Short)
* **Workflow:**
    1.  User uploads a long video file (MP4) or YouTube Link.
    2.  AI (Gemini 1.5 Pro) analyzes the video for high-engagement moments (laughter, key insights).
    3.  Backend (FFmpeg) crops video to 9:16 (Vertical) and cuts the clips.
    4.  AI adds dynamic captions (Alex Hormozi style).
    5.  **Output:** 5-10 Short viral clips.

### SECTION 3: The AI Voice Artist (Silent-to-Audio)
* **Workflow:**
    1.  User uploads a video with no audio.
    2.  User selects a Voice Persona (e.g., "Deep American Male").
    3.  AI analyzes the visual video content (Video-to-Text) to understand context OR User provides script.
    4.  AI generates voiceover perfectly timed to the video length.
    5.  **Output:** Video with synced professional audio.

### SECTION 4: The Global Dubber (Translation)
* **Workflow:**
    1.  User uploads an English video.
    2.  User selects Target Language (e.g., Spanish, Hindi).
    3.  AI Transcribes -> Translates -> Dubs (using Speech-to-Speech or TTS).
    4.  **Output:** The same video, but the speaker is talking in the new language.

## 4. Design Guidelines (Frontend)
* **Theme:** Dark Mode, Cyberpunk/Sleek aesthetic.
* **UX:** Fast interactions. Show "Loading Skeletons" or progress bars during AI generation.
* **Sidebar:** Permanent sidebar on the left.
* **Responsiveness:** Desktop first, but mobile-friendly.

## 5. Technical Rules for the AI Agent
* Always use `google-cloud-aiplatform` library for Vertex AI.
* Use `leafy-oxide-480614-m4` as the Project ID.
* Ensure CORS is enabled in FastAPI for `localhost:3000`.
* Handle errors gracefully (if AI fails, show a toast notification to user).