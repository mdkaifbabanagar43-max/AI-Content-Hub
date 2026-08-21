'use client';

import React, { useState, useRef, useEffect } from 'react';
import { UploadCloud, Scissors, Sparkles, Check, AlertCircle, Terminal, Play, Loader2, Download, Lock, Zap, MousePointerClick, LayoutTemplate, Mic, BookOpen, Heart, Smile, Wrench, Coins, ArrowRight, CheckCircle2, Video, HardDrive, Globe, Activity, X, Film, Layers, Clock, Wand2, Focus, ALargeSmall, Link2, MessageSquareOff, ListChecks } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { API_BASE_URL } from '@/lib/config';
import { LoadingState } from './ui/LoadingState';
import { Skeleton } from './ui/Skeleton';
import { handleAppError } from '@/lib/errorHandler';
import { usePermission } from '@/hooks/usePermission';
import { useAuth } from '@/context/AuthContext';

import { usePlan } from '@/context/PlanContext';
import CreditConfirmationModal from './ui/CreditConfirmationModal';
import { toast } from 'sonner';

// Types
interface ViralClip {
    title: string;
    start_time: string;
    end_time: string;
    virality_score: number;
    reason: string;
    hooks?: string[];
}


export default function ViralRepurposer({ onNavigate }: { onNavigate?: (tab: string) => void }) {
    // STATE
    const [step, setStep] = useState(1);
    const [file, setFile] = useState<File | null>(null);
    const [analyzing, setAnalyzing] = useState(false);
    const [viralClips, setViralClips] = useState<ViralClip[]>([]);
    const [selectedClip, setSelectedClip] = useState<ViralClip | null>(null);

    // Configuration State
    const [contentType, setContentType] = useState('Podcast');
    const [platform, setPlatform] = useState('shorts');
    const [clipLength, setClipLength] = useState('Medium'); // New: Duration Preference
    const [mode, setMode] = useState('podcast_stack');
    const [style, setStyle] = useState('Intense');
    // const [captionStyle, setCaptionStyle] = useState('Hormozi'); // LEGACY
    const [subtitlePreset, setSubtitlePreset] = useState('bold_viral'); // NEW
    const [hookBoost, setHookBoost] = useState(false);
    const [skipCaptions, setSkipCaptions] = useState(false);
    const [selectedCustomHook, setSelectedCustomHook] = useState<string | null>(null);
    const [resolution, setResolution] = useState('720p');

    // Hooks
    const { canUse, userPlan } = usePermission();
    const { deductCredits, refundCredits, credits, capabilities } = usePlan();
    const { user } = useAuth();

    // Capabilities Source of Truth now managed in PlanContext
    // No local fetch needed.

    // HYBRID APPROACH: Use PlanContext to derive capabilities locally to ensure instant feedback,
    // matching backend config. User requested API, but without Auth Token exposed in this scope easily,
    // local derivation using the SAME source of truth logic is safer for this specific file.
    // BUT I will implement the UI logic requested.

    // Derived Capabilities (Frontend Mirror of Backend Source of Truth)
    const canSelectRes = (res: string) => {
        if (res === '720p') return true;

        // Use Context Capabilities if loaded
        if (capabilities) {
            const maxRes = capabilities.max_resolution;
            // Normalize maxRes to string if number, or handle logic
            // Backend sends ints: 720, 1080, 2160

            if (res === '1080p') {
                return maxRes === '1080p' || maxRes === '4k' || maxRes == 1080 || maxRes >= 1080;
            }
            if (res === '4k') {
                return maxRes === '4k' || maxRes === '2160p' || maxRes == 2160 || maxRes >= 2160;
            }
            return false;
        }

        // Fallback to PlanContext UserPlan if API fetch is still loading (unlikely with centralized context)
        if (res === '1080p') return userPlan === 'creator' || userPlan === 'agency' || userPlan === 'pro';
        if (res === '4k') return userPlan === 'agency';
        return false;
    };

    // Processing State
    const [isProcessing, setIsProcessing] = useState(false);
    const [logs, setLogs] = useState<string[]>([]);
    const [resultUrl, setResultUrl] = useState<string | null>(null);
    const [gcsPath, setGcsPath] = useState<string | null>(null);

    // UI Helpers
    const [dragActive, setDragActive] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // URL Import State
    const [sourceTab, setSourceTab] = useState<'file' | 'url'>('url');
    const [videoUrl, setVideoUrl] = useState('');
    const [urlImporting, setUrlImporting] = useState(false);
    const [detectedPlatform, setDetectedPlatform] = useState<string | null>(null);

    // Hooks (Already declared above)

    // CONSTANTS
    const STEPS = [
        { num: 1, label: 'Context' },
        { num: 2, label: 'Platform' },
        { num: 3, label: 'Source' },
        { num: 4, label: 'Moments' },
        { num: 5, label: 'Style' },
        { num: 6, label: 'Generate' }
    ];

    const CONTENT_TYPES = [
        { id: 'Podcast', label: 'Podcast / Interview', icon: Mic, desc: 'Find hooks & stories', mode: 'podcast_stack' },
        { id: 'Educ', label: 'Educational', icon: BookOpen, desc: 'Extract key facts', mode: 'content_fit' },
        { id: 'Motivation', label: 'Story / Motivation', icon: Heart, desc: 'Emotional peaks', mode: 'smart_solo' },
        { id: 'Comedy', label: 'Comedy / Fun', icon: Smile, desc: 'Jokes & reactions', mode: 'smart_solo' },
        { id: 'Tutorial', label: 'Tutorial / How-To', icon: Wrench, desc: 'Actionable steps', mode: 'content_fit' },
        { id: 'Sales', label: 'Sales / Webinar', icon: Coins, desc: 'Pain points & pitch', mode: 'content_fit' },
    ];

    // --- LOGIC: PERMISSIONS & DEFAULTS ---
    useEffect(() => {
        // Enforce plan limits on mode
        if (!canUse('repurposer_modes', mode)) {
            // mode = 'center_crop'; // Don't force reset unless strictly necessary to avoid UX flicker
        }
    }, [userPlan, mode]);

    // --- HANDLERS ---

    const addLog = (msg: string) => setLogs(prev => [...prev, `> ${msg}`]);

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault(); e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
        else if (e.type === "dragleave") setDragActive(false);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault(); e.stopPropagation(); setDragActive(false);
        if (e.dataTransfer.files?.[0]) {
            setFile(e.dataTransfer.files[0]);
            // Don't auto-analyze yet, let user confirm in Step 3
        }
    };

    // --- URL PLATFORM DETECTION ---
    const detectPlatform = (url: string): string | null => {
        if (/youtube\.com|youtu\.be/i.test(url)) return 'youtube';
        if (/tiktok\.com/i.test(url)) return 'tiktok';
        if (/instagram\.com/i.test(url)) return 'instagram';
        if (/twitter\.com|x\.com/i.test(url)) return 'twitter';
        if (/facebook\.com|fb\.watch/i.test(url)) return 'facebook';
        if (/vimeo\.com/i.test(url)) return 'vimeo';
        return null;
    };

    const handleUrlChange = (url: string) => {
        setVideoUrl(url);
        setDetectedPlatform(detectPlatform(url));
    };

    const PLATFORM_LABELS: Record<string, { label: string; color: string }> = {
        youtube: { label: 'YouTube', color: 'text-red-500' },
        tiktok: { label: 'TikTok', color: 'text-cyan-400' },
        instagram: { label: 'Instagram', color: 'text-pink-500' },
        twitter: { label: 'X / Twitter', color: 'text-blue-400' },
        facebook: { label: 'Facebook', color: 'text-blue-500' },
        vimeo: { label: 'Vimeo', color: 'text-cyan-300' },
    };

    // --- URL IMPORT HANDLER ---
    const handleUrlImport = async () => {
        if (!videoUrl.trim()) {
            toast.error('Please paste a video URL.');
            return;
        }
        if (!detectedPlatform) {
            toast.error('Unsupported URL. We support YouTube, TikTok, Instagram, X, Facebook, and Vimeo.');
            return;
        }
        if (!user) {
            toast.error('Please log in to continue.');
            return;
        }

        setUrlImporting(true);
        setAnalyzing(true);
        setViralClips([]);
        setGcsPath(null);
        setLogs([`> Importing from ${PLATFORM_LABELS[detectedPlatform]?.label || detectedPlatform}...`, '> Downloading video...']);

        try {
            const token = await user.getIdToken();

            // 1. Import video from URL
            const importRes = await fetch(`${API_BASE_URL}/import-video-url`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ url: videoUrl.trim() })
            });

            if (!importRes.ok) {
                const errData = await importRes.json();
                throw new Error(errData.detail || 'Failed to import video');
            }

            const importData = await importRes.json();
            const importedGcsPath = importData.gcs_path;
            setGcsPath(importedGcsPath);
            addLog(`> Downloaded ${importData.filename} (${importData.file_size_mb} MB)`);
            addLog(`> Analyzing for ${contentType} patterns...`);

            // 2. Analyze (same flow as file upload)
            const analyzeFormData = new FormData();
            analyzeFormData.append('gcs_path', importedGcsPath);
            analyzeFormData.append('style', style);
            analyzeFormData.append('content_type', contentType);
            analyzeFormData.append('clip_length', clipLength);

            const res = await fetch(`${API_BASE_URL}/analyze-file-gcs`, {
                method: 'POST',
                body: analyzeFormData,
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!res.ok) {
                const errData = await res.json();
                let errorMessage = errData.detail || 'Analysis engine failed';
                if (typeof errData.detail !== 'string') errorMessage = JSON.stringify(errData.detail);
                throw new Error(errorMessage);
            }

            const data = await res.json();
            setViralClips(data.viral_clips);

            if (data.viral_clips.length === 0) {
                addLog('> Analysis complete, but no clips matched criteria.');
                throw new Error('No viral moments detected. Try a different style or content type.');
            }

            setSelectedClip(data.viral_clips[0]);
            addLog(`> Success! ${data.viral_clips.length} moments detected.`);
            setStep(4);

        } catch (err) {
            console.error(err);
            handleAppError(err);
        } finally {
            setUrlImporting(false);
            setAnalyzing(false);
        }
    };

    const handleAnalyzeStart = () => {
        if (file) handleAnalyze(file);
    };

    const handleAnalyze = async (uploadedFile: File) => {
        setAnalyzing(true);
        setViralClips([]);
        setGcsPath(null);
        setLogs(['> Initializing Context-Aware Engine...', `> Uploading '${uploadedFile.name}'...`]);

        try {
            if (!user) throw new Error("Please log in to continue.");
            const token = await user.getIdToken();

            // 1. Get Link
            const urlFormData = new FormData();
            urlFormData.append('filename', uploadedFile.name);
            urlFormData.append('content_type', uploadedFile.type);
            const urlRes = await fetch(`${API_BASE_URL}/get-upload-url`, {
                method: 'POST',
                body: urlFormData,
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!urlRes.ok) throw new Error("Upload handshake failed");
            const { upload_url, gcs_path } = await urlRes.json();
            setGcsPath(gcs_path);

            // 2. Upload
            await fetch(upload_url, { method: 'PUT', body: uploadedFile, headers: { 'Content-Type': uploadedFile.type } });
            addLog(`> Analyzing for ${contentType} patterns...`);

            // 3. Analyze
            // 3. Analyze
            const analyzeFormData = new FormData();
            analyzeFormData.append('gcs_path', gcs_path); // FIX: Use local variable, state is async
            analyzeFormData.append('style', style);
            analyzeFormData.append('content_type', contentType);
            analyzeFormData.append('clip_length', clipLength); // Pass preference

            const res = await fetch(`${API_BASE_URL}/analyze-file-gcs`, {
                method: 'POST',
                body: analyzeFormData,
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) {
                const errData = await res.json();
                console.error("❌ Analysis Error Details:", JSON.stringify(errData, null, 2));
                // Reuse logic or simple stringify if complex
                let errorMessage = errData.detail || 'Analysis engine failed';
                if (typeof errData.detail !== 'string') errorMessage = JSON.stringify(errData.detail);
                throw new Error(errorMessage);
            }
            const data = await res.json();

            setViralClips(data.viral_clips);

            if (data.viral_clips.length === 0) {
                addLog('> Analysis complete, but no clips matched criteria.');
                throw new Error("No viral moments detected. Try a different style or content type.");
            }

            setSelectedClip(data.viral_clips[0]);
            addLog(`> Success! ${data.viral_clips.length} moments detected.`);
            setStep(4);

        } catch (err) {
            console.error(err);
            handleAppError(err);
        } finally {
            setAnalyzing(false);
        }
    };

    // Credit Guard State
    const [showCreditModal, setShowCreditModal] = useState(false);
    const [estimatedCost, setEstimatedCost] = useState(0);

    const handleGenerateClick = () => {
        if (!selectedClip || !gcsPath) return;

        // Parse Duration
        // Format of time is usually "MM:SS" or "HH:MM:SS"
        const parseDuration = (timeStr: string) => {
            const parts = timeStr.split(':').map(Number);
            if (parts.length === 2) return parts[0] * 60 + parts[1];
            if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
            return 0;
        };

        const start = parseDuration(selectedClip.start_time);
        const end = parseDuration(selectedClip.end_time);
        const durationSeconds = end - start;
        const durationMins = Math.max(1, Math.ceil(durationSeconds / 60)); // Min 1 min

        // Cost: 10 credits per minute
        const cost = durationMins * 10;

        setEstimatedCost(cost);
        setShowCreditModal(true);
    };

    const executeGeneration = async () => {
        setShowCreditModal(false);
        const cost = estimatedCost;

        // Final Client-Side Check (Backend handles real check)
        if (!deductCredits(cost)) return;

        setIsProcessing(true);
        setResultUrl(null);
        setLogs(['> Activating Viral Engine...', `> Applying Layout: ${mode}`, '> Synching Audio/Video...']);

        // UX Simulation
        setTimeout(() => addLog('> Generating Dynamic Captions...'), 2500);
        setTimeout(() => addLog('> Rendering High-Bitrate Video...'), 5000);

        // Auth Token
        if (!user) {
            toast.error('Please log in to continue.');
            return;
        }
        const token = await user.getIdToken();

        // resolution parsing (e.g. "720p" -> 720)
        const resolutionInt = parseInt(resolution.replace('p', ''), 10) || 1080;

        try {
            const res = await fetch(`${API_BASE_URL}/repurpose-video`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    start_time: selectedClip?.start_time,
                    end_time: selectedClip?.end_time,
                    gcs_path: gcsPath,
                    style: style,
                    captionStyle: 'legacy', // Legacy fallback
                    subtitle_preset: subtitlePreset,
                    hook_boost: hookBoost,
                    custom_hook_text: selectedCustomHook,
                    title: selectedClip?.title,
                    mode,
                    resolution: resolutionInt,
                    skip_captions: skipCaptions
                })
            });

            if (!res.ok) {
                const errData = await res.json();
                console.error("❌ Backend Error Details:", JSON.stringify(errData, null, 2));

                // Handle FastAPI Validation Errors
                let errorMessage = 'Generation failed';
                if (typeof errData.detail === 'string') {
                    errorMessage = errData.detail;
                } else if (Array.isArray(errData.detail)) {
                    errorMessage = errData.detail.map((e: any) => `${e.loc.join('.')} -> ${e.msg}`).join(', ');
                } else if (typeof errData === 'object') {
                    errorMessage = JSON.stringify(errData);
                }

                throw new Error(errorMessage);
            }
            const data = await res.json();
            
            if (data.status === "processing" && data.job_id) {
                const jobId = data.job_id;
                addLog(`> Job started. Polling status...`);
                
                // Poll for completion
                let isDone = false;
                while (!isDone) {
                    await new Promise(r => setTimeout(r, 3000));
                    
                    // Fetch fresh token dynamically
                    const currentToken = user ? await user.getIdToken() : token;
                    
                    const jobRes = await fetch(`${API_BASE_URL}/api/jobs/${jobId}`, {
                        headers: { 'Authorization': `Bearer ${currentToken}` }
                    });
                    
                    if (!jobRes.ok) {
                        if (jobRes.status === 401) {
                            throw new Error("Authentication failed. Please log in again.");
                        }
                        continue;
                    }
                    
                    const jobData = await jobRes.json();
                    if (jobData.status === "completed") {
                        setResultUrl(jobData.result_url || jobData.video_url);
                        addLog('> Process Complete. Video ready.');
                        isDone = true;
                    } else if (jobData.status === "failed") {
                        throw new Error(jobData.error || "Job failed during processing");
                    }
                }
            } else {
                // Fallback if not using background tasks for some reason
                setResultUrl(data.video_url);
                addLog('> Process Complete. Video ready.');
            }

        } catch (err) {
            handleAppError(err, () => refundCredits(cost));
        } finally {
            setIsProcessing(false);
        }
    };

    // --- IMPORT ICONS ---
    // (Assuming lucide-react is available, imported at top)
    // We need to ensure we have Mic, BookOpen, Heart, Smile, Wrench, Coins imported or available.
    // If not, we might need to update imports.
    // I will assume they are imported already or I will add them to the import list if rewriting the whole file.
    // Checking previous file content: imports were: UploadCloud, Scissors, Sparkles, Check, AlertCircle, Terminal, Play, Loader2, Download, Lock, Zap, MousePointerClick, LayoutTemplate
    // Need to add: Mic, BookOpen, Heart, Smile, Wrench, Coins, ArrowRight, Video, Instagram, Youtube, Facebook...

    // RENDER STEPS
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);

    // Frontend Gatekeeper
    const isModeLocked = (targetMode: string) => {
        if (!capabilities) return false; // Loading...
        // 'smart_solo' and 'content_fit' require Smart Face Tracking (Creator+)
        if (targetMode === 'smart_solo' || targetMode === 'content_fit') {
            return !capabilities.repurposer_smart_crop;
        }
        return false;
    };

    const renderStep1 = () => (
        <div className="max-w-5xl mx-auto py-10 space-y-12">
            <div className="text-center space-y-4">
                <h2 className="text-5xl font-black text-white tracking-tighter">What are you creating?</h2>
                <p className="text-xl text-zinc-400">Context helps our AI find the perfect viral moments.</p>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
                {CONTENT_TYPES.map(type => {
                    const locked = isModeLocked(type.mode);
                    return (
                        <button
                            key={type.id}
                            onClick={() => {
                                if (locked) {
                                    setShowUpgradeModal(true);
                                    return;
                                }
                                setContentType(type.id);
                                if (canUse('repurposer_modes', type.mode)) {
                                    setMode(type.mode);
                                }
                                setStep(2);
                            }}
                            className={cn(
                                "relative p-8 rounded-3xl border text-left transition-all group overflow-hidden",
                                contentType === type.id
                                    ? "bg-zinc-900 border-pink-500 shadow-[0_0_30px_rgba(236,72,153,0.15)] scale-105"
                                    : locked
                                        ? "bg-zinc-950/50 border-zinc-800 opacity-75 hover:opacity-100 cursor-not-allowed" // Locked State
                                        : "bg-zinc-950 border-zinc-800 hover:bg-zinc-900 hover:scale-105 active:scale-95"
                            )}
                        >
                            {locked && (
                                <div className="absolute top-4 right-4 bg-zinc-800/80 p-1.5 rounded-full border border-zinc-700 backdrop-blur-sm z-10">
                                    <Lock size={14} className="text-zinc-400" />
                                </div>
                            )}

                            <div className={cn(
                                "w-14 h-14 rounded-2xl flex items-center justify-center mb-6 transition-colors",
                                contentType === type.id ? "bg-pink-500 text-white" : "bg-zinc-900 text-zinc-400 group-hover:text-pink-500"
                            )}>
                                <type.icon size={28} />
                            </div>
                            <h3 className={cn("text-xl font-bold mb-2", contentType === type.id ? "text-white" : "text-zinc-400")}>{type.label}</h3>
                            <p className="text-xs text-zinc-400">{type.desc}</p>

                            {locked && (
                                <div className="mt-3 inline-flex items-center gap-1.5 text-[10px] font-bold text-pink-500 bg-pink-500/10 px-2 py-1 rounded-md border border-pink-500/20">
                                    <Sparkles size={10} /> Creator Plan
                                </div>
                            )}
                        </button>
                    );
                })}
            </div>

            {/* UPGRADE MODAL (Simple Inline for now) */}
            <AnimatePresence>
                {showUpgradeModal && (
                    <motion.div
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
                        onClick={() => setShowUpgradeModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.95 }} animate={{ scale: 1 }} exit={{ scale: 0.95 }}
                            className="w-full max-w-md bg-zinc-900 border border-zinc-700 rounded-3xl p-8 relative overflow-hidden"
                            onClick={e => e.stopPropagation()}
                        >
                            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500" />
                            <div className="flex flex-col items-center text-center space-y-6">
                                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-pink-500 to-purple-600 flex items-center justify-center shadow-lg shadow-pink-500/25">
                                    <Sparkles size={32} className="text-white" />
                                </div>
                                <div>
                                    <h3 className="text-2xl font-black text-white mb-2">Unlock Smart Magic</h3>
                                    <p className="text-zinc-400 text-sm">
                                        Active Speaker Detection & Content Fit cropping are exclusive to the <strong>Creator Plan</strong>.
                                    </p>
                                </div>
                                <button
                                    onClick={() => onNavigate ? onNavigate('pricing') : (window.location.href = '/?tab=pricing')}
                                    className="w-full py-4 bg-white text-black font-bold rounded-xl hover:bg-zinc-200 transition-colors"
                                >
                                    Upgrade to Creator
                                </button>
                                <button
                                    onClick={() => setShowUpgradeModal(false)}
                                    className="text-zinc-400 hover:text-white text-sm"
                                >
                                    Maybe Later
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );

    const renderStep2 = () => (
        <div className="max-w-4xl mx-auto py-10 space-y-12">
            <div className="text-center space-y-4">
                <h2 className="text-5xl font-black text-white tracking-tighter">Target Platform</h2>
                <p className="text-xl text-zinc-400">Where will this video live?</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[
                    { id: 'shorts', label: 'YouTube Shorts', color: 'from-red-500 to-red-600' },
                    { id: 'tiktok', label: 'TikTok', color: 'from-cyan-400 to-purple-500' },
                    { id: 'reels', label: 'Instagram Reels', color: 'from-pink-500 to-orange-500' }
                ].map(p => (
                    <button
                        key={p.id}
                        onClick={() => { setPlatform(p.id); setStep(3); }}
                        className="relative h-64 rounded-[30px] border border-zinc-800 bg-zinc-950 overflow-hidden group hover:scale-105 transition-all"
                    >
                        <div className={cn("absolute inset-0 bg-gradient-to-br opacity-0 group-hover:opacity-10 transition-opacity", p.color)} />
                        <div className="absolute inset-0 flex items-center justify-center">
                            <h3 className="text-2xl font-black text-white">{p.label}</h3>
                        </div>
                    </button>
                ))}
            </div>
            <div className="flex justify-center">
                <button onClick={() => setStep(1)} className="text-zinc-400 hover:text-white mt-8">Back</button>
                {/* Forward button added implicitly by selection above, but let's add next if needed? No, selection triggers next. 
                    User requested Clip Length here. Let's add it below platform.
                */}
            </div>

            {/* CLIP LENGTH SELECTOR */}
            <div className="space-y-4 text-center animate-in slide-in-from-bottom delay-100">
                <h3 className="text-2xl font-bold text-white">Target Length</h3>
                <div className="flex justify-center gap-4">
                    {['Short (15-30s)', 'Medium (30-60s)', 'Long (60-90s)'].map(l => {
                        const val = l.split(' ')[0];
                        return (
                            <button
                                key={val}
                                onClick={() => setClipLength(val)}
                                className={cn(
                                    "px-6 py-3 rounded-xl font-bold border transition-all",
                                    clipLength === val ? "bg-white text-black border-white" : "bg-zinc-950 text-zinc-400 border-zinc-800 hover:border-zinc-600"
                                )}
                            >
                                {l}
                            </button>
                        );
                    })}
                </div>
                <p className="text-zinc-400 text-sm">Longer clips perform better for podcasts & interviews.</p>
            </div>
        </div>
    );

    const RepurposerSkeleton = () => (
        <div className="w-full max-w-6xl mx-auto space-y-8">
            {/* Header */}
            <div className="flex items-center gap-4 border-b border-zinc-800 pb-6">
                <Skeleton className="w-16 h-16 rounded-xl" />
                <div className="space-y-2">
                    <Skeleton className="h-8 w-64" />
                    <Skeleton className="h-4 w-40" />
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left: Main Video Placeholder */}
                <div className="lg:col-span-2 space-y-4">
                    <div className="aspect-[9/16] max-h-[500px] rounded-3xl bg-zinc-900/50 overflow-hidden relative border border-zinc-800 mx-auto">
                        <Skeleton className="absolute inset-0 w-full h-full opacity-20" />
                        {/* Fake timeline bars */}
                        <div className="absolute bottom-6 left-6 right-6 flex gap-1 h-12 items-end">
                            {[...Array(20)].map((_, i) => (
                                <Skeleton key={i} className="flex-1 rounded-sm" style={{ height: `${Math.random() * 80 + 20}%` }} />
                            ))}
                        </div>
                    </div>
                </div>

                {/* Right: Clip Candidates */}
                <div className="space-y-4">
                    <div className="flex justify-between items-center">
                        <Skeleton className="h-4 w-32" />
                        <Skeleton className="h-4 w-12" />
                    </div>
                    {[1, 2, 3].map(i => (
                        <div key={i} className="p-4 rounded-xl border border-zinc-800 bg-zinc-900/30 flex gap-4">
                            <Skeleton className="w-20 h-24 rounded-lg shrink-0" />
                            <div className="space-y-2 flex-1 pt-2">
                                <Skeleton className="h-4 w-3/4" />
                                <Skeleton className="h-3 w-1/2" />
                                <Skeleton className="h-6 w-16 rounded-full mt-2" />
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );

    const renderStep3 = () => (
        <div className="max-w-4xl mx-auto py-10 min-h-[50vh] flex flex-col">
            {analyzing ? (
                <div className="flex-1 flex flex-col items-center justify-center">
                    <LoadingState
                        steps={[
                            sourceTab === 'url' ? `Importing from ${PLATFORM_LABELS[detectedPlatform || '']?.label || 'URL'}...` : `Uploading '${file?.name}'...`,
                            "Analyzing conversation flow...",
                            "Detecting anchor moments...",
                            "Scoring for retention...",
                            "Selecting top clips..."
                        ]}
                        layout={<RepurposerSkeleton />}
                    />
                </div>
            ) : viralClips.length > 0 ? (
                // ANALYSIS COMPLETE
                <div className="space-y-8 animate-in slide-in-from-bottom">
                    <div className="text-center space-y-2">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/10 text-green-400 text-xs font-bold border border-green-500/20 mb-4">
                            <CheckCircle2 size={12} /> Analysis Complete
                        </div>
                        <h2 className="text-4xl font-black text-white">We found {viralClips.length} gems.</h2>
                        <p className="text-zinc-400">Based on your video type, AI identified high-retention moments.</p>
                    </div>
                    <div className="flex justify-center pt-8">
                        <button onClick={() => setStep(4)} className="px-10 py-4 bg-white text-black font-bold rounded-2xl hover:bg-zinc-200 flex items-center gap-2">
                            Review Moments <ArrowRight size={20} />
                        </button>
                    </div>
                </div>
            ) : (
                // UPLOAD STATE
                <div className="flex-1 flex flex-col items-center justify-center gap-6 animate-in">
                    <div className="text-center">
                        <h2 className="text-2xl font-bold text-white tracking-tight">Add Your Video</h2>
                        <p className="text-sm text-zinc-600 mt-1">Paste a link or upload a local file to begin AI analysis</p>
                    </div>

                    {/* Source Tabs — Segmented control */}
                    <div className="flex bg-[#121215] rounded-lg p-1 border border-white/[0.07]">
                        <button
                            onClick={() => setSourceTab('file')}
                            className={cn(
                                'flex items-center gap-2 px-4 h-8 rounded-md text-xs font-medium transition-all',
                                sourceTab === 'file' ? 'bg-white/[0.09] text-white' : 'text-zinc-600 hover:text-zinc-300'
                            )}
                        >
                            <UploadCloud size={13} /> Upload File
                        </button>
                        <button
                            onClick={() => setSourceTab('url')}
                            className={cn(
                                'flex items-center gap-2 px-4 h-8 rounded-md text-xs font-medium transition-all',
                                sourceTab === 'url' ? 'bg-white/[0.09] text-white' : 'text-zinc-600 hover:text-zinc-300'
                            )}
                        >
                            <Link2 size={13} /> Paste URL
                        </button>
                    </div>

                    {sourceTab === 'file' ? (
                        <>
                            {/* Minimal Dashed Drop Zone */}
                            <div
                                className={cn(
                                    'w-full max-w-xl rounded-xl border border-dashed flex flex-col items-center justify-center cursor-pointer transition-all duration-200 py-14',
                                    dragActive
                                        ? 'border-indigo-500 bg-indigo-500/[0.05]'
                                        : 'border-zinc-700 bg-zinc-950/40 hover:border-zinc-500 hover:bg-zinc-950/60'
                                )}
                                onDragEnter={handleDrag} onDragLeave={handleDrag} onDragOver={handleDrag} onDrop={handleDrop}
                                onClick={() => fileInputRef.current?.click()}
                            >
                                {!file ? (
                                    <div className="flex flex-col items-center gap-3 text-center">
                                        <div className="w-12 h-12 rounded-xl bg-white/[0.04] border border-white/[0.07] flex items-center justify-center">
                                            <UploadCloud size={20} className="text-zinc-500" />
                                        </div>
                                        <div>
                                            <p className="text-sm font-medium text-zinc-300">Drop video here, or <span className="text-indigo-400">browse</span></p>
                                            <p className="text-xs font-mono text-zinc-700 mt-1">MAX 2GB · MP4 / MOV</p>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="flex flex-col items-center gap-3">
                                        <div className="w-10 h-10 rounded-full bg-emerald-600/20 border border-emerald-600/40 flex items-center justify-center">
                                            <Check size={16} className="text-emerald-400" />
                                        </div>
                                        <p className="text-sm font-medium text-white">{file.name}</p>
                                        <button onClick={(e) => { e.stopPropagation(); setFile(null); }} className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors">× Remove</button>
                                    </div>
                                )}
                                <input ref={fileInputRef} type="file" className="hidden" onChange={(e) => { if (e.target.files?.[0]) setFile(e.target.files[0]) }} accept="video/*" />
                            </div>

                            <div className="flex items-center gap-3">
                                <button onClick={() => setStep(2)} className="h-9 px-4 text-xs font-medium text-zinc-500 hover:text-white transition-colors">← Back</button>
                                <button
                                    onClick={handleAnalyzeStart}
                                    disabled={!file}
                                    className="h-9 px-5 bg-white text-black font-semibold text-xs rounded-lg hover:bg-zinc-200 transition-colors flex items-center gap-2 disabled:opacity-40 disabled:saturate-0"
                                >
                                    Start AI Analysis <Sparkles size={13} />
                                </button>
                            </div>
                        </>
                    ) : (
                        /* URL IMPORT TAB */
                        <>
                            <div className="w-full max-w-xl space-y-3">
                                {/* URL Input Bar */}
                                <div className="relative">
                                    {detectedPlatform && (
                                        <div className={cn(
                                            'absolute left-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5 px-2 py-1 rounded-md bg-black/40 border border-white/[0.06] text-[10px] font-bold',
                                            PLATFORM_LABELS[detectedPlatform]?.color || 'text-zinc-400'
                                        )}>
                                            <Globe size={10} />
                                            {PLATFORM_LABELS[detectedPlatform]?.label}
                                        </div>
                                    )}
                                    <input
                                        type="text"
                                        value={videoUrl}
                                        onChange={(e) => handleUrlChange(e.target.value)}
                                        placeholder="Paste YouTube, TikTok, Instagram, or X link..."
                                        className={cn(
                                            'w-full h-12 bg-[#121215] border border-white/[0.08] rounded-xl text-sm text-white placeholder:text-zinc-700 focus:outline-none focus:border-white/[0.18] transition-colors',
                                            detectedPlatform ? 'pl-28 pr-4' : 'px-4'
                                        )}
                                    />
                                </div>

                                {/* Platform badges */}
                                <div className="flex items-center gap-2 flex-wrap">
                                    {Object.entries(PLATFORM_LABELS).map(([key, { label, color }]) => (
                                        <span key={key} className={cn('text-[10px] font-medium px-2 py-1 rounded bg-white/[0.03] border border-white/[0.06]', color)}>
                                            {label}
                                        </span>
                                    ))}
                                </div>
                            </div>

                            <div className="flex items-center gap-3">
                                <button onClick={() => setStep(2)} className="h-9 px-4 text-xs font-medium text-zinc-500 hover:text-white transition-colors">← Back</button>
                                <button
                                    onClick={handleUrlImport}
                                    disabled={!videoUrl.trim() || !detectedPlatform || urlImporting}
                                    className="h-9 px-5 bg-white text-black font-semibold text-xs rounded-lg hover:bg-zinc-200 transition-colors flex items-center gap-2 disabled:opacity-40 disabled:saturate-0"
                                >
                                    {urlImporting ? <><Loader2 size={13} className="animate-spin" /> Importing...</> : <>Import & Analyze <Sparkles size={13} /></>}
                                </button>
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    );

    const renderStep4 = () => (
        <div className="max-w-6xl mx-auto py-6 h-[calc(100vh-150px)] flex gap-6">
            {/* Left: Clips List */}
            <div className="w-72 shrink-0 flex flex-col gap-3">
                <div>
                    <h2 className="text-base font-bold text-white">Viral Moments</h2>
                    <p className="text-xs text-zinc-600 font-mono mt-0.5">{viralClips.length} clips detected</p>
                </div>
                <div className="flex-1 overflow-y-auto custom-scrollbar space-y-2 pr-1">
                    {viralClips.map((clip, i) => (
                        <div
                            key={i}
                            onClick={() => setSelectedClip(clip)}
                            className={cn(
                                'p-4 rounded-xl border cursor-pointer transition-all duration-150',
                                selectedClip === clip
                                    ? 'bg-[#121215] border-indigo-500/60 ring-1 ring-indigo-500/30'
                                    : 'bg-[#121215] border-white/[0.07] hover:border-white/[0.14]'
                            )}
                        >
                            <div className="flex items-center justify-between mb-2">
                                <span className={cn(
                                    'text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider',
                                    selectedClip === clip ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30' : 'bg-white/[0.04] text-zinc-600 border border-white/[0.06]'
                                )}>
                                    Clip #{i + 1}
                                </span>
                                <span className="text-[10px] font-mono text-zinc-600">{clip.start_time}–{clip.end_time || '??'}</span>
                            </div>
                            <h3 className={cn('text-[12px] font-semibold mb-1.5 leading-snug', selectedClip === clip ? 'text-white' : 'text-zinc-400')}>{clip.title}</h3>
                            {/* Virality Score */}
                            <div className="flex items-center gap-2">
                                <div className="flex-1 h-[2px] bg-zinc-800 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-indigo-500 rounded-full transition-all"
                                        style={{ width: `${Math.min(100, (clip.virality_score / 10) * 100)}%` }}
                                    />
                                </div>
                                <span className="text-[10px] font-mono font-bold text-indigo-400">{clip.virality_score}/10</span>
                            </div>
                        </div>
                    ))}
                </div>
                <button onClick={() => setStep(3)} className="text-zinc-500 hover:text-white font-bold py-2 transition-colors flex items-center justify-center gap-2 bg-zinc-900 rounded-xl hover:bg-zinc-800">
                    <ArrowRight size={16} className="rotate-180" /> Back to Import
                </button>
            </div>

            {/* Right: Preview (Placeholder for trimming) */}
            <div className="flex-1 bg-black rounded-[40px] border border-zinc-800 flex flex-col relative overflow-hidden shadow-2xl">
                {/* Decorative */}
                <div className="absolute inset-0 bg-gradient-to-tr from-pink-500/10 via-transparent to-purple-500/10 pointer-events-none" />

                {/* Inner Scrollable Container */}
                <div className="w-full h-full overflow-y-auto custom-scrollbar flex flex-col p-10 relative z-10 text-center">
                    <div className="w-full max-w-lg space-y-8 m-auto">
                    <div className="w-24 h-24 rounded-full bg-zinc-950 flex items-center justify-center mx-auto border border-zinc-800 shadow-xl relative group">
                        <div className="absolute inset-0 bg-pink-500/20 blur-2xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity"></div>
                        <Scissors size={40} className="text-zinc-400 relative z-10" />
                    </div>
                    
                    <div>
                        <h3 className="text-3xl font-black text-white mb-3">{selectedClip?.title || "Select a Moment"}</h3>
                        <p className="text-zinc-400 text-[15px] max-w-sm mx-auto">
                            {selectedClip ? "Review the AI's selection and choose a hook to boost retention." : "Choose a viral moment from the list on the left to continue."}
                        </p>
                    </div>
                        
                    {selectedClip?.hooks && selectedClip.hooks.length > 0 && (
                        <div className="bg-zinc-900/60 border border-zinc-800 rounded-3xl p-6 text-left shadow-lg backdrop-blur-sm">
                            <div className="mb-4 flex flex-col gap-1.5">
                                <h4 className="text-sm font-black text-white uppercase tracking-wider flex items-center gap-2">
                                    <Sparkles size={16} className="text-pink-500" />
                                    A/B Test Hooks <span className="text-xs font-medium text-zinc-500 bg-zinc-950 px-2 py-0.5 rounded-full normal-case">(Optional)</span>
                                </h4>
                                <p className="text-xs font-medium text-zinc-400">Select a hook to overlay on the first 3 seconds of the video.</p>
                            </div>
                            
                            <div className="space-y-3">
                                {selectedClip.hooks.map((hook, idx) => {
                                    const isSelected = selectedCustomHook === hook;
                                    return (
                                        <div 
                                            key={idx}
                                            onClick={() => setSelectedCustomHook(isSelected ? null : hook)}
                                            className={cn(
                                                "p-4 rounded-2xl border text-sm cursor-pointer transition-all flex items-start gap-4 group",
                                                isSelected
                                                    ? "bg-pink-500/10 border-pink-500 text-white shadow-md shadow-pink-500/10" 
                                                    : "bg-zinc-950 border-zinc-800 text-zinc-300 hover:border-zinc-600 hover:bg-zinc-900"
                                            )}
                                        >
                                            <div className={cn(
                                                "w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 mt-0.5 transition-colors",
                                                isSelected ? "border-pink-500" : "border-zinc-700 group-hover:border-zinc-500"
                                            )}>
                                                {isSelected && <div className="w-2.5 h-2.5 bg-pink-500 rounded-full" />}
                                            </div>
                                            <div className="flex-1 leading-relaxed font-medium">
                                                "{hook}"
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>
                        </div>
                    )}
                    
                    {selectedClip && (
                        <button 
                            onClick={() => setStep(5)} 
                            className="w-full py-5 bg-white text-black font-black text-[15px] rounded-2xl hover:bg-zinc-200 transition-all active:scale-[0.98] shadow-[0_10px_30px_rgba(255,255,255,0.15)] flex items-center justify-center gap-2 mt-4"
                        >
                            Confirm & Continue <ArrowRight size={18} />
                        </button>
                    )}
                </div>
                </div>
            </div>
        </div>
    );

    const renderStep5 = () => {
        // Preset Definitions
        const PRESETS = [
            { id: 'bold_viral', label: 'Bold Viral', desc: 'Shorts & Reels', locked: false },
            { id: 'repurpose_pro', label: 'Repurpose Pro', desc: 'Big Yellow Highlights', locked: false },
            { id: 'podcast_clean', label: 'Podcast Clean', desc: 'Minimal & Pro', locked: false },
            { id: 'hook_focus', label: 'Hook Focus', desc: 'Max Retention', locked: !canUse('all_presets', 'hook_focus') }, // Assume this capability key exists or check plan directly
            { id: 'minimal', label: 'Minimal Brand', desc: 'Agency Style', locked: !canUse('all_presets', 'minimal') },
        ];

        // Manual Plan Check for safety if capabilities not granular enough
        const isPresetLocked = (pid: string) => {
            if (pid === 'bold_viral' || pid === 'podcast_clean' || pid === 'repurpose_pro') return false;
            // Creator/Agency get all
            if (userPlan === 'creator' || userPlan === 'agency' || userPlan === 'pro') return false;
            return true; // Starter cannot use focus/minimal
        };

        const isHookBoostLocked = () => {
            if (userPlan === 'creator' || userPlan === 'agency' || userPlan === 'pro') return false;
            return true;
        };

        return (
            <div className="max-w-5xl mx-auto py-10 space-y-10">
                {/* Premium Header with Gradient */}
                <div className="text-center space-y-4 relative">
                    <div className="absolute -top-6 left-1/2 -translate-x-1/2 w-32 h-32 bg-gradient-to-r from-pink-500/20 via-purple-500/20 to-blue-500/20 rounded-full blur-3xl"></div>
                    <div className="inline-flex items-center gap-2 px-4 py-2 bg-zinc-900/80 border border-zinc-800 rounded-full text-sm backdrop-blur-md">
                        <span className="w-2 h-2 bg-gradient-to-r from-pink-500 to-purple-500 rounded-full animate-pulse"></span>
                        <span className="text-zinc-400">Step 5 of 6</span>
                    </div>
                    <h2 className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white via-white to-zinc-400 tracking-tighter">Style & Vibe</h2>
                    <p className="text-xl text-zinc-400">Customize the look of your viral short</p>
                </div>

                {/* Two-Column Layout: Options + Preview */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* LEFT COLUMN: Options */}
                    <div className="space-y-8">
                        {/* Crop Mode Section */}
                        <div className="space-y-4">
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-pink-500/20 to-purple-500/20 flex items-center justify-center">
                                    <Focus size={16} className="text-pink-400" />
                                </div>
                                <label className="text-sm font-bold text-white uppercase tracking-widest">Crop Mode</label>
                            </div>

                            {/* Center Crop Card */}
                            <div
                                onClick={() => setMode('center_crop')}
                                className={cn(
                                    "p-5 rounded-2xl border cursor-pointer transition-all duration-300 group relative overflow-hidden",
                                    mode === 'center_crop'
                                        ? "bg-gradient-to-br from-pink-500/10 to-purple-500/10 border-pink-500 shadow-[0_0_20px_rgba(236,72,153,0.15)] ring-1 ring-pink-500"
                                        : "bg-slate-900/50 border-white/5 hover:border-white/10 hover:bg-slate-900/80"
                                )}
                            >
                                <div className="flex items-start gap-4">
                                    <div className="w-14 h-24 bg-black rounded-xl border-2 border-zinc-700 flex items-center justify-center shrink-0 overflow-hidden">
                                        <div className={cn("w-10 h-10 rounded-full border-2 flex items-center justify-center transition-colors", mode === 'center_crop' ? "border-pink-500 bg-pink-500/20" : "border-zinc-600")}>
                                            <div className={cn("w-4 h-4 rounded-full", mode === 'center_crop' ? "bg-pink-500" : "bg-zinc-600")}></div>
                                        </div>
                                    </div>
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                            <h3 className={cn("font-bold text-lg", mode === 'center_crop' ? "text-white" : "text-zinc-300")}>Center Crop</h3>
                                            {mode === 'center_crop' && <CheckCircle2 size={18} className="text-pink-500" />}
                                        </div>
                                        <p className="text-sm text-zinc-400">Best for solo speakers. Focuses on the main subject.</p>
                                        <div className="flex flex-wrap gap-2 mt-3">
                                            <span className="text-xs px-2 py-1 bg-zinc-800/80 rounded-full text-zinc-400">Vlogs</span>
                                            <span className="text-xs px-2 py-1 bg-zinc-800/80 rounded-full text-zinc-400">Solo Talks</span>
                                            <span className="text-xs px-2 py-1 bg-zinc-800/80 rounded-full text-zinc-400">Tutorials</span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Podcast Stack Card */}
                            <div
                                onClick={() => setMode('podcast_stack')}
                                className={cn(
                                    "p-5 rounded-2xl border cursor-pointer transition-all duration-300 group relative overflow-hidden",
                                    mode === 'podcast_stack'
                                        ? "bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border-blue-500 shadow-[0_0_20px_rgba(59,130,246,0.15)] ring-1 ring-blue-500"
                                        : "bg-slate-900/50 border-white/5 hover:border-white/10 hover:bg-slate-900/80"
                                )}
                            >
                                <div className="flex items-start gap-4">
                                    <div className="w-14 h-24 bg-black rounded-xl border-2 border-zinc-700 flex flex-col shrink-0 overflow-hidden">
                                        <div className={cn("flex-1 flex items-center justify-center border-b", mode === 'podcast_stack' ? "bg-blue-500/10 border-blue-500/40" : "bg-zinc-800 border-zinc-700")}>
                                            <div className={cn("w-5 h-5 rounded-full", mode === 'podcast_stack' ? "bg-blue-500/60" : "bg-zinc-600")}></div>
                                        </div>
                                        <div className={cn("flex-1 flex items-center justify-center", mode === 'podcast_stack' ? "bg-cyan-500/10" : "bg-zinc-800")}>
                                            <div className={cn("w-5 h-5 rounded-full", mode === 'podcast_stack' ? "bg-cyan-500/60" : "bg-zinc-600")}></div>
                                        </div>
                                    </div>
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                            <h3 className={cn("font-bold text-lg", mode === 'podcast_stack' ? "text-white" : "text-zinc-300")}>Podcast Stack</h3>
                                            {mode === 'podcast_stack' && <CheckCircle2 size={18} className="text-blue-500" />}
                                        </div>
                                        <p className="text-sm text-zinc-400">Best for interviews. Shows both speakers stacked vertically.</p>
                                        <div className="flex flex-wrap gap-2 mt-3">
                                            <span className="text-xs px-2 py-1 bg-zinc-800/80 rounded-full text-zinc-400">Podcasts</span>
                                            <span className="text-xs px-2 py-1 bg-zinc-800/80 rounded-full text-zinc-400">Interviews</span>
                                            <span className="text-xs px-2 py-1 bg-zinc-800/80 rounded-full text-zinc-400">Debates</span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Viral Split Card */}
                            <div
                                onClick={() => setMode('viral_split')}
                                className={cn(
                                    "p-5 rounded-2xl border cursor-pointer transition-all duration-300 group relative overflow-hidden",
                                    mode === 'viral_split'
                                        ? "bg-gradient-to-br from-purple-500/10 to-pink-500/10 border-purple-500 shadow-[0_0_20px_rgba(168,85,247,0.15)] ring-1 ring-purple-500"
                                        : "bg-slate-900/50 border-white/5 hover:border-white/10 hover:bg-slate-900/80"
                                )}
                            >
                                <div className="flex items-start gap-4">
                                    <div className="w-14 h-24 bg-black rounded-xl border-2 border-zinc-700 flex flex-col shrink-0 overflow-hidden">
                                        <div className={cn("flex-1 flex items-center justify-center border-b", mode === 'viral_split' ? "bg-purple-500/10 border-purple-500/40" : "bg-zinc-800 border-zinc-700")}>
                                            <div className={cn("w-5 h-5 rounded-full", mode === 'viral_split' ? "bg-purple-500/60" : "bg-zinc-600")}></div>
                                        </div>
                                        <div className={cn("flex-1 bg-gradient-to-br from-indigo-500/20 to-purple-500/20", mode === 'viral_split' ? "opacity-100" : "opacity-30 grayscale")}>
                                        </div>
                                    </div>
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                            <h3 className={cn("font-bold text-lg", mode === 'viral_split' ? "text-white" : "text-zinc-300")}>Viral Split</h3>
                                            {mode === 'viral_split' && <CheckCircle2 size={18} className="text-purple-500" />}
                                        </div>
                                        <p className="text-sm text-zinc-400">Repurpose.io Style: Speaker on top, dynamic background on bottom.</p>
                                        <div className="flex flex-wrap gap-2 mt-3">
                                            <span className="text-xs px-2 py-1 bg-purple-500/20 text-purple-300 rounded-full">High Retention</span>
                                            <span className="text-xs px-2 py-1 bg-zinc-800/80 rounded-full text-zinc-400">TikTok/Shorts</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            {/* Dynamic Cut Card */}
                            <div
                                onClick={() => setMode('dynamic_cut')}
                                className={cn(
                                    "p-5 rounded-2xl border cursor-pointer transition-all duration-300 group relative overflow-hidden",
                                    mode === 'dynamic_cut'
                                        ? "bg-gradient-to-br from-emerald-500/10 to-teal-500/10 border-emerald-500 shadow-[0_0_20px_rgba(16,185,129,0.15)] ring-1 ring-emerald-500"
                                        : "bg-slate-900/50 border-white/5 hover:border-white/10 hover:bg-slate-900/80"
                                )}
                            >
                                <div className="flex items-start gap-4">
                                    <div className="w-14 h-24 bg-black rounded-xl border-2 border-zinc-700 flex flex-col shrink-0 overflow-hidden relative">
                                        {/* Dynamic visualization */}
                                        <div className={cn("absolute inset-0 transition-opacity duration-1000", mode === 'dynamic_cut' ? "opacity-100 animate-pulse bg-emerald-500/20" : "opacity-0")}></div>
                                        <div className={cn("flex-1 flex items-center justify-center border-b z-10", mode === 'dynamic_cut' ? "bg-emerald-500/10 border-emerald-500/40" : "bg-zinc-800 border-zinc-700")}>
                                            <div className={cn("w-5 h-5 rounded-full transition-transform", mode === 'dynamic_cut' ? "bg-emerald-500/60 scale-125" : "bg-zinc-600")}></div>
                                        </div>
                                        <div className={cn("flex-1 flex items-center justify-center z-10", mode === 'dynamic_cut' ? "bg-teal-500/10" : "bg-zinc-800")}>
                                            <div className={cn("w-5 h-5 rounded-full", mode === 'dynamic_cut' ? "bg-teal-500/60" : "bg-zinc-600")}></div>
                                        </div>
                                    </div>
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                            <h3 className={cn("font-bold text-lg flex items-center gap-2", mode === 'dynamic_cut' ? "text-emerald-400" : "text-zinc-300")}>
                                                Dynamic Cut <Sparkles size={14} className="text-emerald-500" />
                                            </h3>
                                            {mode === 'dynamic_cut' && <CheckCircle2 size={18} className="text-emerald-500" />}
                                        </div>
                                        <p className="text-sm text-zinc-400">OpusClip Style: Auto-punches between stacked views and solo tracking to keep retention high.</p>
                                        <div className="flex flex-wrap gap-2 mt-3">
                                            <span className="text-xs px-2 py-1 bg-emerald-500/20 text-emerald-400 font-bold rounded-full border border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.3)]">NEW: Opus-Grade</span>
                                            <span className="text-xs px-2 py-1 bg-zinc-800/80 rounded-full text-zinc-400">Max Retention</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* RIGHT COLUMN: Live Preview */}
                    <div className="space-y-4">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-green-500/20 to-emerald-500/20 flex items-center justify-center">
                                <Sparkles size={16} className="text-green-400" />
                            </div>
                            <label className="text-sm font-bold text-white uppercase tracking-widest">Live Preview</label>
                        </div>

                        <div className="p-6 rounded-3xl bg-gradient-to-br from-zinc-900 to-zinc-950 border border-zinc-800 relative overflow-hidden">
                            {/* Decorative gradient */}
                            <div className={cn("absolute top-0 left-0 w-full h-1 bg-gradient-to-r", mode === 'center_crop' ? "from-pink-500 to-purple-500" : "from-blue-500 to-cyan-500")}></div>

                            <div className="flex items-center gap-3 mb-4">
                                <div className={cn(
                                    "w-10 h-10 rounded-xl flex items-center justify-center",
                                    mode === 'center_crop' ? "bg-pink-500/20 text-pink-400" : "bg-blue-500/20 text-blue-400"
                                )}>
                                    {mode === 'center_crop' ? <Focus size={18} /> : <Layers size={18} />}
                                </div>
                                <div>
                                    <p className="text-sm font-bold text-white">{mode === 'center_crop' ? 'Center Crop' : 'Podcast Stack'}</p>
                                    <p className="text-xs text-zinc-400">{mode === 'center_crop' ? 'Single speaker focus • 9:16' : 'Dual speaker layout • 9:16'}</p>
                                </div>
                            </div>

                            {/* Phone Mockup */}
                            <div className="relative mx-auto" style={{ width: '180px' }}>
                                <div className="aspect-[9/18] bg-black rounded-3xl border-4 border-zinc-700 relative overflow-hidden shadow-2xl">
                                    {/* Notch */}
                                    <div className="absolute top-2 left-1/2 -translate-x-1/2 w-16 h-4 bg-zinc-900 rounded-full z-10"></div>

                                    {/* Preview Content */}
                                    <div className="h-full pt-6">
                                        {mode === 'center_crop' && (
                                            <div className="h-full flex items-center justify-center bg-gradient-to-b from-zinc-900 to-zinc-950">
                                                <div className="w-20 h-20 rounded-full border-4 border-pink-500/50 flex items-center justify-center animate-pulse">
                                                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-pink-500/40 to-purple-500/40"></div>
                                                </div>
                                            </div>
                                        )}
                                        {mode === 'podcast_stack' && (
                                            <div className="flex flex-col h-full">
                                                <div className="flex-1 bg-gradient-to-b from-zinc-900 to-zinc-800 flex items-center justify-center border-b-2 border-black">
                                                    <div className="text-center">
                                                        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500/40 to-blue-600/40 mx-auto mb-1"></div>
                                                        <span className="text-[10px] font-bold text-blue-400">Speaker A</span>
                                                    </div>
                                                </div>
                                                <div className="flex-1 bg-gradient-to-b from-zinc-800 to-zinc-900 flex items-center justify-center">
                                                    <div className="text-center">
                                                        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-cyan-500/40 to-cyan-600/40 mx-auto mb-1"></div>
                                                        <span className="text-[10px] font-bold text-cyan-400">Speaker B</span>
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    {/* Captions Overlay */}
                                    <div className="absolute bottom-6 inset-x-3 text-center">
                                        <div className="inline-block px-3 py-1.5 bg-black/90 rounded-lg">
                                            <span className="text-[10px] font-black text-yellow-400 uppercase tracking-wide">
                                                Captions Here
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                {/* Shadow under phone */}
                                <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 w-32 h-4 bg-black/40 rounded-full blur-xl"></div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Controls Section */}
                <div className="space-y-8">
                    {/* Section Divider */}
                    <div className="flex items-center gap-4">
                        <div className="h-px flex-1 bg-gradient-to-r from-transparent via-zinc-800 to-transparent"></div>
                        <span className="text-xs text-zinc-400 uppercase tracking-widest">Styling Options</span>
                        <div className="h-px flex-1 bg-gradient-to-r from-transparent via-zinc-800 to-transparent"></div>
                    </div>

                    {/* SUBTITLE PRESETS - Enhanced Grid */}
                    <div className="space-y-4">
                        {/* Skip Captions Toggle */}
                        <div
                            onClick={() => setSkipCaptions(!skipCaptions)}
                            className={cn(
                                "p-4 rounded-2xl border transition-all cursor-pointer relative overflow-hidden",
                                skipCaptions
                                    ? "bg-amber-500/10 border-amber-500/40"
                                    : "bg-slate-900/50 border-slate-800 hover:border-slate-600"
                            )}
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className={cn(
                                        "w-9 h-9 rounded-lg flex items-center justify-center transition-all",
                                        skipCaptions ? "bg-amber-500/20 text-amber-400" : "bg-slate-800 text-slate-400"
                                    )}>
                                        <MessageSquareOff size={18} />
                                    </div>
                                    <div>
                                        <h4 className={cn("font-bold text-sm", skipCaptions ? "text-white" : "text-slate-400")}>
                                            Skip Captions
                                        </h4>
                                        <p className="text-xs text-slate-500">Video already has subtitles / captions</p>
                                    </div>
                                </div>
                                <div className={cn(
                                    "w-12 h-6 rounded-full p-0.5 transition-all relative",
                                    skipCaptions ? "bg-amber-500" : "bg-slate-800"
                                )}>
                                    <div className={cn(
                                        "w-5 h-5 rounded-full bg-white shadow-md transition-transform",
                                        skipCaptions ? "translate-x-6" : "translate-x-0"
                                    )} />
                                </div>
                            </div>
                        </div>

                        <div className={cn("transition-all", skipCaptions && "opacity-30 pointer-events-none")}>
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-yellow-500/20 to-orange-500/20 flex items-center justify-center">
                                <ALargeSmall size={16} className="text-yellow-400" />
                            </div>
                            <label className="text-sm font-bold text-white uppercase tracking-widest">Subtitle Style</label>
                        </div>

                        <div className="grid grid-cols-2 gap-3 mt-4">
                            {PRESETS.map(p => {
                                const locked = isPresetLocked(p.id);
                                const isSelected = subtitlePreset === p.id;
                                return (
                                    <button
                                        key={p.id}
                                        onClick={() => {
                                            if (locked) setShowUpgradeModal(true);
                                            else setSubtitlePreset(p.id);
                                        }}
                                        className={cn(
                                            "p-4 rounded-2xl border text-left transition-all duration-300 relative overflow-hidden group",
                                            isSelected
                                                ? "bg-gradient-to-br from-yellow-500/10 to-orange-500/10 border-yellow-500 shadow-[0_0_20px_rgba(234,179,8,0.15)] ring-1 ring-yellow-500"
                                                : locked
                                                    ? "bg-slate-950/50 border-white/5 opacity-50 cursor-not-allowed"
                                                    : "bg-slate-900/50 border-white/5 hover:border-white/10 hover:bg-slate-900/80"
                                        )}
                                    >
                                        {/* Sample Preview */}
                                        <div className={cn(
                                            "text-[10px] font-black px-2 py-1 rounded mb-3 inline-block uppercase",
                                            p.id === 'bold_viral' ? "bg-yellow-500 text-black" :
                                                p.id === 'podcast_clean' ? "bg-white/10 text-white border border-white/20" :
                                                    p.id === 'hook_focus' ? "bg-gradient-to-r from-pink-500 to-purple-500 text-white" :
                                                        "bg-zinc-800 text-zinc-400 italic"
                                        )}>
                                            SAMPLE
                                        </div>

                                        <div className="flex items-center justify-between">
                                            <div>
                                                <div className={cn("font-bold flex items-center gap-2", isSelected ? "text-white" : "text-zinc-300")}>
                                                    {p.label}
                                                    {locked && <Lock size={12} className="text-zinc-500" />}
                                                </div>
                                                <div className={cn("text-xs", isSelected ? "text-zinc-400" : "text-zinc-500")}>{p.desc}</div>
                                            </div>
                                            {isSelected && (
                                                <div className="w-6 h-6 rounded-full bg-yellow-500 flex items-center justify-center">
                                                    <CheckCircle2 size={14} className="text-black" />
                                                </div>
                                            )}
                                        </div>
                                    </button>
                                )
                            })}
                        </div>
                        </div>
                    </div>

                    {/* HOOK BOOST TOGGLE - Premium */}
                    <div
                        onClick={() => {
                            if (isHookBoostLocked()) setShowUpgradeModal(true);
                            else setHookBoost(!hookBoost);
                        }}
                        className={cn(
                            "p-5 rounded-2xl border transition-all cursor-pointer relative overflow-hidden",
                            hookBoost
                                ? "bg-gradient-to-br from-pink-500/20 to-purple-500/10 border-pink-500/50 shadow-[0_0_30px_rgba(236,72,153,0.2)]"
                                : "bg-zinc-900/50 border-zinc-800 hover:border-zinc-600"
                        )}
                    >
                        {/* Animated glow background when active */}
                        {hookBoost && (
                            <div className="absolute inset-0 bg-gradient-to-r from-pink-500/10 via-purple-500/10 to-pink-500/10 animate-pulse"></div>
                        )}

                        <div className="flex items-center justify-between relative z-10">
                            <div className="flex items-center gap-4">
                                <div className={cn(
                                    "w-12 h-12 rounded-xl flex items-center justify-center transition-all",
                                    hookBoost ? "bg-gradient-to-br from-pink-500 to-purple-600 text-white shadow-lg shadow-pink-500/30" : "bg-zinc-800 text-zinc-400"
                                )}>
                                    <Zap size={22} fill={hookBoost ? "white" : "none"} />
                                </div>
                                <div>
                                    <h3 className={cn("font-bold text-lg flex items-center gap-2", hookBoost ? "text-white" : "text-zinc-400")}>
                                        Hook Boost™
                                        {hookBoost && <span className="text-xs px-2 py-0.5 bg-pink-500/20 text-pink-400 rounded-full">Active</span>}
                                    </h3>
                                    <p className="text-sm text-zinc-400">125% bigger text + 1.05x zoom for first 3 seconds</p>
                                </div>
                            </div>

                            {isHookBoostLocked() ? (
                                <div className="flex items-center gap-2 text-zinc-400">
                                    <Lock size={16} />
                                    <span className="text-xs">Pro</span>
                                </div>
                            ) : (
                                <div className={cn(
                                    "w-14 h-7 rounded-full p-1 transition-all relative",
                                    hookBoost ? "bg-gradient-to-r from-pink-500 to-purple-600" : "bg-zinc-800"
                                )}>
                                    <div className={cn(
                                        "w-5 h-5 rounded-full bg-white shadow-md transition-transform",
                                        hookBoost ? "translate-x-7" : "translate-x-0"
                                    )} />
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="pt-6 space-y-3">
                        <button
                            onClick={() => setStep(6)}
                            className="w-full py-5 bg-gradient-to-r from-pink-500 via-purple-500 to-pink-500 bg-[length:200%_100%] animate-gradient rounded-2xl text-white font-bold text-xl hover:scale-[1.02] transition-transform shadow-xl shadow-pink-500/25 flex items-center justify-center gap-2"
                        >
                            Finish & Review
                            <ArrowRight size={20} />
                        </button>
                        <button
                            onClick={() => setStep(4)}
                            className="w-full py-4 text-zinc-400 font-bold hover:text-white transition-colors"
                        >
                            ← Back to Segments
                        </button>
                    </div>
                </div>
            </div>
        );
    };

    const renderStep6 = () => (
        <div className="max-w-2xl mx-auto py-10 text-center space-y-8">
            <div className="space-y-4">
                <div className="w-24 h-24 bg-green-500/10 text-green-500 rounded-full flex items-center justify-center mx-auto mb-6">
                    <CheckCircle2 size={48} />
                </div>
                <h2 className="text-5xl font-black text-white tracking-tighter">Ready to Render?</h2>
                <p className="text-xl text-zinc-400">One credit will be deducted to generate this video.</p>
            </div>

            <div className="bg-slate-900/50 backdrop-blur-md border border-white/5 rounded-3xl p-8 text-left space-y-4 shadow-2xl relative overflow-hidden">
                {/* Decorative glowing blob */}
                <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3"></div>

                <div className="flex items-center justify-between pb-4 border-b border-white/5">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <ListChecks size={20} className="text-indigo-400" /> Order Summary
                    </h3>
                </div>

                <div className="space-y-4 py-2 relative z-10">
                    <div className="flex justify-between items-center">
                        <span className="text-sm text-slate-400">Content Type</span>
                        <span className="text-sm text-white font-bold bg-white/5 px-3 py-1 rounded-full">{contentType}</span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-sm text-slate-400">Platform</span>
                        <span className="text-sm text-white font-bold bg-white/5 px-3 py-1 rounded-full uppercase">{platform}</span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-sm text-slate-400">Duration</span>
                        <span className="text-sm text-white font-bold font-mono bg-white/5 px-3 py-1 rounded-full">{selectedClip?.start_time} - {selectedClip?.end_time}</span>
                    </div>
                </div>

                <div className="border-t border-dashed border-white/10 my-6" />

                {/* Resolution Selector */}
                <div className="space-y-4 relative z-10">
                    <span className="text-sm font-bold text-slate-300 block uppercase tracking-wider">Export Resolution</span>
                    <div className="grid grid-cols-3 gap-3">
                        {['720p', '1080p', '4k'].map((res) => {
                            const isLocked = !canSelectRes(res);
                            return (
                                <button
                                    key={res}
                                    onClick={() => !isLocked && setResolution(res)}
                                    disabled={isLocked}
                                    className={cn(
                                        "relative py-3 rounded-xl font-bold border transition-all duration-300 text-sm overflow-hidden",
                                        resolution === res
                                            ? "bg-indigo-500 text-white border-indigo-500 shadow-[0_0_15px_rgba(99,102,241,0.3)]"
                                            : isLocked
                                                ? "bg-slate-950/50 text-slate-700 border-white/5 cursor-not-allowed"
                                                : "bg-slate-900/50 text-slate-400 border-white/5 hover:border-white/10 hover:text-white"
                                    )}
                                    title={isLocked ? "🔒 Upgrade to unlock" : ""}
                                >
                                    {res.toUpperCase()}
                                    {isLocked && <Lock size={12} className="absolute top-2 right-2 text-slate-700" />}
                                </button>
                            );
                        })}
                    </div>
                </div>

                <div className="border-t border-white/10 my-6 pt-4 flex justify-between items-center relative z-10 bg-black/20 p-4 rounded-2xl">
                    <span className="text-sm font-bold text-slate-300">Total Cost</span>
                    <div className="flex items-center gap-2">
                        <div className="w-5 h-5 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                            <Zap size={12} className="text-white fill-white" />
                        </div>
                        <span className="text-xl text-white font-black">{mode === 'podcast_stack' ? '2' : '2'} Credits</span>
                    </div>
                </div>
            </div>

            {isProcessing ? (
                <div className="p-8 bg-zinc-950 border border-zinc-800 rounded-3xl space-y-4">
                    <Loader2 size={48} className="text-pink-500 animate-spin mx-auto" />
                    <h3 className="text-2xl font-bold text-white">Generating...</h3>
                    <div className="space-y-1">
                        {logs.slice(-2).map((l, i) => <p key={i} className="text-zinc-400 text-sm font-mono">{l}</p>)}
                    </div>
                </div>
            ) : resultUrl ? (
                <div className="space-y-8 animate-in zoom-in duration-500">
                    {/* SUCCESS BANNER */}
                    <div className="flex items-center justify-center gap-3">
                        <div className="w-10 h-10 bg-green-500/10 text-green-400 rounded-full flex items-center justify-center">
                            <CheckCircle2 size={20} />
                        </div>
                        <h3 className="text-2xl font-black text-white">Your Clip is Ready!</h3>
                    </div>

                    {/* VIDEO PLAYER */}
                    <div className="aspect-[9/16] max-h-[60vh] mx-auto bg-black rounded-3xl overflow-hidden shadow-2xl border border-zinc-800 relative group">
                        <video
                            key={resultUrl}
                            controls
                            className="w-full h-full object-contain"
                            src={resultUrl}
                            autoPlay
                            loop
                            muted
                            playsInline
                        />
                    </div>

                    {/* ACTION BUTTONS */}
                    <div className="flex flex-col items-center gap-3 max-w-md mx-auto">
                        {/* Download Button — real download, no new tab */}
                        <button
                            onClick={async () => {
                                try {
                                    const res = await fetch(resultUrl!);
                                    const blob = await res.blob();
                                    const url = URL.createObjectURL(blob);
                                    const a = document.createElement('a');
                                    a.href = url;
                                    a.download = `cloneframe_clip_${Date.now()}.mp4`;
                                    document.body.appendChild(a);
                                    a.click();
                                    document.body.removeChild(a);
                                    URL.revokeObjectURL(url);
                                    toast.success('Download started!');
                                } catch {
                                    toast.error('Download failed. Please try again.');
                                }
                            }}
                            className="w-full py-4 bg-white text-black font-bold rounded-2xl flex items-center justify-center gap-2 hover:scale-[1.02] transition-transform shadow-lg"
                        >
                            <Download size={20} /> Download Video
                        </button>

                        {/* Save to Library */}
                        <button
                            onClick={async () => {
                                if (!user || !resultUrl) return;
                                try {
                                    const token = await user.getIdToken();
                                    const res = await fetch(`${API_BASE_URL}/save-project`, {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                                        body: JSON.stringify({
                                            user_id: user.uid,
                                            topic: selectedClip?.title || contentType + ' Clip',
                                            video_url: resultUrl,
                                            platform: platform,
                                            mood: style
                                        })
                                    });
                                    if (res.ok) {
                                        toast.success('Saved to your library!');
                                    } else {
                                        throw new Error('Save failed');
                                    }
                                } catch {
                                    toast.error('Could not save. Try again.');
                                }
                            }}
                            className="w-full py-4 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-bold rounded-2xl flex items-center justify-center gap-2 hover:scale-[1.02] transition-transform shadow-lg shadow-purple-500/20"
                        >
                            <HardDrive size={18} /> Save to Library
                        </button>

                        {/* Generate Another Clip from Same Video */}
                        {viralClips.length > 1 && (
                            <button
                                onClick={() => { setStep(4); setResultUrl(null); setSelectedClip(null); }}
                                className="w-full py-4 bg-indigo-600 border border-indigo-500 text-white font-bold rounded-2xl hover:bg-indigo-500 transition-colors flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(79,70,229,0.3)]"
                            >
                                <Scissors size={18} /> Generate Another Clip
                            </button>
                        )}

                        {/* New Project */}
                        <button
                            onClick={() => { setStep(1); setFile(null); setViralClips([]); setResultUrl(null); setSelectedClip(null); setGcsPath(null); }}
                            className="w-full py-4 bg-zinc-900 border border-zinc-800 text-zinc-300 font-bold rounded-2xl hover:bg-zinc-800 hover:text-white transition-colors flex items-center justify-center gap-2"
                        >
                            <Video size={18} /> Start New Video
                        </button>
                    </div>
                </div>
            ) : (
                <div className="space-y-4">
                    <button
                        onClick={() => {
                            if (userPlan === 'free') {
                                setShowUpgradeModal(true);
                            } else {
                                handleGenerateClick();
                            }
                        }}
                        disabled={isProcessing || analyzing}
                        className={cn(
                            "px-12 py-5 font-black text-2xl rounded-full transition-all shadow-[0_0_50px_rgba(255,255,255,0.2)] flex items-center gap-3",
                            isProcessing || analyzing
                                ? "bg-zinc-700 text-zinc-400 cursor-not-allowed opacity-60"
                                : userPlan === 'free'
                                    ? "bg-zinc-800 text-zinc-400 hover:bg-zinc-700 cursor-pointer"
                                    : "bg-white text-black hover:scale-105"
                        )}
                    >
                        {userPlan === 'free' ? (
                            <>
                                <Lock size={24} className="text-purple-500" /> UPGRADE TO GENERATE
                            </>
                        ) : (
                            "GENERATE VIDEO"
                        )}
                    </button>
                    <br />
                    <button onClick={() => setStep(5)} className="text-zinc-400 hover:text-white">Make Adjustments</button>
                </div>
            )}
        </div>
    );

    return (
        <div className="flex flex-col min-h-[calc(100vh-100px)] max-w-[1600px] mx-auto">
            {/* WIZARD HEADER */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8 pt-2">
                <div>
                    <h1 className="text-xl font-bold text-white tracking-tight">Viral Repurposer</h1>
                    <p className="text-xs font-mono text-zinc-600 mt-0.5">Transform long videos into high-retention viral clips</p>
                </div>

                {/* Connected-node horizontal stepper */}
                <div className="flex items-center gap-0 overflow-x-auto pb-1 scrollbar-none">
                    {STEPS.map((s, idx) => {
                        const isCompleted = step > s.num;
                        const isCurrent = step === s.num;
                        const canJump = step > s.num;
                        return (
                            <div key={s.num} className="flex items-center">
                                <button
                                    onClick={() => canJump && setStep(s.num)}
                                    className={cn(
                                        'flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-150',
                                        canJump ? 'cursor-pointer' : 'cursor-default',
                                        isCurrent
                                            ? 'text-white'
                                            : isCompleted
                                            ? 'text-zinc-400 hover:text-zinc-200'
                                            : 'text-zinc-700'
                                    )}
                                >
                                    {/* Node dot */}
                                    <div className={cn(
                                        'w-5 h-5 rounded-full flex items-center justify-center transition-all duration-200 shrink-0',
                                        isCurrent
                                            ? 'bg-indigo-600 border-2 border-indigo-400 animate-pulse-ring text-white'
                                            : isCompleted
                                            ? 'bg-emerald-600 border border-emerald-500 text-white'
                                            : 'bg-transparent border border-zinc-800 text-zinc-700'
                                    )}>
                                        {isCompleted
                                            ? <Check size={9} strokeWidth={3} />
                                            : <span className="text-[9px] font-bold">{s.num}</span>
                                        }
                                    </div>
                                    <span className="hidden sm:block whitespace-nowrap">{s.label}</span>
                                </button>
                                {/* Connector line */}
                                {idx < STEPS.length - 1 && (
                                    <div className={cn(
                                        'w-6 h-[1px] mx-0.5 transition-colors duration-300 shrink-0',
                                        step > s.num + 1 ? 'bg-emerald-700' : step > s.num ? 'bg-indigo-600' : 'bg-zinc-800'
                                    )} />
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* MAIN CONTENT AREA */}
            <AnimatePresence mode="wait">
                <motion.div
                    key={step}
                    initial={{ opacity: 0, y: 10, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -10, scale: 0.98 }}
                    transition={{ duration: 0.3 }}
                    className="flex-1"
                >
                    {step === 1 && renderStep1()}
                    {step === 2 && renderStep2()}
                    {step === 3 && renderStep3()}
                    {step === 4 && renderStep4()}
                    {step === 5 && renderStep5()}
                    {step === 6 && renderStep6()}
                </motion.div>
            </AnimatePresence>

            <CreditConfirmationModal
                isOpen={showCreditModal}
                onClose={() => setShowCreditModal(false)}
                onConfirm={executeGeneration}
                estimatedCost={estimatedCost}
                currentBalance={credits} // from usePlan
                taskName="Repurpose Video"
            />
        </div>
    );
}

