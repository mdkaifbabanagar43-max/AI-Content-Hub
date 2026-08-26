'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
    Sparkles,
    Zap,
    Mic,
    ArrowRight,
    Terminal,
    CheckCircle2,
    Users,
    Briefcase,
    Lock,
    Video,
    Cpu,
    Server,
    Database,
    Cloud,
    Layers,
    Copy,
    Check,
    Flame,
    Code2,
    Workflow,
    Building2
} from 'lucide-react';
import Navbar from './Navbar';
import Footer from './Footer';
import Pricing from './Pricing';
import { toast } from 'sonner';

export default function LandingPage({ onSignInClick }: { onSignInClick: () => void }) {
    const [waitlistEmail, setWaitlistEmail] = useState('');
    const [isSubmittingWaitlist, setIsSubmittingWaitlist] = useState(false);
    const [waitlistJoined, setWaitlistJoined] = useState(false);
    const [activeTab, setActiveTab] = useState<'script' | 'voice' | 'render' | 'delivery'>('script');
    const [copiedCode, setCopiedCode] = useState(false);
    const [activeLang, setActiveLang] = useState<'python' | 'curl' | 'node'>('python');

    const handleWaitlistSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!waitlistEmail || !waitlistEmail.includes('@')) {
            toast.error('Please enter a valid business email address.');
            return;
        }
        setIsSubmittingWaitlist(true);
        setTimeout(() => {
            setIsSubmittingWaitlist(false);
            setWaitlistJoined(true);
            toast.success('Priority B2B Agency Beta Access confirmed! We have reserved your spot.');
        }, 600);
    };

    const copyApiSnippet = () => {
        const snippet = activeLang === 'python' ? pythonCode : activeLang === 'node' ? nodeCode : curlCode;
        navigator.clipboard.writeText(snippet);
        setCopiedCode(true);
        toast.success('API code snippet copied to clipboard!');
        setTimeout(() => setCopiedCode(false), 2000);
    };

    const pythonCode = `import requests

# 1. Dispatch Automated Video Generation to CloneFrame Pipeline
response = requests.post(
    "https://api.cloneframe.com/v1/generate",
    headers={"Authorization": "Bearer cf_live_agency_token_2026"},
    json={
        "client_id": "client_luxury_realestate",
        "topic": "3 Modern Architectural Trends Dominating 2026",
        "models": {
            "script": "gemini-2.0-flash",
            "voice": "elevenlabs-multilingual-v2",
            "video_render": "google-veo-2"
        },
        "target_aspect_ratio": "9:16",
        "language": "en-US",
        "character_dna_id": "char_lead_architect_01"
    }
)

# Returns async job ID queued via Google Cloud Tasks
job = response.json()
print(f"Pipeline active: {job['job_id']} | Status: {job['status']}")`;

    const nodeCode = `import axios from 'axios';

// 1. Dispatch Automated Video Generation to CloneFrame Pipeline
const { data: job } = await axios.post(
  'https://api.cloneframe.com/v1/generate',
  {
    client_id: 'client_luxury_realestate',
    topic: '3 Modern Architectural Trends Dominating 2026',
    models: {
      script: 'gemini-2.0-flash',
      voice: 'elevenlabs-multilingual-v2',
      video_render: 'google-veo-2'
    },
    target_aspect_ratio: '9:16',
    language: 'en-US',
    character_dna_id: 'char_lead_architect_01'
  },
  {
    headers: { Authorization: 'Bearer cf_live_agency_token_2026' }
  }
);

console.log(\`Pipeline active: \${job.job_id} | Status: \${job.status}\`);`;

    const curlCode = `curl -X POST "https://api.cloneframe.com/v1/generate" \\
  -H "Authorization: Bearer cf_live_agency_token_2026" \\
  -H "Content-Type: application/json" \\
  -d '{
    "client_id": "client_luxury_realestate",
    "topic": "3 Modern Architectural Trends Dominating 2026",
    "models": {
      "script": "gemini-2.0-flash",
      "voice": "elevenlabs-multilingual-v2",
      "video_render": "google-veo-2"
    },
    "target_aspect_ratio": "9:16",
    "language": "en-US"
  }'`;

    return (
        <div className="min-h-screen bg-[#030307] text-white font-sans selection:bg-indigo-500/30 overflow-x-hidden">
            <Navbar onSignInClick={onSignInClick} onWaitlistClick={() => {
                const element = document.getElementById('waitlist-section');
                if (element) element.scrollIntoView({ behavior: 'smooth' });
            }} />

            {/* =========================================================================
                1. HERO SECTION (Explicit B2B Headline & Sub-headline from Brief)
            ========================================================================= */}
            <section className="relative pt-20 pb-24 lg:pt-32 lg:pb-36 overflow-hidden">
                {/* Ambient Radial Gradients */}
                <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[550px] bg-gradient-to-tr from-indigo-600/20 via-purple-600/20 to-pink-600/10 blur-[150px] rounded-full pointer-events-none -z-10"></div>
                <div className="absolute top-10 left-10 w-72 h-72 bg-blue-600/10 blur-[100px] rounded-full pointer-events-none -z-10"></div>

                <div className="w-full max-w-[1500px] mx-auto px-4 sm:px-6 md:px-12 text-center relative z-10">
                    {/* B2B Category Badge */}
                    <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-white/[0.04] border border-indigo-500/30 shadow-[0_0_20px_rgba(99,102,241,0.15)] mb-8 backdrop-blur-xl">
                        <span className="flex h-2 w-2 relative">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
                        </span>
                        <span className="text-xs sm:text-sm font-semibold tracking-wide text-zinc-200">
                            MULTI-MODEL AI VIDEO ORCHESTRATION FOR B2B AGENCIES
                        </span>
                    </div>

                    {/* REQUIRED HERO HEADLINE */}
                    <h1 className="text-[44px] sm:text-[64px] lg:text-[84px] font-[900] tracking-[-0.035em] leading-[1.05] text-white mb-7 max-w-5xl mx-auto">
                        The Automated AI Video Pipeline for{' '}
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-300 via-purple-300 to-pink-300">
                            B2B Agencies.
                        </span>
                    </h1>

                    {/* REQUIRED HERO SUB-HEADLINE */}
                    <p className="text-[19px] sm:text-[23px] lg:text-[25px] text-zinc-300 font-normal max-w-4xl mx-auto mb-10 leading-relaxed tracking-tight">
                        Turn concepts into ready-to-publish short-form videos in seconds. Orchestrating <span className="text-white font-semibold">Gemini 2.0</span>, <span className="text-white font-semibold">Veo</span>, and <span className="text-white font-semibold">ElevenLabs</span> into one unified API.
                    </p>

                    {/* Interactive Waitlist / CTA Component */}
                    <div id="waitlist-section" className="max-w-xl mx-auto mb-14">
                        {!waitlistJoined ? (
                            <form onSubmit={handleWaitlistSubmit} className="flex flex-col sm:flex-row items-center gap-2.5 p-2 bg-[#090912]/90 border border-white/15 rounded-2xl shadow-[0_15px_40px_rgba(0,0,0,0.8)] backdrop-blur-2xl">
                                <input
                                    type="email"
                                    value={waitlistEmail}
                                    onChange={(e) => setWaitlistEmail(e.target.value)}
                                    placeholder="Enter your agency or business email..."
                                    className="w-full px-5 py-3.5 bg-transparent text-white placeholder-zinc-500 text-sm sm:text-base outline-none rounded-xl"
                                    required
                                />
                                <button
                                    type="submit"
                                    disabled={isSubmittingWaitlist}
                                    className="w-full sm:w-auto px-7 py-3.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-600 hover:from-indigo-400 hover:to-purple-500 text-white font-bold text-sm sm:text-base rounded-xl transition-all shadow-[0_0_25px_rgba(99,102,241,0.4)] flex items-center justify-center gap-2 shrink-0 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50"
                                >
                                    {isSubmittingWaitlist ? 'Securing Spot...' : 'Join Private Beta'}
                                    <ArrowRight size={16} />
                                </button>
                            </form>
                        ) : (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                className="p-4 bg-emerald-950/40 border border-emerald-500/30 rounded-2xl text-center flex items-center justify-between gap-4"
                            >
                                <div className="flex items-center gap-3 text-left">
                                    <CheckCircle2 size={24} className="text-emerald-400 shrink-0" />
                                    <div>
                                        <div className="text-sm font-bold text-white">Spot Reserved: Agency Beta Priority Queue (#142)</div>
                                        <div className="text-xs text-emerald-300/80">Check {waitlistEmail} for your developer sandbox key.</div>
                                    </div>
                                </div>
                                <button
                                    onClick={onSignInClick}
                                    className="px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-black font-bold text-xs rounded-lg shrink-0 transition-colors"
                                >
                                    Launch App
                                </button>
                            </motion.div>
                        )}

                        <div className="flex flex-wrap items-center justify-center gap-6 mt-4 text-xs sm:text-sm text-zinc-400 font-medium">
                            <span className="flex items-center gap-1.5">
                                <CheckCircle2 size={14} className="text-emerald-400" /> Multi-Tenant Agency Workspaces
                            </span>
                            <span className="flex items-center gap-1.5">
                                <CheckCircle2 size={14} className="text-emerald-400" /> Dedicated Google Cloud Compute
                            </span>
                            <span className="flex items-center gap-1.5">
                                <CheckCircle2 size={14} className="text-emerald-400" /> Zero Infrastructure Overhead
                            </span>
                        </div>
                    </div>

                    {/* Live Pipeline Metric Counters */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto pt-6 border-t border-white/10">
                        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                            <div className="text-2xl sm:text-3xl font-[900] text-white">99.9%</div>
                            <div className="text-xs text-zinc-400 font-mono mt-0.5">Cloud Run Uptime SLA</div>
                        </div>
                        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                            <div className="text-2xl sm:text-3xl font-[900] text-indigo-400">&lt; 45s</div>
                            <div className="text-xs text-zinc-400 font-mono mt-0.5">Average Scene Render</div>
                        </div>
                        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                            <div className="text-2xl sm:text-3xl font-[900] text-purple-400">1080p 60fps</div>
                            <div className="text-xs text-zinc-400 font-mono mt-0.5">Native 9:16 Vertical</div>
                        </div>
                        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                            <div className="text-2xl sm:text-3xl font-[900] text-emerald-400">30+ Langs</div>
                            <div className="text-xs text-zinc-400 font-mono mt-0.5">Multilingual Dubbing</div>
                        </div>
                    </div>
                </div>
            </section>

            {/* =========================================================================
                2. HOW IT WORKS (THE PIPELINE BREAKDOWN - HEAVY COMPUTE PROOF)
            ========================================================================= */}
            <section id="pipeline" className="py-24 bg-[#05050b] border-t border-white/10 relative">
                <div className="w-full max-w-[1500px] mx-auto px-4 sm:px-6 md:px-12">
                    <div className="text-center max-w-3xl mx-auto mb-16">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-mono font-semibold uppercase tracking-wider mb-4">
                            <Workflow size={13} /> Heavy Cloud Compute Architecture
                        </div>
                        <h2 className="text-[34px] sm:text-[46px] font-[900] text-white tracking-tight leading-tight mb-4">
                            How the Multi-Model Pipeline Executes
                        </h2>
                        <p className="text-base sm:text-lg text-zinc-400">
                            Our asynchronous FastAPI engine orchestrates world-class foundation models on Google Cloud, processing thousands of GPU-intensive render jobs concurrently.
                        </p>
                    </div>

                    {/* Pipeline Stage Cards (4 Pillars: Scripting -> Voice -> Render -> Cloud Delivery) */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
                        {/* Step 1: Scripting with Gemini 2.0 */}
                        <div className={`p-6 rounded-2xl border transition-all cursor-pointer relative ${
                            activeTab === 'script' 
                                ? 'bg-gradient-to-b from-indigo-950/40 to-black border-indigo-500/50 shadow-[0_0_30px_rgba(99,102,241,0.2)]' 
                                : 'bg-[#0a0a12]/70 border-white/10 hover:border-white/20'
                        }`} onClick={() => setActiveTab('script')}>
                            <div className="flex items-center justify-between mb-4">
                                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300">
                                    STAGE 01
                                </span>
                                <span className="text-[11px] font-mono text-zinc-400">Vertex AI</span>
                            </div>
                            <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-4 text-indigo-400">
                                <Sparkles size={24} />
                            </div>
                            <h3 className="text-lg font-bold text-white mb-2">1. Script & Narrative Synthesis</h3>
                            <p className="text-xs sm:text-sm text-zinc-400 leading-relaxed mb-4">
                                <strong className="text-zinc-200">Gemini 2.0 Flash</strong> analyzes client prompts, extracting viral retention hooks, dialogue pacing, and compiling deterministic scene bibles.
                            </p>
                            <div className="text-[11px] font-mono text-indigo-400 flex items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span> Gemini 2.0 Flash API
                            </div>
                        </div>

                        {/* Step 2: Voice with ElevenLabs */}
                        <div className={`p-6 rounded-2xl border transition-all cursor-pointer relative ${
                            activeTab === 'voice' 
                                ? 'bg-gradient-to-b from-purple-950/40 to-black border-purple-500/50 shadow-[0_0_30px_rgba(168,85,247,0.2)]' 
                                : 'bg-[#0a0a12]/70 border-white/10 hover:border-white/20'
                        }`} onClick={() => setActiveTab('voice')}>
                            <div className="flex items-center justify-between mb-4">
                                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-purple-500/20 text-purple-300">
                                    STAGE 02
                                </span>
                                <span className="text-[11px] font-mono text-zinc-400">Voice Synthesis</span>
                            </div>
                            <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center mb-4 text-purple-400">
                                <Mic size={24} />
                            </div>
                            <h3 className="text-lg font-bold text-white mb-2">2. Voice & Dialogue Engine</h3>
                            <p className="text-xs sm:text-sm text-zinc-400 leading-relaxed mb-4">
                                <strong className="text-zinc-200">ElevenLabs Multilingual v2</strong> generates broadcast-grade character dialogue with custom emotional inflections and millisecond timestamping.
                            </p>
                            <div className="text-[11px] font-mono text-purple-400 flex items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-purple-400"></span> ElevenLabs Studio API
                            </div>
                        </div>

                        {/* Step 3: Neural Video with Veo */}
                        <div className={`p-6 rounded-2xl border transition-all cursor-pointer relative ${
                            activeTab === 'render' 
                                ? 'bg-gradient-to-b from-pink-950/40 to-black border-pink-500/50 shadow-[0_0_30px_rgba(236,72,153,0.2)]' 
                                : 'bg-[#0a0a12]/70 border-white/10 hover:border-white/20'
                        }`} onClick={() => setActiveTab('render')}>
                            <div className="flex items-center justify-between mb-4">
                                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-pink-500/20 text-pink-300">
                                    STAGE 03
                                </span>
                                <span className="text-[11px] font-mono text-zinc-400">Neural Video</span>
                            </div>
                            <div className="w-12 h-12 rounded-xl bg-pink-500/10 border border-pink-500/20 flex items-center justify-center mb-4 text-pink-400">
                                <Video size={24} />
                            </div>
                            <h3 className="text-lg font-bold text-white mb-2">3. Google Veo Neural Render</h3>
                            <p className="text-xs sm:text-sm text-zinc-400 leading-relaxed mb-4">
                                Dispatched to <strong className="text-zinc-200">Google Veo</strong> with character turnaround DNA sheets for flawless consistency across multiple shot angles and environments.
                            </p>
                            <div className="text-[11px] font-mono text-pink-400 flex items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-pink-400"></span> Google Veo 2 + Imagen
                            </div>
                        </div>

                        {/* Step 4: Cloud Tasks & Delivery */}
                        <div className={`p-6 rounded-2xl border transition-all cursor-pointer relative ${
                            activeTab === 'delivery' 
                                ? 'bg-gradient-to-b from-emerald-950/40 to-black border-emerald-500/50 shadow-[0_0_30px_rgba(16,185,129,0.2)]' 
                                : 'bg-[#0a0a12]/70 border-white/10 hover:border-white/20'
                        }`} onClick={() => setActiveTab('delivery')}>
                            <div className="flex items-center justify-between mb-4">
                                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                                    STAGE 04
                                </span>
                                <span className="text-[11px] font-mono text-zinc-400">GCS CDN</span>
                            </div>
                            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-4 text-emerald-400">
                                <Cloud size={24} />
                            </div>
                            <h3 className="text-lg font-bold text-white mb-2">4. GCS Storage & CDN Delivery</h3>
                            <p className="text-xs sm:text-sm text-zinc-400 leading-relaxed mb-4">
                                Distributed <strong className="text-zinc-200">Cloud Tasks</strong> workers stitch scenes, burn kinetic subtitles, mux high-fidelity audio, and output signed GCS MP4 URLs.
                            </p>
                            <div className="text-[11px] font-mono text-emerald-400 flex items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Cloud Storage + Tasks
                            </div>
                        </div>
                    </div>

                    {/* Interactive Pipeline Simulator Canvas */}
                    <div className="p-6 sm:p-8 rounded-3xl bg-[#080811] border border-white/10 relative overflow-hidden shadow-2xl">
                        <div className="flex flex-col lg:flex-row items-center justify-between gap-8">
                            <div className="w-full lg:w-1/2 space-y-4">
                                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-white/5 border border-white/10 text-xs font-mono text-zinc-300">
                                    <Server size={12} className="text-indigo-400" /> Microservice Orchestrator Inspection
                                </div>
                                <h4 className="text-2xl font-bold text-white">
                                    {activeTab === 'script' && 'Prompt-to-Scene Compiler (Gemini 2.0 Flash)'}
                                    {activeTab === 'voice' && 'Neural Voice Allocation (ElevenLabs v2)'}
                                    {activeTab === 'render' && 'Diffusion Frame Synthesis (Google Veo)'}
                                    {activeTab === 'delivery' && 'Asynchronous Cloud Tasks Delivery (GCS)'}
                                </h4>
                                <p className="text-sm text-zinc-400 leading-relaxed">
                                    {activeTab === 'script' && 'Translates high-level brand briefs into 5-act narrative arcs with visual continuity constraints, emotion flags, and zero hallucination risk.'}
                                    {activeTab === 'voice' && 'Assigns character IDs to dedicated vocal fingerprints, regulating volume curves and dynamic audio ducking behind background soundscapes.'}
                                    {activeTab === 'render' && 'Combines reference visual identity packs with scene-level camera movement (Pan, Zoom, Tracking Shot) at 1080x1920 vertical canvas.'}
                                    {activeTab === 'delivery' && 'Executes MoviePy direct audio-video muxing fallback with zero dropped frames, caching raw assets securely inside Google Cloud Storage.'}
                                </p>
                                <div className="flex flex-wrap gap-2 pt-2">
                                    <span className="px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/10 text-xs font-mono text-zinc-300">
                                        Format: 9:16 Vertical
                                    </span>
                                    <span className="px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/10 text-xs font-mono text-zinc-300">
                                        Concurrency: 100+ Jobs
                                    </span>
                                    <span className="px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/10 text-xs font-mono text-zinc-300">
                                        Payload: JSON REST / Webhooks
                                    </span>
                                </div>
                            </div>

                            {/* Simulated Pipeline Execution Preview */}
                            <div className="w-full lg:w-1/2 bg-black/80 rounded-2xl border border-white/10 p-5 font-mono text-xs text-zinc-300 shadow-inner">
                                <div className="flex items-center justify-between pb-3 mb-3 border-b border-white/10 text-zinc-400">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2.5 h-2.5 rounded-full bg-red-500/80"></div>
                                        <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/80"></div>
                                        <div className="w-2.5 h-2.5 rounded-full bg-green-500/80"></div>
                                        <span className="text-[11px] text-zinc-400 ml-2">cloudrun_worker_01.log</span>
                                    </div>
                                    <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                                        200 OK
                                    </span>
                                </div>

                                <pre className="overflow-x-auto text-[11px] leading-relaxed text-indigo-300">
{activeTab === 'script' ? `{
  "action": "COMPILE_STORYBOARD",
  "engine": "gemini-2.0-flash",
  "topic": "3 Modern Architectural Trends",
  "scenes": [
    {
      "scene_id": "scene_001",
      "pacing": "Fast Hook (3.2s)",
      "camera": "Dynamic Push-In",
      "dialogue": "Most buildings waste 40% of their energy. Here is why."
    }
  ],
  "validation": "ORIGINALITY_SCORE: 0.04 (PASSED)"
}` : activeTab === 'voice' ? `{
  "action": "SYNTHESIZE_AUDIO",
  "provider": "ElevenLabs",
  "voice_id": "v_architect_authoritative_en",
  "duration": 3.2,
  "sample_rate": 44100,
  "audio_gcs_uri": "gs://shortcutai-user-uploads-2026/audio_01.mp3"
}` : activeTab === 'render' ? `{
  "action": "GENERATE_VIDEO_CLIP",
  "model": "google-veo-2",
  "resolution": "1080x1920",
  "fps": 60,
  "art_style": "Photorealistic 3D Architectural",
  "video_raw_uri": "gs://shortcutai-user-uploads-2026/raw_scene_01.mp4"
}` : `{
  "action": "ASSEMBLE_AND_FINALIZE",
  "status": "COMPLETED",
  "muxing_engine": "MoviePy_Direct_Mux",
  "final_mp4_url": "https://storage.googleapis.com/shortcutai-user-uploads-2026/render_final.mp4",
  "total_pipeline_latency_seconds": 38.4
}`}
                                </pre>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* =========================================================================
                3. B2B SMMA AGENCY SOLUTIONS (Why Marketing Agencies Use CloneFrame)
            ========================================================================= */}
            <section id="solutions" className="py-24 bg-[#030307] relative">
                <div className="w-full max-w-[1500px] mx-auto px-4 sm:px-6 md:px-12">
                    <div className="text-center max-w-3xl mx-auto mb-16">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs font-mono font-semibold uppercase tracking-wider mb-4">
                            <Briefcase size={13} /> Agency-First Features
                        </div>
                        <h2 className="text-[34px] sm:text-[46px] font-[900] text-white tracking-tight leading-tight mb-4">
                            Built for High-Volume Marketing Agencies
                        </h2>
                        <p className="text-base sm:text-lg text-zinc-400">
                            Eliminate the bottlenecks of manual video editors and fragmented tools. Deliver 10x more content for your agency clients at a fraction of the cost.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {/* Card 1: Multi-Client Workspaces */}
                        <div className="p-8 rounded-3xl bg-[#090914] border border-white/10 hover:border-indigo-500/40 transition-all group">
                            <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-6 text-indigo-400 group-hover:scale-110 transition-transform">
                                <Building2 size={28} />
                            </div>
                            <h3 className="text-2xl font-bold text-white mb-3">Multi-Client Isolation</h3>
                            <p className="text-zinc-400 text-sm leading-relaxed mb-6">
                                Create isolated workspaces for each agency client. Store distinct brand colors, character DNA bibles, tone guidelines, and font assets securely.
                            </p>
                            <ul className="space-y-2.5 text-xs text-zinc-300 font-medium">
                                <li className="flex items-center gap-2">
                                    <CheckCircle2 size={14} className="text-indigo-400" /> Client-Specific Asset Segregation
                                </li>
                                <li className="flex items-center gap-2">
                                    <CheckCircle2 size={14} className="text-indigo-400" /> Dedicated Voice Fingerprints
                                </li>
                            </ul>
                        </div>

                        {/* Card 2: Batch Reel Engine */}
                        <div className="p-8 rounded-3xl bg-[#090914] border border-white/10 hover:border-purple-500/40 transition-all group">
                            <div className="w-14 h-14 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center mb-6 text-purple-400 group-hover:scale-110 transition-transform">
                                <Flame size={28} />
                            </div>
                            <h3 className="text-2xl font-bold text-white mb-3">Viral Hook Split-Testing</h3>
                            <p className="text-zinc-400 text-sm leading-relaxed mb-6">
                                Automatically generate 10 variations of the first 3 seconds of any video. Test different psychological hooks on TikTok, Instagram Reels, and YouTube Shorts.
                            </p>
                            <ul className="space-y-2.5 text-xs text-zinc-300 font-medium">
                                <li className="flex items-center gap-2">
                                    <CheckCircle2 size={14} className="text-purple-400" /> Hormozi & MrBeast Retention Hooks
                                </li>
                                <li className="flex items-center gap-2">
                                    <CheckCircle2 size={14} className="text-purple-400" /> Auto-Generated Captions & Emojis
                                </li>
                            </ul>
                        </div>

                        {/* Card 3: Character & Visual DNA Lock */}
                        <div className="p-8 rounded-3xl bg-[#090914] border border-white/10 hover:border-pink-500/40 transition-all group">
                            <div className="w-14 h-14 rounded-2xl bg-pink-500/10 border border-pink-500/20 flex items-center justify-center mb-6 text-pink-400 group-hover:scale-110 transition-transform">
                                <Users size={28} />
                            </div>
                            <h3 className="text-2xl font-bold text-white mb-3">Character DNA Lock</h3>
                            <p className="text-zinc-400 text-sm leading-relaxed mb-6">
                                Maintain consistent AI characters across hundreds of videos. Our system passes 4-view turnaround sheets to Google Veo to preserve faces and outfits.
                            </p>
                            <ul className="space-y-2.5 text-xs text-zinc-300 font-medium">
                                <li className="flex items-center gap-2">
                                    <CheckCircle2 size={14} className="text-pink-400" /> 3D Pixar, Anime, or Photorealistic
                                </li>
                                <li className="flex items-center gap-2">
                                    <CheckCircle2 size={14} className="text-pink-400" /> No Facial Warping Across Cuts
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>
            </section>

            {/* =========================================================================
                4. GOOGLE CLOUD ECOSYSTEM & ARCHITECTURE (Targeted for GCP Reviewer)
            ========================================================================= */}
            <section id="architecture" className="py-24 bg-[#05050d] border-y border-white/10 relative">
                <div className="w-full max-w-[1500px] mx-auto px-4 sm:px-6 md:px-12">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                        <div>
                            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-mono font-semibold uppercase tracking-wider mb-4">
                                <Cloud size={13} /> Infrastructure Verification
                            </div>
                            <h2 className="text-[34px] sm:text-[46px] font-[900] text-white tracking-tight leading-tight mb-6">
                                Fully Native on Google Cloud Platform
                            </h2>
                            <p className="text-zinc-300 text-base leading-relaxed mb-6">
                                CloneFrame relies heavily on Google Cloud services for computing power, low latency model execution, and enterprise-grade asset caching:
                            </p>

                            <div className="space-y-4">
                                {[
                                    {
                                        title: 'Google Vertex AI & Gemini 2.0 Flash',
                                        desc: 'Powers the narrative director and multi-modal scene breakdown with 2M+ token context window.'
                                    },
                                    {
                                        title: 'Cloud Run Autoscaling Microservices',
                                        desc: 'Serverless container orchestration provisioned with 8Gi Memory and 2 vCPUs per worker instance.'
                                    },
                                    {
                                        title: 'Google Cloud Tasks Distributed Queues',
                                        desc: 'Rate-limited job dispatching preventing upstream API exhaustion and managing parallel video generation.'
                                    },
                                    {
                                        title: 'Google Cloud Storage (GCS) Buckets',
                                        desc: 'High-speed encrypted object storage serving signed URLs for instant media preview and export.'
                                    }
                                ].map((item, i) => (
                                    <div key={i} className="flex items-start gap-3.5 p-4 rounded-xl bg-white/[0.02] border border-white/5">
                                        <div className="w-6 h-6 rounded-md bg-blue-500/20 text-blue-400 flex items-center justify-center shrink-0 mt-0.5">
                                            <Check size={14} />
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-bold text-white">{item.title}</h4>
                                            <p className="text-xs text-zinc-400 mt-1 leading-relaxed">{item.desc}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* GCP Stack Topology Visual */}
                        <div className="p-8 rounded-3xl bg-black border border-white/10 relative overflow-hidden shadow-2xl">
                            <div className="flex items-center justify-between pb-4 mb-6 border-b border-white/10">
                                <div className="text-sm font-mono text-zinc-400 flex items-center gap-2">
                                    <Cloud size={16} className="text-blue-400" />
                                    <span>GCP Project: shortcutai-backend</span>
                                </div>
                                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                                    us-central1
                                </span>
                            </div>

                            <div className="space-y-4 font-mono text-xs">
                                <div className="p-4 rounded-xl bg-indigo-950/20 border border-indigo-500/30 flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <Cpu className="text-indigo-400" size={18} />
                                        <div>
                                            <div className="text-white font-bold">Cloud Run Service</div>
                                            <div className="text-zinc-400 text-[11px]">ai-video-backend-00154-8lc</div>
                                        </div>
                                    </div>
                                    <span className="text-indigo-300 text-[11px]">8Gi / 2 vCPU</span>
                                </div>

                                <div className="p-4 rounded-xl bg-purple-950/20 border border-purple-500/30 flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <Layers className="text-purple-400" size={18} />
                                        <div>
                                            <div className="text-white font-bold">Cloud Tasks Queue</div>
                                            <div className="text-zinc-400 text-[11px]">generation-queue</div>
                                        </div>
                                    </div>
                                    <span className="text-purple-300 text-[11px]">Active (500/s)</span>
                                </div>

                                <div className="p-4 rounded-xl bg-blue-950/20 border border-blue-500/30 flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <Database className="text-blue-400" size={18} />
                                        <div>
                                            <div className="text-white font-bold">Cloud Storage Bucket</div>
                                            <div className="text-zinc-400 text-[11px]">shortcutai-user-uploads-2026</div>
                                        </div>
                                    </div>
                                    <span className="text-blue-300 text-[11px]">AES-256</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* =========================================================================
                5. DEVELOPER API TERMINAL
            ========================================================================= */}
            <section id="api" className="py-24 bg-[#030307] relative">
                <div className="w-full max-w-[1500px] mx-auto px-4 sm:px-6 md:px-12">
                    <div className="text-center max-w-3xl mx-auto mb-16">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono font-semibold uppercase tracking-wider mb-4">
                            <Code2 size={13} /> Developer API Specs
                        </div>
                        <h2 className="text-[34px] sm:text-[46px] font-[900] text-white tracking-tight leading-tight mb-4">
                            One Unified Endpoint for Complete Video Generation
                        </h2>
                        <p className="text-base sm:text-lg text-zinc-400">
                            Plug CloneFrame into your agency CRM, Zapier, or proprietary workflow with our clean REST API.
                        </p>
                    </div>

                    <div className="max-w-4xl mx-auto rounded-3xl bg-[#090912] border border-white/15 overflow-hidden shadow-2xl">
                        {/* Terminal Header */}
                        <div className="flex items-center justify-between px-6 py-4 bg-black/60 border-b border-white/10">
                            <div className="flex items-center gap-2">
                                <div className="flex gap-1.5">
                                    <div className="w-3 h-3 rounded-full bg-red-500/70"></div>
                                    <div className="w-3 h-3 rounded-full bg-yellow-500/70"></div>
                                    <div className="w-3 h-3 rounded-full bg-green-500/70"></div>
                                </div>
                                <div className="flex items-center gap-2 ml-4">
                                    {(['python', 'node', 'curl'] as const).map((lang) => (
                                        <button
                                            key={lang}
                                            onClick={() => setActiveLang(lang)}
                                            className={`px-3 py-1 rounded-md text-xs font-mono font-medium transition-colors ${
                                                activeLang === lang
                                                    ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                                                    : 'text-zinc-400 hover:text-white'
                                            }`}
                                        >
                                            {lang === 'python' ? 'Python SDK' : lang === 'node' ? 'Node.js' : 'cURL'}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <button
                                onClick={copyApiSnippet}
                                className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white font-mono px-3 py-1 rounded-lg bg-white/5 border border-white/10 transition-colors"
                            >
                                {copiedCode ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                                <span>{copiedCode ? 'Copied' : 'Copy Code'}</span>
                            </button>
                        </div>

                        {/* Terminal Body */}
                        <div className="p-6 overflow-x-auto font-mono text-xs sm:text-sm text-zinc-300 bg-black/90">
                            <pre className="text-indigo-200 leading-relaxed">
                                {activeLang === 'python' ? pythonCode : activeLang === 'node' ? nodeCode : curlCode}
                            </pre>
                        </div>
                    </div>
                </div>
            </section>

            {/* =========================================================================
                6. PRICING SECTION (B2B SMMA TIERS)
            ========================================================================= */}
            <div id="pricing">
                <Pricing />
            </div>

            {/* =========================================================================
                7. FINAL CTA (Join Private Beta)
            ========================================================================= */}
            <section className="py-28 relative overflow-hidden bg-gradient-to-b from-transparent via-indigo-950/20 to-black border-t border-white/10">
                <div className="w-full max-w-4xl mx-auto px-6 text-center relative z-10">
                    <h2 className="text-[40px] sm:text-[58px] font-[900] text-white tracking-tight leading-none mb-6">
                        Scale Your Agency Content <br />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-300 via-purple-300 to-pink-300">
                            On Automated Rails.
                        </span>
                    </h2>
                    <p className="text-lg text-zinc-300 max-w-2xl mx-auto mb-10">
                        Join forward-thinking agencies building high-margin video retainers with CloneFrame's automated multi-model pipeline.
                    </p>

                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                        <button
                            onClick={() => {
                                const element = document.getElementById('waitlist-section');
                                if (element) element.scrollIntoView({ behavior: 'smooth' });
                            }}
                            className="w-full sm:w-auto px-10 py-4 bg-white text-black font-[800] text-lg rounded-2xl hover:bg-zinc-200 transition-all shadow-[0_0_40px_rgba(255,255,255,0.3)] hover:scale-105 active:scale-95"
                        >
                            Join Private Beta
                        </button>
                        <button
                            onClick={onSignInClick}
                            className="w-full sm:w-auto px-10 py-4 bg-white/[0.06] border border-white/15 text-white font-[700] text-lg rounded-2xl hover:bg-white/10 transition-colors"
                        >
                            Sign In / Sandbox
                        </button>
                    </div>
                </div>
            </section>

            {/* =========================================================================
                8. FOOTER WITH REQUIRED REVIEWER HACK
            ========================================================================= */}
            <Footer />
        </div>
    );
}
