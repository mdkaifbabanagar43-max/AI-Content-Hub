'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Sparkles, Smartphone, MonitorPlay, Zap, Clock,
    Ghost, Laugh, Brain, Rocket, CheckCircle2,
    Loader2, Download, Play, Terminal, ArrowRight, ArrowLeft,
    Edit2, RefreshCw, Volume2, Image as ImageIcon, Wand2, Mic, Lock, Globe, Sliders, Bookmark, Check
} from 'lucide-react';
import { Skeleton } from './ui/Skeleton';
import { LoadingState } from './ui/LoadingState';
import { cn } from '@/lib/utils';
import { useAuth } from '@/context/AuthContext';
import { API_BASE_URL } from '@/lib/config';
import { forceDownload } from '@/lib/download';
import { handleAppError } from '@/lib/errorHandler';
import { LANGUAGES, Voice } from '@/lib/voices'; // Import new voice DB
import { usePlan } from '@/context/PlanContext';

// --- CONFIG CONSTANTS ---
const PLATFORMS = [
    { id: 'tiktok', label: 'TikTok / Reels', icon: Smartphone, desc: '9:16 Vertical • Fast' },
    { id: 'youtube', label: 'YouTube Shorts', icon: MonitorPlay, desc: '9:16 Vertical • Cinematic' },
];

const MOODS = {
    scary: { color: 'text-purple-400', border: 'border-purple-500/50', icon: Ghost },
    fast: { color: 'text-yellow-400', border: 'border-yellow-500/50', icon: Zap },
    informative: { color: 'text-blue-400', border: 'border-blue-500/50', icon: Brain },
    motivational: { color: 'text-red-400', border: 'border-red-500/50', icon: Rocket },
    funny: { color: 'text-orange-400', border: 'border-orange-500/50', icon: Laugh },
};

