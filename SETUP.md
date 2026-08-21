# AI Video SaaS - Project Setup Guide

## 🌐 Deployed Services

| Service | Platform | URL |
|---------|----------|-----|
| **Frontend** | Vercel | https://ai-video-saas.vercel.app (or your custom domain) |
| **Backend** | Google Cloud Run | https://ai-video-backend-1033839714188.us-central1.run.app |
| **Code** | GitHub | https://github.com/mdkaifbabanagar43-max/AI-Content-Hub |
| **GCP Project** | Google Cloud | `shortcutai-backend` |

---

## 💻 New Laptop Setup

### Prerequisites
1. **Node.js** v18+ → https://nodejs.org/
2. **Python** 3.10+ → https://www.python.org/
3. **Git** → https://git-scm.com/
4. **Google Cloud CLI** → https://cloud.google.com/sdk/docs/install

### Step 1: Clone Repository
```bash
git clone https://github.com/mdkaifbabanagar43-max/AI-Content-Hub.git
cd AI-Content-Hub
```

### Step 2: Frontend Setup
```bash
cd frontend
npm install
```

Create `frontend/.env.local`:
```env
NEXT_PUBLIC_FIREBASE_API_KEY=your_firebase_api_key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your_project_id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your_project.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
NEXT_PUBLIC_FIREBASE_APP_ID=your_app_id
```

Run locally:
```bash
npm run dev
# Opens at http://localhost:3000
```

### Step 3: Backend Setup
```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Step 4: Google Cloud Authentication
```bash
gcloud auth login
gcloud config set project shortcutai-backend
gcloud auth application-default login
```

Run backend locally:
```bash
uvicorn main:app --reload --port 8001
```

---

## 🚀 Deployment Commands

### Deploy Backend to Cloud Run
```bash
cd backend
gcloud run deploy ai-video-backend --source=. --region=us-central1
```

### Deploy Frontend to Vercel
Frontend auto-deploys when you push to `main`:
```bash
git add .
git commit -m "your changes"
git push origin main
```

---

## 🔑 Environment Variables (Secrets)

### Frontend (Vercel Dashboard → Settings → Environment Variables)
- `NEXT_PUBLIC_FIREBASE_API_KEY`
- `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`
- `NEXT_PUBLIC_FIREBASE_PROJECT_ID`
- `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET`
- `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID`
- `NEXT_PUBLIC_FIREBASE_APP_ID`

### Backend (Cloud Run → Edit & Deploy → Variables)
- `GOOGLE_CLOUD_PROJECT` = `shortcutai-backend`
- `PEXELS_API_KEY` = your Pexels API key
- Firebase credentials auto-injected via Cloud Run

---

## 📁 Project Structure
```
AI_Video_SaaS/
├── frontend/          # Next.js 14 app
│   ├── app/           # App router pages
│   ├── components/    # React components
│   └── .env.local     # Firebase config (create this)
│
├── backend/           # FastAPI Python backend
│   ├── routers/       # API endpoints
│   ├── services/      # Business logic (Veo, TTS, etc.)
│   └── requirements.txt
│
└── SETUP.md           # This file
```

---

## 🎬 Key Features
- **Idea Studio** - AI video generation from topics
- **Viral Repurposer** - Crop videos for social media
- **Global Dubber** - Multi-language dubbing
- **Product Ads** - AI product advertisement videos

---

## 📞 Support
GitHub Issues: https://github.com/mdkaifbabanagar43-max/AI-Content-Hub/issues
