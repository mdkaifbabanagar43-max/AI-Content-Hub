'use client';

import { useState, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Sparkles, Smartphone, MonitorPlay, Zap, Clock,
    Ghost, Laugh, Brain, Rocket, CheckCircle2,
    Loader2, Download, Play, Terminal, ArrowRight, ArrowLeft,
    Edit2, RefreshCw, Volume2, Image as ImageIcon, Wand2, Mic, Lock, Globe, Sliders, Bookmark, Check,
    Flame, GraduationCap, BookOpen, Lightbulb, TrendingUp, History,
    LayoutGrid, Network
} from 'lucide-react';
import { ConceptGraph } from './ConceptGraph';
import { Skeleton } from './ui/Skeleton';
import { LoadingState } from './ui/LoadingState';
import { cn } from '@/lib/utils';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';
import { API_BASE_URL } from '@/lib/config';
import { forceDownload } from '@/lib/download';
import { handleAppError } from '@/lib/errorHandler';
import { LANGUAGES, Voice } from '@/lib/voices';
import { usePlan } from '@/context/PlanContext';

// --- CONTENT TYPES (Step 0 - Clean Unified Aesthetics) ---
const CONTENT_TYPES = [
    { id: 'educational', label: 'Educational', icon: GraduationCap, desc: 'Facts, tutorials, how-tos' },
    { id: 'motivation', label: 'Motivation', icon: Flame, desc: 'Inspire and energize' },
    { id: 'story', label: 'Story', icon: BookOpen, desc: 'Narratives & drama' },
    { id: 'explainer', label: 'Explainer', icon: Lightbulb, desc: 'Break down complex topics' },
    { id: 'finance', label: 'Finance', icon: TrendingUp, desc: 'Crypto, stocks, money' },
    { id: 'history', label: 'History', icon: History, desc: 'Past events & stories' },
    { id: 'podcast', label: 'Podcast', icon: Mic, desc: 'Conversational style' },
];

// --- CONFIG CONSTANTS ---
const PLATFORMS = [
    { id: 'tiktok', label: 'TikTok / Reels', icon: Smartphone, desc: '9:16 Vertical â€¢ Fast' },
    { id: 'youtube', label: 'YouTube Shorts', icon: MonitorPlay, desc: '9:16 Vertical â€¢ Cinematic' },
];

const MOODS = {
    scary: { label: 'Scary', icon: Ghost },
    fast: { label: 'Fast Paced', icon: Zap },
    informative: { label: 'Informative', icon: Brain },
    motivational: { label: 'Motivational', icon: Rocket },
    funny: { label: 'Humorous', icon: Laugh },
};

// --- STEP MAP ---
const STEPS = {
    TOPIC: 1,
    CONCEPT: 2,
    DIRECTOR: 3,
    RENDER: 4,
    SUCCESS: 5,
} as const;