export default function IdeaStudio() {
    // --- STATE MANAGEMENT ---
    const { user } = useAuth();
    const { deductCredits, refundCredits, userPlan } = usePlan();

    // Wizard State
    const [step, setStep] = useState(1);
    const [isLoading, setIsLoading] = useState(false);

    // Data State
    const [topic, setTopic] = useState('');
    const [platform, setPlatform] = useState(PLATFORMS[0].id);
    const [duration, setDuration] = useState("30s");
    const [quality, setQuality] = useState("720p");
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);

    // Audio Identity State
    const [languageId, setLanguageId] = useState('en-US'); // Default US English
    const [voiceId, setVoiceId] = useState<string>('');

    // Derived State for Voice Selection
    const currentLang = LANGUAGES.find(l => l.id === languageId) || LANGUAGES[0];

    // Auto-select first voice when language changes
    useEffect(() => {
        if (currentLang && currentLang.voices.length > 0) {
            const isValid = currentLang.voices.find(v => v.id === voiceId);
            if (!isValid) {
                setVoiceId(currentLang.voices[0].id);
            }
        }
    }, [languageId, currentLang]);


    const [ideas, setIdeas] = useState<any[]>([]);
    const [selectedIdea, setSelectedIdea] = useState<any>(null);

    const [previewAssets, setPreviewAssets] = useState<any>(null);
    const [editedScript, setEditedScript] = useState('');

    // --- SCRIPT REVIEW STATE (New Step 2.5) ---
    const [isReviewingScript, setIsReviewingScript] = useState(false);
    const [reviewScript, setReviewScript] = useState('');

    const [logs, setLogs] = useState<string[]>([]);
    const [finalVideoUrl, setFinalVideoUrl] = useState<string | null>(null);

    // --- STEPS LOGIC ---

    // STEP 1 -> 2: BRAINSTORM
    const handleBrainstorm = async () => {
        if (!topic || !user) return;
        setIsLoading(true);
        try {
            const token = await user.getIdToken();
            const res = await fetch(`${API_BASE_URL}/brainstorm`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    topic,
                    language: currentLang.label // Pass label for clearer LLM instructions
                })
            });
            const data = await res.json();
            setIdeas(data);
            setStep(2);
        } catch (e) {
            alert("Brainstorming failed. Check backend.");
        } finally {
            setIsLoading(false);
        }
    };

    // STEP 2 -> 2.5: GENERATE SCRIPT PREVIEW
    const previewScript = async (idea: any) => {
        setIsLoading(true);
        if (!user) return;
        try {
            setSelectedIdea(idea);
            const token = await user.getIdToken();
            const res = await fetch(`${API_BASE_URL}/generate-script-preview`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    title: idea.title,
                    hook: idea.hook,
                    mood: idea.mood || 'informative',
                    voice_name: voiceId,
                    platform: platform,
                    duration: duration,
                    language: currentLang.label
                })
            });
            const data = await res.json();
            if (!data) throw new Error("Empty response");

            setReviewScript(data.script || data.voiceover || "");
            setIsReviewingScript(true);
        } catch (e) {
            console.error(e);
            alert("Script Preview failed");
        } finally {
            setIsLoading(false);
        }
    };

    // STEP 2.5 -> 3: CONFIRM SCRIPT & GENERATE ASSETS
    const generateScriptAndVisuals = async (finalScript: string) => {
        setIsLoading(true);
        setIsReviewingScript(false); // Close Modal

        if (!user || !selectedIdea) return;
        try {
            const token = await user.getIdToken();
            const res = await fetch(`${API_BASE_URL}/produce-video-assets`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    title: selectedIdea.title,
                    hook: selectedIdea.hook,
                    mood: selectedIdea.mood || 'informative',
                    voice_name: voiceId,
                    platform: platform,
                    duration: duration,
                    language: currentLang.label,
                    script: finalScript // PASS EDITED SCRIPT
                })
            });
            const data = await res.json();
            if (!data) throw new Error("Empty response from backend");

            setPreviewAssets({
                script: data.voiceover || data.script || "",
                audio_base64: data.audio_base64 || null,
                visual_plan: data.visual_plan || [],
                visual_terms: data.visual_plan || []
            });
            setEditedScript(data.voiceover || data.script || "");
            setStep(3);
        } catch (e) {
            console.error(e);
            alert("Generation failed. Check backend.");
            setIsReviewingScript(true); // Re-open modal on failure
        } finally {
            setIsLoading(false);
        }
    };

    // STEP 3 -> 4: RENDER FINAL
    const [renderStage, setRenderStage] = useState(0);
    const handleRender = async () => {
        if (!previewAssets || !user) return;

        const cost = 5;
        if (!deductCredits(cost)) return;

        setStep(4);
        setRenderStage(0);

        const progressInterval = setInterval(() => {
            setRenderStage(prev => (prev < 3 ? prev + 1 : prev));
        }, 4000);

        const handleBeforeUnload = (e: BeforeUnloadEvent) => {
            e.preventDefault();
            e.returnValue = '';
        };
        window.addEventListener('beforeunload', handleBeforeUnload);

        try {
            const token = await user.getIdToken();
            const res = await fetch(`${API_BASE_URL}/render-final`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    script: editedScript,
                    audio_base64: previewAssets.audio_base64,
                    visual_plan: previewAssets.visual_plan,
                    user_id: user.uid,
                    topic: selectedIdea.title,
                    mood: selectedIdea.mood,
                    platform: platform
                })
            });
            const data = await res.json();

            clearInterval(progressInterval);
            window.removeEventListener('beforeunload', handleBeforeUnload);

            if (!res.ok) throw new Error(data.detail || "Generation failed");

            if (data.video_url) {
                setRenderStage(4);
                setTimeout(() => {
                    setFinalVideoUrl(data.video_url);
                    setStep(5);
                }, 1000);
            } else {
                throw new Error("No URL returned");
            }
        } catch (e) {
            clearInterval(progressInterval);
            window.removeEventListener('beforeunload', handleBeforeUnload);
            setLogs(prev => [...prev, "❌ RENDER FAILED."]);
            setStep(3);
            handleAppError(e, () => refundCredits(cost));
        }
    };

    const handleSaveProject = async () => {
        if (!user || !finalVideoUrl) return;
        try {
            const token = await user.getIdToken();
            const res = await fetch(`${API_BASE_URL}/save-project`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    user_id: user.uid,
                    topic: selectedIdea.title,
                    video_url: finalVideoUrl,
                    script: editedScript,
                    platform: platform,
                    mood: selectedIdea.mood
                })
            });

            if (res.ok) {
                alert("Saved to Library! 💾");
            } else {
                throw new Error("Save failed");
            }
        } catch (e) {
            alert("Failed to save project.");
            console.error(e);
        }
    };

    const handleDownload = async () => {
        if (!finalVideoUrl) return;
        alert("Downloading started... ⬇️");
        await forceDownload(finalVideoUrl, `ai-studio-${Date.now()}.mp4`);
    };

    // --- RENDERERS ---

    // STEP 1: STUDIO INPUT (Spacious "Hero" Layout)
    const renderStep1 = () => (
        <div className="max-w-[1200px] mx-auto min-h-[80vh] p-6 relative z-10 flex flex-col items-center justify-start pt-4 md:pt-10">

            {/* 1. Header & Hero Input */}
            <div className="w-full text-center space-y-6 mb-10 animate-in slide-in-from-bottom duration-700 fade-in">
                <div className="space-y-4">
                    <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full bg-zinc-900/80 border border-zinc-800 text-xs font-bold tracking-widest text-purple-400 uppercase shadow-xl backdrop-blur-md">
                        <Sparkles size={12} /> IdeaStudio v2.1
                    </div>
                    <h1 className="text-5xl md:text-7xl font-black text-white tracking-tighter leading-tight drop-shadow-2xl">
                        Create <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-pink-500 to-red-500">Viral</span> Videos
                    </h1>
                </div>

                {/* Big Search Bar */}
                <div className="max-w-4xl mx-auto relative group">
                    <div className="absolute inset-0 bg-gradient-to-r from-purple-600/30 to-pink-600/30 rounded-3xl blur-2xl group-focus-within:opacity-100 opacity-40 transition-opacity duration-700"></div>
                    <div className="relative bg-black/60 backdrop-blur-xl border border-zinc-800 rounded-3xl p-3 shadow-2xl flex items-center gap-4 transition-all group-focus-within:border-purple-500/50 group-focus-within:bg-black/80">
                        <div className="pl-6 text-zinc-500 group-focus-within:text-purple-400 transition-colors">
                            <Wand2 size={32} />
                        </div>
                        <input
                            value={topic}
                            onChange={(e) => setTopic(e.target.value)}
                            placeholder="What do you want to create? (e.g., 'Facts about Mars')"
                            className="flex-1 bg-transparent border-none text-2xl md:text-3xl font-medium text-white py-4 md:py-6 placeholder-zinc-700 focus:ring-0 focus:outline-none"
                            onKeyDown={(e) => e.key === 'Enter' && handleBrainstorm()}
                            autoFocus
                        />
                        <div className="pr-2">
                            <button
                                onClick={handleBrainstorm}
                                disabled={!topic || isLoading}
                                className="h-14 md:h-16 px-6 md:px-8 rounded-2xl bg-white hover:bg-zinc-200 text-black font-bold text-lg flex items-center gap-2 shadow-lg hover:shadow-purple-500/20 transition-all disabled:opacity-50 disabled:grayscale transform hover:scale-105 active:scale-95"
                            >
                                {isLoading ? <Loader2 className="animate-spin" /> : <span className="hidden md:inline">GENERATE</span>}
                                {!isLoading && <ArrowRight size={24} />}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* 2. Configuration Cards (Spacious Grid) */}
            <div className="w-full max-w-5xl grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8 mb-12 animate-in slide-in-from-bottom duration-700 delay-100 fade-in">

                {/* Visual Settings */}
                <div className="bg-zinc-900/30 border border-zinc-800/50 rounded-3xl p-6 md:p-8 hover:bg-zinc-900/50 transition-colors">
                    <h3 className="text-xs font-bold text-zinc-500 uppercase flex items-center gap-2 mb-6 tracking-widest">
                        <Sliders size={14} /> Format & Style
                    </h3>

                    <div className="space-y-6">
                        {/* Platform */}
                        <div className="space-y-3">
                            <label className="text-xs font-bold text-zinc-500 uppercase">Platform</label>
                            <div className="grid grid-cols-2 gap-3">
                                {PLATFORMS.map(p => (
                                    <button
                                        key={p.id}
                                        onClick={() => setPlatform(p.id)}
                                        className={cn(
                                            "flex flex-col items-center gap-2 py-4 px-2 rounded-2xl border transition-all hover:scale-[1.02]",
                                            platform === p.id
                                                ? "bg-purple-500/10 border-purple-500 text-purple-400"
                                                : "bg-black/50 border-zinc-800 text-zinc-500 hover:bg-zinc-800"
                                        )}
                                    >
                                        <p.icon size={24} />
                                        <span className="text-sm font-bold">{p.label}</span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Duration & Quality */}
                        <div className="grid grid-cols-2 gap-6">
                            <div className="space-y-3">
                                <label className="text-xs font-bold text-zinc-500 uppercase">Duration</label>
                                <div className="flex bg-black/50 rounded-xl p-1.5 border border-zinc-800">
                                    {['30s', '60s'].map(d => (
                                        <button
                                            key={d}
                                            onClick={() => setDuration(d)}
                                            className={cn("flex-1 py-2 rounded-lg text-xs font-bold transition-all", duration === d ? "bg-zinc-800 text-white shadow" : "text-zinc-500 hover:text-zinc-300")}
                                        >
                                            {d}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            <div className="space-y-3">
                                <label className="text-xs font-bold text-zinc-500 uppercase">Quality</label>
                                <div className="flex bg-black/50 rounded-xl p-1.5 border border-zinc-800">
                                    {['720p', '1080p', '4k'].map(q => {
                                        // Cap Check
                                        const { capabilities, userPlan } = usePlan();

                                        // Logic:
                                        // 1080p -> Locked if max < 1080p (Starter)
                                        // 4k -> Locked if max < 4k (Starter, Creator)

                                        const maxRes = capabilities?.max_resolution || '720p';
                                        let isLocked = false;

                                        // Robust check for mixed types (str/int)
                                        const is720Cap = maxRes === '720p' || maxRes == 720;
                                        const is1080Cap = maxRes === '1080p' || maxRes == 1080;
                                        // If cap is 720, lock 1080 and 4k
                                        if (q === '1080p' && is720Cap) isLocked = true;

                                        // If cap is NOT 4k/2160, lock 4k
                                        const is4kCap = maxRes === '4k' || maxRes === '2160p' || maxRes == 2160 || maxRes >= 2160;
                                        if (q === '4k' && !is4kCap) isLocked = true;

                                        // Fallback logic if capabilities missing
                                        const isLockedFallback = (q === '1080p' && !['creator', 'agency', 'pro'].includes(userPlan)) ||
                                            (q === '4k' && userPlan !== 'agency');

                                        const finalLocked = capabilities ? isLocked : isLockedFallback;

                                        return (
                                            <button
                                                key={q}
                                                onClick={() => {
                                                    if (finalLocked) {
                                                        // Use specific upgrade modal or alert
                                                        // For 4k, we ideally want to say "Upgrade to Agency"
                                                        setShowUpgradeModal(true);
                                                    } else {
                                                        setQuality(q);
                                                    }
                                                }}
                                                className={cn(
                                                    "flex-1 py-2 rounded-lg text-xs font-bold transition-all relative",
                                                    quality === q
                                                        ? "bg-zinc-800 text-white shadow"
                                                        : finalLocked
                                                            ? "text-zinc-600 cursor-not-allowed" // Visually muted
                                                            : "text-zinc-500 hover:text-zinc-300"
                                                )}
                                                title={finalLocked ? "Upgrade to Creator Plan" : ""}
                                            >
                                                <span className="flex items-center justify-center gap-1">
                                                    {q}
                                                    {finalLocked && <Lock size={10} />}
                                                </span>
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Audio Identity */}
                <div className="bg-zinc-900/30 border border-zinc-800/50 rounded-3xl p-6 md:p-8 hover:bg-zinc-900/50 transition-colors">
                    <h3 className="text-xs font-bold text-zinc-500 uppercase flex items-center gap-2 mb-6 tracking-widest">
                        <Mic size={14} /> Audio Identity
                    </h3>

                    <div className="space-y-6">
                        {/* Language Grid */}
                        <div className="space-y-3">
                            <label className="text-xs font-bold text-zinc-500 uppercase">Language</label>
                            <div className="grid grid-cols-5 gap-3">
                                {LANGUAGES.slice(0, 5).map(lang => ( // Show top 5
                                    <button key={lang.id} onClick={() => setLanguageId(lang.id)} className={cn("flex flex-col items-center justify-center h-14 rounded-xl border transition-all", languageId === lang.id ? "bg-purple-500/20 border-purple-500 text-white" : "bg-black/50 border-zinc-800 text-zinc-500 hover:border-zinc-700")}>
                                        <span className="text-xl">{lang.flag}</span>
                                    </button>
                                ))}
                            </div>
                            {/* Dark Dropdown */}
                            <div className="relative">
                                <select
                                    value={languageId}
                                    onChange={(e) => setLanguageId(e.target.value)}
                                    className="w-full bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs px-3 py-3 rounded-xl focus:border-purple-500 outline-none hover:bg-zinc-800 transition-colors cursor-pointer"
                                >
                                    {LANGUAGES.map(l => (
                                        <option key={l.id} value={l.id} className="bg-zinc-900 text-zinc-300 py-2">
                                            {l.flag} {l.label}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        {/* Persona List */}
                        <div className="space-y-3">
                            <label className="text-xs font-bold text-zinc-500 uppercase">Voice Persona</label>
                            <div className="grid grid-cols-1 gap-2 max-h-[140px] overflow-y-auto pr-2 custom-scrollbar">
                                {currentLang.voices.map(voice => (
                                    <button
                                        key={voice.id}
                                        onClick={() => setVoiceId(voice.id)}
                                        className={cn(
                                            "flex items-center gap-4 p-3 rounded-xl border text-left transition-all group hover:scale-[1.01]",
                                            voiceId === voice.id
                                                ? "bg-purple-500/10 border-purple-500/50 ring-1 ring-purple-500/30 text-white"
                                                : "bg-black/50 border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-800"
                                        )}
                                    >
                                        <div className={cn(
                                            "w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 transition-colors",
                                            voiceId === voice.id ? "bg-purple-500 text-white" : "bg-zinc-800 text-zinc-600"
                                        )}>
                                            {voice.gender === 'Male' ? 'M' : 'F'}
                                        </div>
                                        <span className={cn("text-sm font-bold flex-1", voiceId === voice.id ? "text-white" : "text-zinc-400")}>{voice.label.split('(')[0]}</span>
                                        {voiceId === voice.id && <Check size={14} className="text-purple-400" />}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

        </div>
    );

    // STEP 2: CONCEPT SELECTION (Polished)
    const renderStep2 = () => (
        <div className="space-y-10 max-w-6xl mx-auto pb-20 relative pt-10">
            <header className="flex items-center justify-between border-b border-zinc-800 pb-6">
                <div>
                    <h2 className="text-4xl font-black text-white mb-2 tracking-tight">Choose your <span className="text-purple-400">Angle</span></h2>
                    <p className="text-zinc-500">Our AI generated {ideas.length} viral concepts for "{topic}"</p>
                </div>
                <button onClick={() => setStep(1)} className="px-4 py-2 rounded-lg hover:bg-zinc-800 text-zinc-400 text-sm transition-colors flex items-center gap-2">
                    <ArrowLeft size={16} /> Back to Search
                </button>
            </header>

            {isLoading ? (
                <LoadingState
                    steps={[
                        "Analyzing topic trends...",
                        "Identifying viral angles...",
                        "Drafting scroll-stopping hooks...",
                        "Applying engagement psychology..."
                    ]}
                    layout={
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {[1, 2, 3].map((i) => (
                                <div key={i} className="h-[400px] bg-zinc-900/40 border border-zinc-800 rounded-3xl p-8 flex flex-col justify-between">
                                    <div className="flex justify-between items-start mb-6">
                                        <Skeleton className="w-10 h-10 rounded-2xl" />
                                        <Skeleton className="w-16 h-6 rounded-md" />
                                    </div>
                                    <div className="space-y-4">
                                        <Skeleton className="h-8 w-3/4" />
                                        <Skeleton className="h-8 w-1/2" />
                                        <Skeleton className="h-1 w-12 mt-4" />
                                    </div>
                                    <div className="space-y-2 mt-8">
                                        <Skeleton className="h-4 w-full" />
                                        <Skeleton className="h-4 w-full" />
                                        <Skeleton className="h-4 w-2/3" />
                                    </div>
                                    <div className="flex justify-end mt-4">
                                        <Skeleton className="h-4 w-24" />
                                    </div>
                                </div>
                            ))}
                        </div>
                    }
                />
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {ideas.map((idea, idx) => {
                        const MoodIcon = MOODS[idea.mood as keyof typeof MOODS]?.icon || Zap;
                        const moodStyle = MOODS[idea.mood as keyof typeof MOODS] || MOODS.fast;

                        return (
                            <motion.button
                                key={idea.id}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: idx * 0.1 }}
                                whileHover={{ scale: 1.02, y: -5 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={() => {
                                    previewScript(idea);
                                }}
                                className="group relative h-[400px] perspective-1000 text-left w-full focus:outline-none"
                            >
                                <div className="absolute inset-0 bg-gradient-to-br from-zinc-900 to-black border border-zinc-800 rounded-3xl p-8 flex flex-col justify-between transition-all group-hover:border-purple-500/50 group-hover:shadow-[0_0_40px_rgba(168,85,247,0.15)] overflow-hidden">
                                    <div className={`absolute -right-10 -top-10 w-40 h-40 bg-${moodStyle.color.split('-')[1]}-500/10 rounded-full blur-3xl group-hover:bg-${moodStyle.color.split('-')[1]}-500/20 transition-all`} />

                                    <div>
                                        <div className="flex justify-between items-start mb-6">
                                            <div className={`p-3 rounded-2xl bg-zinc-950 border border-zinc-800 ${moodStyle.color} group-hover:scale-110 transition-transform duration-300 shadow-lg`}>
                                                <MoodIcon size={24} />
                                            </div>
                                            <span className={`text-[10px] font-bold tracking-wider uppercase px-2 py-1 rounded bg-zinc-950 border border-zinc-800 text-zinc-500`}>
                                                {idea.mood}
                                            </span>
                                        </div>

                                        <h3 className="text-2xl font-bold text-white leading-tight mb-4 group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-white group-hover:to-zinc-400 transition-all">
                                            {idea.title}
                                        </h3>

                                        <div className="w-12 h-1 bg-zinc-800 rounded-full mb-4 group-hover:bg-purple-500 transition-colors" />
                                    </div>

                                    <div className="relative">
                                        <p className="text-zinc-400 text-sm leading-relaxed line-clamp-4 italic border-l-2 border-zinc-800 pl-4">
                                            "{idea.hook}"
                                        </p>
                                    </div>

                                    <div className="absolute bottom-6 right-8 opacity-0 group-hover:opacity-100 transition-all translate-x-4 group-hover:translate-x-0 flex items-center gap-2 text-purple-400 font-bold text-sm">
                                        SELECT ANGLE <ArrowRight size={16} />
                                    </div>
                                </div>
                            </motion.button>
                        );
                    })}
                </div>
            )}
        </div>
    );

    // STEP 3: DIRECTOR'S STUDIO (Same Logic, Better Spacing)
    const renderStep3 = () => (
        <div className="flex flex-col h-[calc(100vh-140px)] max-w-[1600px] mx-auto space-y-6 pt-6">
            <div className="flex items-center justify-between shrink-0 mb-2">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-500/10 rounded-lg text-purple-400 border border-purple-500/20">
                        <Edit2 size={24} />
                    </div>
                    <div>
                        <h2 className="text-2xl font-bold text-white">Director's Studio</h2>
                        <p className="text-zinc-500 text-sm">Fine-tune your viral script and assets</p>
                    </div>
                </div>
                <button onClick={() => setStep(2)} className="flex items-center gap-2 px-4 py-2 rounded-lg hover:bg-zinc-800 text-zinc-400 text-sm transition-colors border border-transparent hover:border-zinc-700">
                    <ArrowLeft size={16} /> Choose Different Concept
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 h-full min-h-0 pb-6">
                <div className="lg:col-span-7 flex flex-col bg-zinc-900/40 border border-zinc-800 rounded-3xl overflow-hidden backdrop-blur-sm shadow-2xl">
                    <div className="bg-black/40 border-b border-zinc-800 px-6 py-4 flex items-center justify-between">
                        <div className="flex items-center gap-2 text-zinc-500">
                            <Terminal size={14} />
                            <span className="text-xs font-mono uppercase tracking-widest">Script_Editor_v2</span>
                        </div>
                    </div>
                    <textarea
                        value={editedScript}
                        onChange={(e) => setEditedScript(e.target.value)}
                        className="flex-1 w-full bg-transparent p-8 text-xl text-zinc-300 font-mono leading-relaxed focus:outline-none resize-none custom-scrollbar selection:bg-purple-500/30"
                        placeholder="AI generating script..."
                    />
                </div>

                <div className="lg:col-span-5 flex flex-col gap-6">
                    <div className="bg-zinc-900/60 border border-zinc-800 rounded-3xl p-6 shadow-xl relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-32 bg-purple-500/5 rounded-full blur-3xl -translate-y-10 translate-x-10 pointer-events-none"></div>
                        <h3 className="text-xs font-bold text-zinc-500 uppercase flex items-center gap-2 mb-4 tracking-widest">
                            <Volume2 size={14} className="text-purple-400" /> Audio Synthesis
                        </h3>
                        <div className="bg-black/50 rounded-xl p-4 border border-zinc-800/50 backdrop-blur-md">
                            <audio controls src={`data:audio/mp3;base64,${previewAssets?.audio_base64}`} className="w-full h-10 opacity-80 hover:opacity-100 transition-opacity" />
                        </div>
                    </div>

                    <div className="flex-1 bg-zinc-900/60 border border-zinc-800 rounded-3xl p-6 shadow-xl relative overflow-hidden flex flex-col">
                        <h3 className="text-xs font-bold text-zinc-500 uppercase flex items-center gap-2 mb-4 tracking-widest">
                            <ImageIcon size={14} className="text-purple-400" /> Visual Strategy
                        </h3>
                        <div className="flex-1 bg-black/50 rounded-xl p-6 border-l-2 border-purple-500 italic text-zinc-400 leading-relaxed overflow-y-auto custom-scrollbar font-serif text-lg">
                            {previewAssets?.thumbnail_desc || "AI is devising a visual plan..."}
                        </div>
                    </div>

                    <button
                        onClick={() => {
                            if (userPlan === 'free') {
                                setShowUpgradeModal(true);
                            } else {
                                handleRender();
                            }
                        }}
                        className={cn(
                            "w-full py-8 text-black rounded-3xl shadow-[0_0_40px_rgba(255,255,255,0.1)] hover:shadow-[0_0_60px_rgba(255,255,255,0.2)] transform transition-all active:scale-[0.98] flex items-center justify-center gap-4 group relative overflow-hidden",
                            userPlan === 'free' ? "bg-zinc-800 text-zinc-400 hover:bg-zinc-700" : "bg-white hover:bg-zinc-200"
                        )}
                    >
                        {userPlan === 'free' ? (
                            <>
                                <Lock size={24} className="text-purple-400" />
                                <span className="text-2xl font-black tracking-tight uppercase">Upgrade to Render</span>
                            </>
                        ) : (
                            <>
                                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/50 to-transparent -translate-x-full group-hover:animate-shimmer" />
                                <span className="text-2xl font-black tracking-tight">RENDER MASTERPIECE</span>
                                <ArrowRight strokeWidth={4} className="group-hover:translate-x-1 transition-transform" />
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );

    // STEP 4: RENDERING (Same)
    const renderStep4 = () => {
        const stages = [
            { id: 1, label: "Quantum Initialization", desc: "Spinning up GPU clusters..." },
            { id: 2, label: "Visual Synthesis", desc: "Generating and editing video assets..." },
            { id: 3, label: "Aural Formatting", desc: "Syncing voiceover and mastering audio..." },
            { id: 4, label: "Final Polish", desc: "Applying color grading and viral metadata..." }
        ];

        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] w-full max-w-4xl mx-auto relative px-4">
                <div className="absolute inset-0 bg-purple-500/5 blur-3xl rounded-full animate-pulse pointer-events-none"></div>
                <div className="w-full bg-zinc-950/80 backdrop-blur-xl rounded-3xl border border-zinc-800 p-8 md:p-12 shadow-2xl relative overflow-hidden flex flex-col gap-8">
                    <div className="text-center space-y-2 mb-4">
                        <div className="flex justify-center mb-4">
                            <div className="relative w-24 h-24">
                                <svg className="w-full h-full rotate-[-90deg]" viewBox="0 0 36 36">
                                    <path className="text-zinc-800" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="2" />
                                    <motion.path className="text-purple-500" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray={`${((renderStage + 1) / 4) * 100}, 100`} initial={{ strokeDasharray: "0, 100" }} animate={{ strokeDasharray: `${((renderStage + 1) / 4) * 100}, 100` }} transition={{ duration: 0.5 }} />
                                </svg>
                                <div className="absolute inset-0 flex items-center justify-center text-sm font-mono font-bold text-white">{(renderStage + 1) * 25}%</div>
                            </div>
                        </div>
                        <h2 className="text-3xl font-black text-white tracking-tight">Constructing Masterpiece</h2>
                        <p className="text-zinc-500">Antigravity Engine is processing your request</p>
                    </div>

                    <div className="space-y-6 max-w-lg mx-auto w-full">
                        {stages.map((stage, idx) => {
                            const isActive = renderStage >= idx;
                            return (
                                <div key={stage.id} className="relative flex items-center gap-4 group">
                                    {idx !== stages.length - 1 && <div className={`absolute left-[19px] top-10 w-[2px] h-8 bg-zinc-800 ${isActive ? 'bg-purple-900' : ''}`} />}
                                    <div className={`relative z-10 w-10 h-10 rounded-full border flex items-center justify-center transition-all duration-500 ${isActive ? 'bg-purple-500 border-purple-400 text-white shadow-[0_0_15px_rgba(168,85,247,0.4)]' : 'bg-zinc-900 border-zinc-700 text-zinc-600'}`}>
                                        {isActive ? <CheckCircle2 size={18} /> : <span className="text-xs font-mono">{stage.id}</span>}
                                    </div>
                                    <div className={`flex-1 transition-all duration-500 ${isActive ? 'opacity-100' : 'opacity-40'}`}>
                                        <h4 className={`text-lg font-bold ${isActive ? 'text-white' : 'text-zinc-300'}`}>{stage.label}</h4>
                                        <p className="text-xs text-zinc-500">{stage.desc}</p>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        );
    };

    // STEP 5: SUCCESS
    const renderStep5 = () => (
        <div className="h-full flex flex-col items-center justify-center space-y-10 py-10">
            <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="relative rounded-3xl overflow-hidden shadow-2xl border border-zinc-800 bg-black max-h-[70vh] aspect-[9/16]">
                <video src={finalVideoUrl!} controls autoPlay loop playsInline className="w-full h-full object-cover" />
            </motion.div>
            <div className="flex gap-4">
                <button onClick={handleSaveProject} className="px-8 py-4 bg-zinc-800 hover:bg-zinc-700 text-white font-bold rounded-xl border border-zinc-700 flex items-center gap-2 transform transition-transform active:scale-95">
                    <Bookmark size={20} className="text-purple-400" /> Save to Library
                </button>
                <button onClick={handleDownload} className="px-8 py-4 bg-white hover:bg-zinc-200 text-black font-bold rounded-xl flex items-center gap-2 transform transition-transform active:scale-95">
                    <Download size={20} /> Download Device
                </button>
                <button onClick={() => { setStep(1); setFinalVideoUrl(null); setTopic(''); }} className="p-4 bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 text-zinc-400 hover:text-white rounded-xl transition-all" title="Start New">
                    <RefreshCw size={20} />
                </button>
            </div>
        </div>
    );

    // --- SCRIPT REVIEW MODAL ---
    const renderScriptReviewModal = () => (
        <AnimatePresence>
            {isReviewingScript && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
                >
                    <motion.div
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="bg-zinc-900 border border-zinc-800 rounded-3xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]"
                    >
                        <div className="p-6 border-b border-zinc-800 flex justify-between items-center bg-zinc-950/50">
                            <div>
                                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                                    <Edit2 size={20} className="text-purple-400" /> Review Script
                                </h3>
                                <p className="text-zinc-500 text-xs">Edit the AI generated script before producing audio.</p>
                            </div>
                            <button onClick={() => setIsReviewingScript(false)} className="text-zinc-500 hover:text-white transition-colors">
                                <ArrowLeft size={20} />
                            </button>
                        </div>

                        <div className="flex-1 p-6 overflow-hidden flex flex-col">
                            <textarea
                                value={reviewScript}
                                onChange={(e) => setReviewScript(e.target.value)}
                                className="flex-1 w-full bg-zinc-950/50 border border-zinc-800 rounded-xl p-4 text-zinc-300 font-mono text-base focus:ring-1 focus:ring-purple-500 focus:outline-none resize-none custom-scrollbar"
                                placeholder="Loading script..."
                            />
                        </div>

                        <div className="p-6 border-t border-zinc-800 bg-zinc-950/50 flex justify-end gap-4">
                            <button
                                onClick={() => setIsReviewingScript(false)}
                                className="px-6 py-3 rounded-xl text-zinc-400 hover:bg-zinc-800 transition-colors font-bold text-sm"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => generateScriptAndVisuals(reviewScript)}
                                disabled={isLoading}
                                className="px-8 py-3 bg-white text-black hover:bg-zinc-200 rounded-xl font-bold text-sm flex items-center gap-2 transition-all transform hover:scale-105"
                            >
                                {isLoading ? <Loader2 className="animate-spin" size={16} /> : <Zap size={16} fill="currentColor" />}
                                GENERATE MASTERPIECE
                            </button>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );

    return (
        <div className="min-h-screen bg-black text-white p-6 md:p-12 font-sans selection:bg-purple-500/30 flex flex-col">
            <div className="fixed inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 pointer-events-none"></div>
            <div className="fixed inset-0 bg-gradient-to-br from-black via-zinc-950 to-black pointer-events-none"></div>

            <div className="relative z-10 w-full mx-auto flex-1 flex flex-col">
                <AnimatePresence mode='wait'>
                    <motion.div key={step} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} className="flex-1">
                        {step === 1 && renderStep1()}
                        {step === 2 && renderStep2()}
                        {step === 3 && renderStep3()}
                        {step === 4 && renderStep4()}
                        {step === 5 && renderStep5()}
                    </motion.div>
                </AnimatePresence>
            </div>
            {renderScriptReviewModal()}
            {/* UPGRADE MODAL */}
            {showUpgradeModal && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
                    onClick={() => setShowUpgradeModal(false)}
                >
                    <div
                        className="w-full max-w-md bg-zinc-900 border border-zinc-700 rounded-3xl p-8 relative overflow-hidden text-center space-y-6"
                        onClick={e => e.stopPropagation()}
                    >
                        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500" />
                        <div className="w-16 h-16 rounded-full bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center shadow-lg shadow-purple-500/25 mx-auto">
                            <Sparkles size={32} className="text-white" />
                        </div>
                        <div>
                            <h3 className="text-2xl font-black text-white mb-2">Unlock HD Quality</h3>
                            <p className="text-zinc-400 text-sm">
                                1080p Resolution creates crisper, more professional videos. Exclusive to the <strong>Creator Plan</strong>.
                            </p>
                        </div>
                        <button
                            onClick={() => window.location.href = '/pricing'}
                            className="w-full py-4 bg-white text-black font-bold rounded-xl hover:bg-zinc-200 transition-colors"
                        >
                            Upgrade to Creator
                        </button>
                        <button
                            onClick={() => setShowUpgradeModal(false)}
                            className="text-zinc-500 hover:text-white text-sm"
                        >
                            Maybe Later
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}