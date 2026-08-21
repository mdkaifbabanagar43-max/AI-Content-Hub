# Frontend Specification Document
## ShortcutAI — AI Content Hub

---

## 1. Overview & UI Philosophy

The **ShortcutAI** frontend is a high-performance Single Page Application (SPA) built with **Next.js 15+ (App Router)**, **React 19**, **TypeScript**, and **Tailwind CSS**. It embraces an obsidian dark-mode aesthetic (`#030303`), subtle glassmorphism (`backdrop-blur-2xl`), indigo/purple gradient accents, and fluid micro-animations powered by **Framer Motion**.

---

## 2. Navigation & Workspace Tabs

In the current implementation, `frontend/components/Layout.tsx` and `frontend/components/Sidebar.tsx` manage workspace routing through an in-memory tab engine. The legacy `trend-cloner` has been completely removed and unified into the single flagship **Video Cloner** workspace:

```typescript
// frontend/components/Layout.tsx
const pages = [
  { id: 'dashboard',    component: <DashboardHome setActiveTab={setActiveTab} /> },
  { id: 'idea-studio',  component: <IdeaStudio onNavigate={setActiveTab} /> },
  { id: 'video-cloner', component: <VideoCloner onNavigate={setActiveTab} /> }, // Unified Flagship Entry Point
  { id: 'repurposer',   component: <ViralRepurposer onNavigate={setActiveTab} /> },
  { id: 'voice-lab',    component: <VoiceLab onNavigate={setActiveTab} /> },
  { id: 'dubber',       component: <GlobalDubber onNavigate={setActiveTab} /> },
  { id: 'gallery',      component: <Gallery /> },
  { id: 'pricing',      component: <Pricing /> },
];
```

---

## 3. Unified Video Cloner Frontend Architecture

### 3.1 Unified 6-Stage Studio Architecture (`frontend/components/VideoCloner.tsx`)

The Video Cloner provides a polished, multi-step interactive studio experience mapping directly to the Phase 8 API lifecycle:

```
[STAGE 1: Source Ingestion] ──────> [STAGE 2: Video DNA & Visual Treatment] ──────> [STAGE 3: Visual Identity Pack]
  - Drag-and-drop MP4/MOV             - Hook Formula & Pacing                         - Multi-angle character turnarounds
  - Social media URL import (yt-dlp)  - Art style, lighting, camera language, mood    - Environment cards & Locked References
           │
           ▼
[STAGE 4: Creative Transformation] ──> [STAGE 5: Storyboard & Shot Planning] ──────> [STAGE 6: Production & Live Telemetry]
  - Story prompt & language selection   - Scene-by-scene script & dialogue review      - Live Veo scene progress bars
  - Audio Mode A vs. Mode B toggle      - Camera angle mapping & timing estimation     - QualityReviewer live status metrics
                                        - Click "Approve & Produce Video"              - Final video preview & export
```

### 3.2 Key Interaction Patterns
- **Stage 3 (Visual Identity Pack):** Renders a grid of generated character turnarounds and environment plates for user approval before moving to the storyboard stage.
- **Stage 4 (Audio Modes):** Presents a clear toggle between Mode A (Voiceover, fast/reliable) and Mode B (Talking Character, precise lip-sync).
- **Stage 6 (Live Telemetry):** Utilizes real-time visual progress bars reflecting the backend asynchronous Generation Attempt lifecycle.

---

## 4. Primary UI Components Breakdown

### 4.1 Shell & Navigation
- **`Layout.tsx`:** Primary application container. Manages focus mode (hiding sidebar), mobile hamburger navigation, and active workspace rendering.
- **`Sidebar.tsx`:** Collapsible sidebar with persisted state in `localStorage` (`sidebar-collapsed`). Displays user profile, plan tier badge (`starter`, `creator`, `agency`), real-time credit counter, and keyboard shortcuts (`⌘1`–`⌘7`).

### 4.2 Core Feature Modules
- **`DashboardHome.tsx`:** Quick action launchpads, usage statistics, and recent projects fetched from Firestore.
- **`VideoCloner.tsx`:** The centralized 6-stage video cloning studio.
- **`ViralRepurposer.tsx`:** 6-step video repurposer with GCS direct uploads, moment detection, facial recognition cropping (`podcast_stack`, `smart_solo`, `content_fit`), and dynamic animated captions (`bold_viral`, `neon_surge`).
- **`IdeaStudio.tsx` & `ConceptGraph.tsx`:** Topic-to-video studio generating AI hooks, scripts, TTS voiceovers, stock footage plans, and interactive SVG topic graphs.
- **`GlobalDubber.tsx`:** Multilingual translation interface with neural voiceover previews and lip-sync options.
- **`VoiceLab.tsx` & `AIVoiceArtist.tsx`:** TTS audio playground and voice cloning sample upload modal.
- **`Gallery.tsx`:** Media gallery of completed video exports and repurposed clips.

---

## 5. State Management Architecture

```
 ┌───────────────────────────────────────────────────────────────────────┐
 │                     GLOBAL REACT CONTEXT LAYER                        │
 │                                                                       │
 │   ┌─────────────────────────────────┐ ┌───────────────────────────┐   │
 │   │ AuthContext.tsx                 │ │ PlanContext.tsx           │   │
 │   │ - Firebase Auth User Object     │ │ - Real-Time Firestore Sync│   │
 │   │ - JWT ID Token Management       │ │ - Credits Balance State   │   │
 │   │ - Login / Logout Handlers       │ │ - Backend Capabilities    │   │
 │   └─────────────────────────────────┘ └───────────────────────────┘   │
 └───────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
 ┌───────────────────────────────────────────────────────────────────────┐
 │                    LOCAL COMPONENT STATE LAYER                        │
 │  useState & useRef Hooks (Form Controls, Stepper Index, UI Modals)    │
 └───────────────────────────────────────────────────────────────────────┘
```

---

## 6. Responsive Design Breakpoints

ShortcutAI enforces a **Mobile-First Responsive Design Policy**:

| Breakpoint | Min Width | Layout Behavior |
| :--- | :--- | :--- |
| **Mobile (`< 640px`)** | `0px` | Top fixed header active; sidebar collapses into full-screen drawer overlay. |
| **Tablet (`md: 768px`)** | `768px` | Collapsible sidebar appears on left; mobile header hidden. |
| **Desktop (`lg: 1024px`)** | `1024px` | Multi-panel workspaces in Repurposer, Idea Studio, and Video Cloner. |
| **Wide Screen (`xl: 1280px`)** | `1280px` | Side-by-side video player, storyboard, and telemetry panels. |