export default function IdeaStudio({ onNavigate }: { onNavigate?: (tab: string) => void }) {
    const { user } = useAuth();
    const { deductCredits, refundCredits, userPlan } = usePlan();

    // Wizard State
    const [step, setStep] = useState(1);
    const [isLoading, setIsLoading] = useState(false);

    // Content Type State
    const [contentType, setContentType] = useState('educational');

    // Data State
    const [topic, setTopic] = useState('');
    const [platform, setPlatform] = useState(PLATFORMS[0].id);
    const [duration, setDuration] = useState("30s");
    const [quality, setQuality] = useState("720p");
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);

    // Advanced Settings State
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [visualStyle, setVisualStyle] = useState('Cinematic');
    const [bgmStyle, setBgmStyle] = useState('Epic');

    // Audio Identity State
    const [languageId, setLanguageId] = useState('en-US');
    const [voiceId, setVoiceId] = useState<string>('');

    const currentLang = LANGUAGES.find(l => l.id === languageId) || LANGUAGES[0];

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
    const [conceptViewMode, setConceptViewMode] = useState<'grid' | 'graph'>('graph');

    const [previewAssets, setPreviewAssets] = useState<any>(null);
    const [editedScript, setEditedScript] = useState('');

    const [isReviewingScript, setIsReviewingScript] = useState(false);
    const [reviewScript, setReviewScript] = useState('');
    const originalReviewScript = useRef('');
    const previewInFlight = useRef(false);

    const [logs, setLogs] = useState<string[]>([]);
    const [renderStage, setRenderStage] = useState(0);
    const [finalVideoUrl, setFinalVideoUrl] = useState<string | null>(null);

    const MAX_SCRIPT_CHARS = 5000;
    const scriptValidationError = useMemo(() => {
        const trimmed = reviewScript.trim();
        if (!trimmed) return 'Script cannot be empty.';
        if (trimmed.length < 20) return 'Script is too short to generate audio.';
        if (reviewScript.length > MAX_SCRIPT_CHARS) return `Script exceeds ${MAX_SCRIPT_CHARS} character limit (${reviewScript.length} chars).`;
        return null;
    }, [reviewScript]);

    // STEP 1 -> 2: BRAINSTORM
    const handleBrainstorm = async () => {
        if (!user) return;
        if (!topic || !topic.trim()) {
            toast.error('Please enter a topic before brainstorming.');
            return;
        }
        if (topic.trim().length > 2000) {
            toast.error('Topic is too long. Please limit to 2000 characters.');
            return;
        }
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
                    platform,
                    contentType
                })
            });

            if (!res.ok) throw new Error('Failed to generate concepts');
            const data = await res.json();
            if (data.concepts) {
                setIdeas(data.concepts);
                setStep(2);
            } else if (Array.isArray(data)) {
                setIdeas(data);
                setStep(2);
            }
        } catch (err) {
            handleAppError(err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleNovaReel = async () => {
        if (!user) return;
        if (!topic || !topic.trim()) {
            toast.error('Please enter a topic for the video.');
            return;
        }
        
        setIsLoading(true);
        setStep(STEPS.RENDER);
        setRenderStage(1);
        setLogs(["Starting AWS Bedrock Nova Reel engine...", "Generating 30s video in 6s chunks..."]);
        
        try {
            const token = await user.getIdToken();
            const res = await fetch(`${API_BASE_URL}/generate-nova-reel`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    topic,
                    voice_name: voiceId || 'en-US-Journey-D'
                })
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => null);
                throw new Error(errData?.detail || 'Nova Reel generation failed');
            }
            const data = await res.json();
            
            setFinalVideoUrl(data.url);
            setLogs(prev => [...prev, "🎉 30s AWS Nova Reel video fully rendered!"]);
            setRenderStage(4);
            setStep(STEPS.SUCCESS);
        } catch (err) {
            handleAppError(err);
            setStep(STEPS.TOPIC);
        } finally {
            setIsLoading(false);
        }
    };

    // PREVIEW SCRIPT
    const previewScript = async (concept: any) => {
        if (!user || previewInFlight.current) return;
        previewInFlight.current = true;
        setSelectedIdea(concept);
        setIsLoading(true);
        try {
            const token = await user.getIdToken();
            const res = await fetch(`${API_BASE_URL}/generate-script-preview`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    title: concept.title,
                    hook: concept.hook || '',
                    mood: concept.mood || 'informative',
                    platform,
                    duration: '30s',
                    voice_name: voiceId,
                    language: currentLang.label,
                    content_type: contentType,
                    visual_style: visualStyle,
                    bgm_style: bgmStyle
                })
            });

            if (!res.ok) throw new Error('Failed to generate script preview');
            const data = await res.json();
            setReviewScript(data.script);
            originalReviewScript.current = data.script;
            setIsReviewingScript(true);
        } catch (err) {
            handleAppError(err);
        } finally {
            setIsLoading(false);
            previewInFlight.current = false;
        }
    };

    // GENERATE SCRIPT AND VISUALS
    const generateScriptAndVisuals = async (finalScriptText: string) => {
        if (!user || !selectedIdea) return;
        setIsReviewingScript(false);
        setIsLoading(true);
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
                    hook: selectedIdea.hook || '',
                    mood: selectedIdea.mood || 'informative',
                    script: finalScriptText,
                    platform,
                    duration: '30s',
                    voice_name: voiceId,
                    language: currentLang.label,
                    content_type: contentType,
                    visual_style: visualStyle,
                    bgm_style: bgmStyle
                })
            });

            if (!res.ok) throw new Error('Failed to prepare director assets');
            const data = await res.json();
            setPreviewAssets(data);
            setEditedScript(finalScriptText);
            setStep(3);
        } catch (err) {
            handleAppError(err);
        } finally {
            setIsLoading(false);
        }
    };

    // STEP 3 -> 4: RENDER
    const handleRender = async () => {
        if (!user || !selectedIdea) return;
        const COST = 20;

        if (!deductCredits(COST)) return;

        setStep(4);
        setRenderStage(0);

        try {
            const token = await user.getIdToken();
            setRenderStage(1);

            const res = await fetch(`${API_BASE_URL}/render-final`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    concept: selectedIdea,
                    script: editedScript,
                    platform,
                    language: currentLang.label,
                    voice: voiceId,
                    duration,
                    quality,
                    visual_style: visualStyle,
                    bgm_style: bgmStyle,
                    audio_base64: previewAssets?.audio_base64,
                    visual_plan: previewAssets?.visual_plan
                })
            });

            setRenderStage(2);
            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'Render failed');
            }

            const data = await res.json();
            setRenderStage(3);

            if (data.status === 'processing' && data.job_id) {
                const jobId = data.job_id;
                let isDone = false;
                while (!isDone) {
                    await new Promise(r => setTimeout(r, 3000));
                    const jobRes = await fetch(`${API_BASE_URL}/api/jobs/${jobId}`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    if (!jobRes.ok) continue;
                    const jobData = await jobRes.json();
                    if (jobData.status === 'completed') {
                        setFinalVideoUrl(jobData.result_url || jobData.video_url);
                        isDone = true;
                        setStep(5);
                    } else if (jobData.status === 'failed') {
                        throw new Error(jobData.error || 'Video rendering failed');
                    }
                }
            } else if (data.video_url) {
                setFinalVideoUrl(data.video_url);
                setStep(5);
            }
        } catch (err) {
            handleAppError(err, () => refundCredits(COST));
            setStep(3);
        }
    };

    const handleSaveProject = () => {
        toast.success("Saved to Library!");
    };

    const handleDownload = () => {
        if (finalVideoUrl) {
            forceDownload(finalVideoUrl, `idea-studio-${Date.now()}.mp4`);
        }
    };

    // STEP 1: TOPIC INPUT & CONTENT TYPE
    const renderStep1 = () => {
        return (
            <div className="w-full max-w-4xl mx-auto flex items-center justify-center min-h-[70vh]">
                <div className="w-full bento-card p-10 md:p-16 relative overflow-hidden flex flex-col items-center">
                    
                    {/* Decorative glow inside the card */}
                    <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent" />
                    <div className="absolute -top-40 -inset-x-20 h-[300px] bg-indigo-500/10 blur-[120px] rounded-full pointer-events-none" />

                    {/* Header */}
                    <div className="text-center space-y-3 mb-10 relative z-10">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-[10px] font-bold tracking-widest uppercase mb-2">
                            <Sparkles size={12} />
                            Idea Studio
                        </div>
                        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-white">
                            What are we creating?
                        </h1>
                        <p className="text-base text-slate-400 max-w-lg mx-auto">
                            Describe your topic, and our AI will instantly generate scripts, voiceovers, and auto-edited viral shorts.
                        </p>
                    </div>

                    {/* Content Type Selector */}
                    <div className="w-full max-w-2xl space-y-3 mb-8 relative z-10">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider ml-1">Content Format</label>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                            {CONTENT_TYPES.map((ct) => {
                                const Icon = ct.icon;
                                const isSelected = contentType === ct.id;
                                return (
                                    <button
                                        key={ct.id}
                                        onClick={() => setContentType(ct.id)}
                                        className={cn(
                                            'flex flex-col items-center gap-2 p-4 rounded-2xl border transition-all duration-300',
                                            isSelected
                                                ? 'bg-indigo-600/20 border-indigo-500/50 text-white shadow-[0_0_20px_rgba(99,102,241,0.15)]'
                                                : 'glass hover:bg-white/[0.04] text-slate-400 hover:text-slate-200'
                                        )}
                                    >
                                        <Icon size={20} className={isSelected ? "text-indigo-400" : "text-slate-500"} />
                                        <span className="text-xs font-medium">{ct.label}</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Main Prompt Input Area */}
                    <div className="w-full max-w-2xl space-y-3 relative z-10">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider ml-1">Video Topic</label>
                        <div className="relative group">
                            <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500 to-cyan-500 rounded-2xl blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
                            <div className="relative flex items-center bg-[#09090b] border border-white/10 rounded-2xl overflow-hidden p-2">
                                
                                <select
                                    value={languageId}
                                    onChange={(e) => setLanguageId(e.target.value)}
                                    className="appearance-none bg-white/[0.04] hover:bg-white/[0.08] border border-white/5 rounded-xl px-4 py-3 text-sm font-medium cursor-pointer focus:outline-none text-white/80 transition-all shrink-0 h-full"
                                    title="Language"
                                >
                                    {LANGUAGES.map(l => (
                                        <option key={l.id} value={l.id} className="bg-slate-900">
                                            {l.flag} {l.label.split(' ')[0]}
                                        </option>
                                    ))}
                                </select>

                                <input
                                    value={topic}
                                    onChange={(e) => setTopic(e.target.value)}
                                    placeholder="E.g., The secret history of the pyramids..."
                                    className="flex-1 bg-transparent border-none text-base font-medium text-white placeholder-slate-500 px-4 focus:ring-0 focus:outline-none h-12"
                                    onKeyDown={(e) => e.key === 'Enter' && handleBrainstorm()}
                                    autoFocus
                                />

                                <div className="flex gap-2 h-full">
                                    <motion.button
                                        whileHover={{ scale: 1.02 }}
                                        whileTap={{ scale: 0.98 }}
                                        onClick={handleBrainstorm}
                                        disabled={!topic || isLoading}
                                        className="h-12 px-6 rounded-xl bg-indigo-600 text-white font-bold text-sm flex items-center gap-2 hover:bg-indigo-500 transition-colors disabled:opacity-50 shrink-0 shadow-lg shadow-indigo-500/20"
                                        title="Brainstorm viral angles"
                                    >
                                        {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                                        Generate
                                    </motion.button>
                                    
                                    <motion.button
                                        whileHover={{ scale: 1.02 }}
                                        whileTap={{ scale: 0.98 }}
                                        onClick={handleNovaReel}
                                        disabled={!topic || isLoading}
                                        className="h-12 px-4 rounded-xl bg-cyan-600/20 border border-cyan-500/50 text-cyan-400 font-bold text-sm flex items-center gap-2 hover:bg-cyan-600/30 transition-colors disabled:opacity-50 shrink-0 shadow-lg shadow-cyan-500/10"
                                        title="Generate a 30s Text-to-Video using Amazon Nova Reel"
                                    >
                                        {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />}
                                        Nova Reel
                                    </motion.button>
                                </div>
                            </div>
                        </div>
                        <div className="flex justify-between items-center px-1 pt-2">
                            <p className="text-[10px] text-slate-500">Press <kbd className="px-1.5 py-0.5 rounded border border-white/10 bg-white/5 font-mono">Enter ↵</kbd> to generate</p>
                        </div>
                    </div>

                    {/* Advanced Settings â€” compact accordion */}
                    <div className="w-full max-w-2xl relative z-10">
                        <button
                            onClick={() => setShowAdvanced(!showAdvanced)}
                            className="mx-auto flex items-center gap-2 text-zinc-600 hover:text-zinc-300 text-xs font-medium transition-colors group"
                        >
                            <Sliders size={12} className="group-hover:text-indigo-400 transition-colors" />
                            <span>Advanced Settings</span>
                            <ArrowRight size={10} className={cn('transition-transform duration-200', showAdvanced ? 'rotate-90' : '')} />
                        </button>

                        <AnimatePresence>
                            {showAdvanced && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    transition={{ duration: 0.25 }}
                                    className="overflow-hidden"
                                >
                                    <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3 max-w-3xl mx-auto text-left">
                                        {/* Format */}
                                        <div className="bg-[#121215] border border-white/[0.07] rounded-xl p-4 space-y-3">
                                            <p className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider flex items-center gap-1.5">
                                                <MonitorPlay size={11} className="text-indigo-500" /> Platform
                                            </p>
                                            <div className="grid grid-cols-2 gap-1.5">
                                                {PLATFORMS.map(p => (
                                                    <button
                                                        key={p.id}
                                                        onClick={() => setPlatform(p.id)}
                                                        className={cn(
                                                            'flex items-center gap-1.5 h-8 px-2 rounded-lg border text-[11px] font-medium transition-all',
                                                            platform === p.id
                                                                ? 'bg-white/[0.08] border-white/[0.18] text-white'
                                                                : 'border-white/[0.05] text-zinc-600 hover:text-zinc-300 hover:border-white/[0.1]'
                                                        )}
                                                    >
                                                        <p.icon size={11} />
                                                        <span className="truncate">{p.label.split('/')[0]}</span>
                                                    </button>
                                                ))}
                                            </div>
                                        </div>

                                        {/* Voice */}
                                        <div className="bg-[#121215] border border-white/[0.07] rounded-xl p-4 space-y-3">
                                            <p className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider flex items-center gap-1.5">
                                                <Mic size={11} className="text-indigo-500" /> Voice
                                            </p>
                                            <div className="flex flex-wrap gap-1 mb-2">
                                                {LANGUAGES.slice(0, 5).map(lang => (
                                                    <button
                                                        key={lang.id}
                                                        onClick={() => setLanguageId(lang.id)}
                                                        className={cn(
                                                            'w-8 h-8 rounded-lg flex items-center justify-center text-sm transition-all border',
                                                            languageId === lang.id
                                                                ? 'bg-white/[0.08] border-white/[0.16]'
                                                                : 'border-white/[0.05] hover:border-white/[0.1]'
                                                        )}
                                                    >
                                                        {lang.flag}
                                                    </button>
                                                ))}
                                            </div>
                                            <div className="space-y-1 max-h-[80px] overflow-y-auto custom-scrollbar">
                                                {currentLang.voices.slice(0, 3).map(voice => (
                                                    <button
                                                        key={voice.id}
                                                        onClick={() => setVoiceId(voice.id)}
                                                        className={cn(
                                                            'w-full flex items-center gap-2 px-2 h-8 rounded-lg border text-left text-[11px] font-medium transition-all',
                                                            voiceId === voice.id
                                                                ? 'bg-white/[0.07] border-white/[0.16] text-white'
                                                                : 'border-transparent text-zinc-600 hover:text-zinc-300'
                                                        )}
                                                    >
                                                        <span className="w-4 h-4 rounded-full bg-white/[0.07] flex items-center justify-center text-[8px] font-bold text-zinc-500 shrink-0">
                                                            {voice.gender === 'Male' ? 'M' : 'F'}
                                                        </span>
                                                        <span className="truncate">{voice.label.split('(')[0].trim()}</span>
                                                        {voiceId === voice.id && <Check size={10} className="ml-auto text-indigo-400" />}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>

                                        {/* Visuals & Music */}
                                        <div className="bg-[#121215] border border-white/[0.07] rounded-xl p-4 space-y-3">
                                            <p className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider flex items-center gap-1.5">
                                                <ImageIcon size={11} className="text-indigo-500" /> Style
                                            </p>
                                            <div>
                                                <p className="text-[10px] text-zinc-700 mb-1.5">Visual</p>
                                                <div className="grid grid-cols-2 gap-1">
                                                    {['Cinematic', 'Minimalist', 'AI Art', 'Nature'].map(style => (
                                                        <button
                                                            key={style}
                                                            onClick={() => setVisualStyle(style)}
                                                            className={cn(
                                                                'h-7 px-2 rounded-lg border text-[10px] font-medium transition-all',
                                                                visualStyle === style
                                                                    ? 'bg-white/[0.08] border-white/[0.18] text-white'
                                                                    : 'border-white/[0.05] text-zinc-600 hover:text-zinc-300'
                                                            )}
                                                        >{style}</button>
                                                    ))}
                                                </div>
                                            </div>
                                            <div>
                                                <p className="text-[10px] text-zinc-700 mb-1.5">Music</p>
                                                <div className="grid grid-cols-2 gap-1">
                                                    {['Epic', 'Lo-Fi', 'Suspense', 'Upbeat'].map(bgm => (
                                                        <button
                                                            key={bgm}
                                                            onClick={() => setBgmStyle(bgm)}
                                                            className={cn(
                                                                'h-7 px-2 rounded-lg border text-[10px] font-medium transition-all',
                                                                bgmStyle === bgm
                                                                    ? 'bg-white/[0.08] border-white/[0.18] text-white'
                                                                    : 'border-white/[0.05] text-zinc-600 hover:text-zinc-300'
                                                            )}
                                                        >{bgm}</button>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    {/* Social Proof */}
                    <div className="text-center">
                        <p className="text-zinc-700 text-[11px] font-mono flex items-center justify-center gap-4">
                            <span className="flex items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                                <span>10K+ videos produced</span>
                            </span>
                            <span className="flex items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                                <span>Avg generation: 45s</span>
                            </span>
                        </p>
                    </div>

                </div>
            </div>
        );
    };



    // STEP 2: CONCEPT SELECTION (Clean Dark Luxury Cards)
    const renderStep2 = () => (
        <div className="space-y-8 max-w-6xl mx-auto pb-20 relative pt-10">
            <header className="flex flex-col md:flex-row items-start md:items-center justify-between border-b border-white/[0.08] pb-6 gap-4">
                <div>
                    <h2 className="text-3xl md:text-4xl font-bold text-white mb-1.5 tracking-tight">Choose your <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-sky-400">Angle</span></h2>
                    <p className="text-slate-400 text-sm">Generated {ideas.length} viral angles for "{topic}"</p>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1 bg-slate-900 border border-white/[0.08] p-1 rounded-xl">
                        <button
                            onClick={() => setConceptViewMode('grid')}
                            className={cn("px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all", conceptViewMode === 'grid' ? "bg-slate-800 text-white shadow" : "text-slate-400 hover:text-slate-200")}
                        >
                            <LayoutGrid size={14} /> Cards
                        </button>
                        <button
                            onClick={() => setConceptViewMode('graph')}
                            className={cn("px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all", conceptViewMode === 'graph' ? "bg-indigo-500/20 text-indigo-200 border border-indigo-500/30 shadow" : "text-slate-400 hover:text-slate-200")}
                        >
                            <Network size={14} /> Concept Graph
                        </button>
                    </div>
                    <button onClick={() => setStep(1)} className="px-3.5 py-2 rounded-xl hover:bg-white/[0.06] text-slate-400 hover:text-white text-xs font-semibold transition-colors flex items-center gap-2 border border-transparent hover:border-white/5">
                        <ArrowLeft size={14} /> Back
                    </button>
                </div>
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
                                <div key={i} className="h-[380px] bg-slate-900/40 border border-white/[0.06] rounded-3xl p-7 flex flex-col justify-between">
                                    <div className="flex justify-between items-start mb-6">
                                        <Skeleton className="w-10 h-10 rounded-xl" />
                                        <Skeleton className="w-16 h-5 rounded-md" />
                                    </div>
                                    <div className="space-y-3">
                                        <Skeleton className="h-7 w-3/4" />
                                        <Skeleton className="h-7 w-1/2" />
                                    </div>
                                    <div className="space-y-2 mt-6">
                                        <Skeleton className="h-4 w-full" />
                                        <Skeleton className="h-4 w-5/6" />
                                    </div>
                                    <div className="flex justify-end mt-4">
                                        <Skeleton className="h-4 w-24" />
                                    </div>
                                </div>
                            ))}
                        </div>
                    }
                />
            ) : conceptViewMode === 'graph' ? (
                <ConceptGraph
                    topic={topic}
                    concepts={ideas}
                    onSelectConcept={(concept) => previewScript(concept)}
                />
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {ideas.map((idea, idx) => {
                        const moodInfo = MOODS[idea.mood as keyof typeof MOODS] || MOODS.fast;
                        const MoodIcon = moodInfo.icon;

                        return (
                            <motion.button
                                key={idea.id}
                                initial={{ opacity: 0, y: 15 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: idx * 0.08 }}
                                whileHover={{ y: -4 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={() => previewScript(idea)}
                                className="group relative h-[380px] text-left w-full focus:outline-none"
                            >
                                <div className="absolute inset-0 bg-slate-950 border border-white/[0.08] rounded-3xl p-7 flex flex-col justify-between transition-all duration-300 group-hover:border-indigo-500/40 group-hover:bg-slate-900/90 shadow-xl group-hover:shadow-[0_0_30px_rgba(99,102,241,0.12)] overflow-hidden">
                                    <div>
                                        <div className="flex justify-between items-start mb-5">
                                            <div className="p-2.5 rounded-xl bg-slate-900 border border-white/10 text-indigo-400 group-hover:scale-105 transition-transform">
                                                <MoodIcon size={18} />
                                            </div>
                                            <span className="text-[9px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                                                {idea.mood}
                                            </span>
                                        </div>

                                        <h3 className="text-xl font-bold text-white leading-tight mb-3 group-hover:text-indigo-200 transition-colors">
                                            {idea.title}
                                        </h3>
                                        <div className="w-10 h-0.5 bg-slate-800 rounded-full mb-4 group-hover:bg-indigo-500 transition-colors" />
                                    </div>

                                    <div className="relative">
                                        <p className="text-slate-400 text-xs leading-relaxed line-clamp-4 italic border-l-2 border-indigo-500/40 pl-3">
                                            "{idea.hook}"
                                        </p>
                                    </div>

                                    <div className="flex items-center justify-end gap-2 text-indigo-400 font-bold text-xs group-hover:translate-x-1 transition-all pt-2">
                                        <span>Select Angle</span>
                                        <ArrowRight size={14} />
                                    </div>
                                </div>
                            </motion.button>
                        );
                    })}
                </div>
            )}
        </div>
    );

    // STEP 3: DIRECTOR'S STUDIO
    const renderStep3 = () => (
        <div className="flex flex-col h-[calc(100vh-140px)] max-w-[1600px] mx-auto space-y-6 pt-6">
            <div className="flex items-center justify-between shrink-0 mb-2">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-indigo-500/10 rounded-xl text-indigo-400 border border-indigo-500/20">
                        <Edit2 size={20} />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-white">Director's Studio</h2>
                        <p className="text-slate-400 text-xs">Fine-tune your viral script and audio synthesis</p>
                    </div>
                </div>
                <button onClick={() => setStep(2)} className="flex items-center gap-2 px-3.5 py-2 rounded-xl hover:bg-white/[0.06] text-slate-400 text-xs font-semibold transition-colors border border-white/5">
                    <ArrowLeft size={14} /> Change Angle
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-full min-h-0 pb-6">
                <div className="lg:col-span-7 flex flex-col justify-end">
                    {/* Chat Bubble Interface */}
                    <div className="flex-1 flex flex-col gap-6 bg-slate-900/40 backdrop-blur-md rounded-3xl p-6 border border-white/5 shadow-2xl relative overflow-hidden">
                        
                        {/* Decorative Background Glow */}
                        <div className="absolute top-0 left-0 w-full h-32 bg-gradient-to-b from-indigo-500/10 to-transparent pointer-events-none" />

                        {/* User Prompt (Simulated) */}
                        <div className="flex justify-end animate-in fade-in slide-in-from-right-4 duration-500">
                            <div className="max-w-[80%] bg-indigo-600 text-white p-4 rounded-2xl rounded-tr-sm shadow-md">
                                <p className="text-sm font-medium">Generate a viral video about: "{topic || 'Awesome AI video'}"</p>
                            </div>
                        </div>

                        {/* AI Response (Script Editor) */}
                        <div className="flex gap-4 animate-in fade-in slide-in-from-left-4 duration-700 delay-150 flex-1">
                            {/* AI Avatar */}
                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shrink-0 shadow-lg shadow-indigo-500/30">
                                <Sparkles size={20} className="text-white" />
                            </div>

                            {/* Editable Chat Bubble */}
                            <div className="flex-1 flex flex-col max-w-[85%] bg-slate-800/80 border border-white/10 rounded-2xl rounded-tl-sm shadow-xl overflow-hidden group focus-within:border-indigo-500/50 focus-within:ring-1 focus-within:ring-indigo-500/50 transition-all">
                                <div className="px-4 py-2 bg-slate-800/50 border-b border-white/5 flex items-center justify-between">
                                    <span className="text-xs font-bold text-indigo-300 flex items-center gap-1.5"><Terminal size={12} /> AI Script Assistant</span>
                                    <span className="text-[10px] text-slate-500 uppercase tracking-wider">Editable</span>
                                </div>
                                <textarea
                                    value={editedScript}
                                    onChange={(e) => setEditedScript(e.target.value)}
                                    className="flex-1 w-full bg-transparent p-4 text-sm md:text-base text-slate-200 font-medium leading-relaxed focus:outline-none resize-none custom-scrollbar selection:bg-indigo-500/30"
                                    placeholder="AI generating script..."
                                />
                            </div>
                        </div>
                    </div>
                </div>

                <div className="lg:col-span-5 flex flex-col gap-6">
                    <div className="bg-slate-950 border border-white/[0.08] rounded-3xl p-6 shadow-xl relative overflow-hidden">
                        <h3 className="text-xs font-bold text-slate-400 uppercase flex items-center gap-2 mb-3.5 tracking-wider">
                            <Volume2 size={14} className="text-indigo-400" /> Audio Preview
                        </h3>
                        <div className="bg-slate-900/80 rounded-xl p-3.5 border border-white/5">
                            <audio controls src={`data:audio/mp3;base64,${previewAssets?.audio_base64}`} className="w-full h-9 opacity-90" />
                        </div>
                    </div>

                    <div className="flex-1 bg-slate-950 border border-white/[0.08] rounded-3xl p-6 shadow-xl flex flex-col">
                        <h3 className="text-xs font-bold text-slate-400 uppercase flex items-center gap-2 mb-3.5 tracking-wider">
                            <ImageIcon size={14} className="text-indigo-400" /> Visual Strategy
                        </h3>
                        <div className="flex-1 bg-slate-900/60 rounded-xl p-5 border-l-2 border-indigo-500 italic text-slate-300 leading-relaxed overflow-y-auto custom-scrollbar text-sm">
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
                            "w-full py-5 text-black rounded-2xl shadow-xl transition-all font-black text-lg flex items-center justify-center gap-3 group relative overflow-hidden",
                            userPlan === 'free' ? "bg-slate-800 text-slate-400 hover:bg-slate-700" : "bg-white hover:bg-slate-200"
                        )}
                    >
                        {userPlan === 'free' ? (
                            <>
                                <Lock size={20} className="text-indigo-400" />
                                <span className="uppercase tracking-tight">Upgrade to Render</span>
                            </>
                        ) : (
                            <>
                                <span className="uppercase tracking-tight">Render Masterpiece</span>
                                <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );

    // STEP 4: RENDERING
    const renderStep4 = () => {
        const stages = [
            { id: 1, label: "Initialization", desc: "Allocating GPU clusters..." },
            { id: 2, label: "Visual Synthesis", desc: "Generating and editing video assets..." },
            { id: 3, label: "Aural Formatting", desc: "Syncing voiceover and mastering audio..." },
            { id: 4, label: "Final Polish", desc: "Applying color grading and viral metadata..." }
        ];

        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] w-full max-w-4xl mx-auto relative px-4">
                <div className="w-full bento-card p-8 md:p-12 relative overflow-hidden flex flex-col gap-8">
                    <div className="text-center space-y-2 mb-2">
                        <div className="flex justify-center mb-4">
                            <div className="relative w-20 h-20">
                                <svg className="w-full h-full rotate-[-90deg]" viewBox="0 0 36 36">
                                    <path className="text-slate-800" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="2" />
                                    <motion.path className="text-indigo-500" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray={`${((renderStage + 1) / 4) * 100}, 100`} initial={{ strokeDasharray: "0, 100" }} animate={{ strokeDasharray: `${((renderStage + 1) / 4) * 100}, 100` }} transition={{ duration: 0.5 }} />
                                </svg>
                                <div className="absolute inset-0 flex items-center justify-center text-xs font-mono font-bold text-white">{(renderStage + 1) * 25}%</div>
                            </div>
                        </div>
                        <h2 className="text-2xl md:text-3xl font-bold text-white tracking-tight">Constructing Masterpiece</h2>
                        <p className="text-slate-400 text-xs">AI engine is producing your video</p>
                    </div>

                    <div className="space-y-5 max-w-lg mx-auto w-full">
                        {stages.map((stage, idx) => {
                            const isActive = renderStage >= idx;
                            return (
                                <div key={stage.id} className="relative flex items-center gap-4 group">
                                    {idx !== stages.length - 1 && <div className={`absolute left-[17px] top-9 w-[2px] h-7 bg-slate-800 ${isActive ? 'bg-indigo-600' : ''}`} />}
                                    <div className={`relative z-10 w-9 h-9 rounded-full border flex items-center justify-center transition-all duration-500 ${isActive ? 'bg-indigo-500 border-indigo-400 text-white shadow-[0_0_15px_rgba(99,102,241,0.3)]' : 'bg-slate-900 border-slate-800 text-slate-500'}`}>
                                        {isActive ? <CheckCircle2 size={16} /> : <span className="text-xs font-mono">{stage.id}</span>}
                                    </div>
                                    <div className={`flex-1 transition-all duration-500 ${isActive ? 'opacity-100' : 'opacity-40'}`}>
                                        <h4 className={`text-base font-bold ${isActive ? 'text-white' : 'text-slate-400'}`}>{stage.label}</h4>
                                        <p className="text-xs text-slate-500">{stage.desc}</p>
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
        <div className="h-full flex flex-col items-center justify-center space-y-8 py-10">
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="relative rounded-3xl overflow-hidden shadow-2xl border border-white/[0.08] bg-black max-h-[70vh] aspect-[9/16]">
                <video src={finalVideoUrl!} controls autoPlay loop playsInline className="w-full h-full object-cover" />
            </motion.div>
            <div className="flex gap-3">
                <button onClick={handleSaveProject} className="px-6 py-3.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl border border-white/10 flex items-center gap-2 transition-all">
                    <Bookmark size={16} className="text-indigo-400" /> Save to Library
                </button>
                <button onClick={handleDownload} className="px-6 py-3.5 bg-white hover:bg-slate-200 text-black font-bold text-xs rounded-xl flex items-center gap-2 transition-all">
                    <Download size={16} /> Download
                </button>
                <button onClick={() => { setStep(1); setFinalVideoUrl(null); setTopic(''); }} className="p-3.5 bg-slate-900 border border-white/10 hover:bg-slate-800 text-slate-400 hover:text-white rounded-xl transition-all" title="Start New">
                    <RefreshCw size={16} />
                </button>
            </div>
        </div>
    );

    // SCRIPT REVIEW MODAL
    const renderScriptReviewModal = () => (
        <AnimatePresence>
            {isReviewingScript && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md"
                >
                    <motion.div
                        initial={{ scale: 0.95, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="bg-slate-950 border border-white/10 rounded-3xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]"
                    >
                        <div className="p-5 border-b border-white/10 flex justify-between items-center bg-slate-900/40">
                            <div>
                                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                    <Edit2 size={18} className="text-indigo-400" /> Review Script
                                </h3>
                                <p className="text-slate-400 text-xs">Edit the AI generated script before producing audio.</p>
                            </div>
                            <button
                                onClick={() => {
                                    setReviewScript(originalReviewScript.current);
                                    setIsReviewingScript(false);
                                }}
                                className="text-slate-400 hover:text-white transition-colors"
                            >
                                <ArrowLeft size={18} />
                            </button>
                        </div>

                        <div className="flex-1 p-5 overflow-hidden flex flex-col gap-2">
                            <textarea
                                value={reviewScript}
                                onChange={(e) => {
                                    if (e.target.value.length <= MAX_SCRIPT_CHARS) {
                                        setReviewScript(e.target.value);
                                    }
                                }}
                                className={`flex-1 w-full bg-slate-900/60 border rounded-xl p-4 text-slate-200 font-mono text-sm focus:ring-1 focus:ring-indigo-500 focus:outline-none resize-none custom-scrollbar ${
                                    scriptValidationError && reviewScript.length > 0 ? 'border-red-500/60' : 'border-white/10'
                                }`}
                                placeholder="Loading script..."
                                maxLength={MAX_SCRIPT_CHARS}
                            />
                            <div className="flex justify-between text-xs px-1">
                                <span className={scriptValidationError ? 'text-red-400' : 'text-slate-400'}>
                                    {scriptValidationError || 'âœ“ Script looks good'}
                                </span>
                                <span className={reviewScript.length > MAX_SCRIPT_CHARS * 0.9 ? 'text-amber-400' : 'text-zinc-400'}>
                                    {reviewScript.length}/{MAX_SCRIPT_CHARS}
                                </span>
                            </div>
                        </div>

                        <div className="p-5 border-t border-white/10 bg-slate-900/40 flex justify-end gap-3">
                            <button
                                onClick={() => {
                                    setReviewScript(originalReviewScript.current);
                                    setIsReviewingScript(false);
                                }}
                                className="px-5 py-2.5 rounded-xl text-slate-400 hover:bg-white/5 transition-colors font-semibold text-xs"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => generateScriptAndVisuals(reviewScript)}
                                disabled={isLoading || !!scriptValidationError}
                                title={scriptValidationError || ''}
                                className="px-6 py-2.5 bg-white text-black hover:bg-slate-200 rounded-xl font-bold text-xs flex items-center gap-2 transition-all disabled:opacity-40 disabled:saturate-0"
                            >
                                {isLoading ? <Loader2 className="animate-spin" size={15} /> : <Zap size={15} fill="currentColor" />}
                                GENERATE MASTERPIECE
                            </button>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );

    return (
        <div className="min-h-screen bg-transparent text-white p-0 font-sans selection:bg-indigo-500/30 flex flex-col">
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
            {showUpgradeModal && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
                    onClick={() => setShowUpgradeModal(false)}
                >
                    <div
                        className="w-full max-w-md glass-strong border border-white/[0.12] rounded-3xl p-8 relative overflow-hidden text-center space-y-6 shadow-[0_40px_80px_rgba(0,0,0,0.8)]"
                        onClick={e => e.stopPropagation()}
                    >
                        <div className="w-14 h-14 rounded-2xl bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 flex items-center justify-center mx-auto">
                            <Sparkles size={28} />
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-white mb-1.5">Unlock HD Quality</h3>
                            <p className="text-slate-400 text-xs leading-relaxed">
                                1080p Resolution creates crisper, more professional videos. Exclusive to the <strong>Creator Plan</strong>.
                            </p>
                        </div>
                        <button
                            onClick={() => onNavigate ? onNavigate('pricing') : (window.location.href = '/?tab=pricing')}
                            className="w-full py-3.5 bg-white text-black font-bold text-xs rounded-xl hover:bg-slate-200 transition-colors"
                        >
                            Upgrade to Creator
                        </button>
                        <button
                            onClick={() => setShowUpgradeModal(false)}
                            className="text-slate-400 hover:text-white text-xs"
                        >
                            Maybe Later
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
