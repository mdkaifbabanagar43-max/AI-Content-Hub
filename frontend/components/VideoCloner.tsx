'use client';

import React, { useState, useEffect, useRef } from 'react';
import { 
    Sparkles, Link as LinkIcon, Video, CheckCircle2, Loader2, ArrowRight, 
    Zap, UploadCloud, File as FileIcon, Eye, ShieldCheck, Film, Layers,
    Volume2, MessageSquare, Play, Download, RefreshCw, ChevronRight, Wand2,
    ShieldAlert
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-hot-toast';
import { cn } from '@/lib/utils';
import { API_BASE_URL } from '@/lib/config';
import { motion, AnimatePresence } from 'framer-motion';

const NICHES = [
    { id: 'Finance', label: 'Finance & Wealth', color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    { id: 'Fitness', label: 'Fitness & Health', color: 'text-orange-400', bg: 'bg-orange-500/10' },
    { id: 'Tech', label: 'Tech & AI', color: 'text-blue-400', bg: 'bg-blue-500/10' },
    { id: 'Comedy', label: 'Comedy & Entertainment', color: 'text-pink-400', bg: 'bg-pink-500/10' },
    { id: 'RealEstate', label: 'Real Estate', color: 'text-indigo-400', bg: 'bg-indigo-500/10' }
];

/**
 * P3 Phase D: parses backend 422 detail into per-gate findings.
 * Backend format: "...validation pipeline: <str(e)>. Gate findings: ['a', 'b']"
 * (Python list repr -> single quotes, so JSON.parse is not usable).
 */
function extractGateFindings(detail: string): string[] {
    const match = detail.match(/Gate findings:\s*\[([\s\S]*?)\]\s*$/);
    if (match) {
        return match[1]
            .split("', '")
            .map((s) => s.replace(/^['"]|['"]$/g, "").trim())
            .filter(Boolean);
    }
    const idx = detail.indexOf("validation pipeline");
    if (idx !== -1) return [detail.slice(idx).replace(/^.*?pipeline:\s*/, "").trim()];
    return [detail];
}


export default function VideoCloner({ onNavigate }: { onNavigate?: (tab: string) => void }) {
    const { user } = useAuth();
    
    // Project & Step state
    const [step, setStep] = useState(1);
    const [projectId, setProjectId] = useState<string>(() => `proj_${Date.now().toString(36)}`);
    const [videoUrl, setVideoUrl] = useState('');
    const [videoFile, setVideoFile] = useState<File | null>(null);
    const [selectedNiche, setSelectedNiche] = useState('Finance');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    
    // Data states
    const [sourceVideoId, setSourceVideoId] = useState<string>('');
    const [analysisData, setAnalysisData] = useState<any>(null);
    const [cloneBlueprint, setCloneBlueprint] = useState<any>(null);
    const [visualIdentityPack, setVisualIdentityPack] = useState<any>(null);
    
    // Transform & Preservation states
    const [customPrompt, setCustomPrompt] = useState<string>('');
    const [targetLanguage, setTargetLanguage] = useState<string>('Hinglish / Hindi');
    const [targetDuration, setTargetDuration] = useState<number>(30); // Preset ~30s
    const [productionBlueprint, setProductionBlueprint] = useState<any>(null);
    const [isTransforming, setIsTransforming] = useState(false);
    const [gateFindings, setGateFindings] = useState<string[]>([]);
    
    // User Preservation Options (Authoritative)
    const [preserveVisualStyle, setPreserveVisualStyle] = useState<boolean>(true);
    const [preserveCharacters, setPreserveCharacters] = useState<boolean>(false);
    const [preserveEnvironment, setPreserveEnvironment] = useState<boolean>(false);
    const [preserveCameraPacing, setPreserveCameraPacing] = useState<boolean>(true);
    const [cloneMode, setCloneMode] = useState<string>('style_only');

    const applyPreset = (preset: 'style_only' | 'characters_only' | 'characters_and_style' | 'full_visual_clone' | 'trend_inspired') => {
        setCloneMode(preset);
        if (preset === 'style_only') {
            setPreserveVisualStyle(true);
            setPreserveCharacters(false);
            setPreserveEnvironment(false);
            setPreserveCameraPacing(true);
        } else if (preset === 'characters_only') {
            // Contract "Character Clone" (Q2): keep characters + art style;
            // regenerate environment AND camera/pacing.
            setPreserveVisualStyle(true);
            setPreserveCharacters(true);
            setPreserveEnvironment(false);
            setPreserveCameraPacing(false);
        } else if (preset === 'characters_and_style') {
            setPreserveVisualStyle(true);
            setPreserveCharacters(true);
            setPreserveEnvironment(false);
            setPreserveCameraPacing(true);
        } else if (preset === 'full_visual_clone') {
            setPreserveVisualStyle(true);
            setPreserveCharacters(true);
            setPreserveEnvironment(true);
            setPreserveCameraPacing(true);
        } else if (preset === 'trend_inspired') {
            setPreserveVisualStyle(false);
            setPreserveCharacters(false);
            setPreserveEnvironment(false);
            setPreserveCameraPacing(true);
        }
    };
    
    // Lip-sync mode: false = Mode A (Voiceover), true = Mode B (Talking Character)
    const [useLipSync, setUseLipSync] = useState<boolean>(false);
    
    // Generation state
    const [isGenerating, setIsGenerating] = useState(false);
    const [generationProgress, setGenerationProgress] = useState<string>('');
    const [finalVideoUrl, setFinalVideoUrl] = useState<string | null>(null);
    const [telemetryLogs, setTelemetryLogs] = useState<Array<{ time: string; msg: string; type: string }>>([]);
    const [currentSceneNum, setCurrentSceneNum] = useState<number>(1);
    const [totalScenesNum, setTotalScenesNum] = useState<number>(1);
    const [qualityScore, setQualityScore] = useState<number | null>(null);
    const [currentStage, setCurrentStage] = useState<string>('Initializing');
    const [sseConnected, setSseConnected] = useState<boolean>(false);

    // Status-polling & SSE lifecycle guards
    const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const eventSourceRef = useRef<EventSource | null>(null);

    const stopStatusPolling = () => {
        if (pollIntervalRef.current !== null) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
        }
    };

    const closeEventSource = () => {
        if (eventSourceRef.current !== null) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
    };

    // Clear active poll timer & SSE stream when the wizard unmounts
    useEffect(() => {
        return () => {
            stopStatusPolling();
            closeEventSource();
        };
    }, []);

    const getAuthHeaders = async () => {
        if (!user) throw new Error("Not logged in");
        const token = await user.getIdToken();
        return { 'Authorization': `Bearer ${token}` };
    };

    // Step 1: Handle Source Ingest & Analysis
    const handleAnalyze = async () => {
        if (!videoUrl && !videoFile) {
            toast.error("Please upload a video file or paste a video URL.");
            return;
        }
        if (!user) {
            toast.error("Please log in first.");
            return;
        }

        setIsAnalyzing(true);
        try {
            const headers = await getAuthHeaders();
            let record: any = null;

            // Ingest source video
            if (videoFile) {
                const formData = new FormData();
                formData.append('file', videoFile);
                const upRes = await fetch(`${API_BASE_URL}/projects/${projectId}/source-videos`, {
                    method: 'POST',
                    headers,
                    body: formData
                });
                if (!upRes.ok) {
                    const err = await upRes.json().catch(() => ({}));
                    throw new Error(err.detail || "Failed to upload source video.");
                }
                record = await upRes.json();
            } else if (videoUrl) {
                const upRes = await fetch(`${API_BASE_URL}/projects/${projectId}/source-videos/from-url`, {
                    method: 'POST',
                    headers: { ...headers, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: videoUrl })
                });
                if (!upRes.ok) {
                    const err = await upRes.json().catch(() => ({}));
                    throw new Error(err.detail || "Failed to import video from URL.");
                }
                record = await upRes.json();
            }

            if (!record || !record.source_video_id) {
                throw new Error(record?.detail || "Failed to ingest source video.");
            }

            setSourceVideoId(record.source_video_id);

            // Run Analysis
            const anRes = await fetch(`${API_BASE_URL}/projects/${projectId}/source-videos/${record.source_video_id}/analyze`, {
                method: 'POST',
                headers: { ...headers, 'Content-Type': 'application/json' }
            });
            if (!anRes.ok) {
                const err = await anRes.json().catch(() => ({}));
                throw new Error(err.detail || "Source video analysis failed.");
            }
            const anData = await anRes.json();
            setAnalysisData(anData);

            // Build Clone Blueprint
            const cbRes = await fetch(`${API_BASE_URL}/projects/${projectId}/source-videos/${record.source_video_id}/clone-blueprint`, {
                method: 'POST',
                headers: { ...headers, 'Content-Type': 'application/json' }
            });
            let cbData: any = null;
            if (cbRes.ok) {
                cbData = await cbRes.json();
            } else {
                // Fallback to /clone-blueprints
                const fallbackRes = await fetch(`${API_BASE_URL}/projects/${projectId}/clone-blueprints`, {
                    method: 'POST',
                    headers: { ...headers, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ analysis_id: anData.analysis_id })
                });
                if (!fallbackRes.ok) {
                    const err = await fallbackRes.json().catch(() => ({}));
                    throw new Error(err.detail || "Failed to build clone blueprint.");
                }
                cbData = await fallbackRes.json();
            }
            setCloneBlueprint(cbData);

            // Fetch or create Visual Identity Pack — pass analysis-derived data
            const analysisChars = (anData.character_identities || []).map((c: any) => ({
                character_id: c.character_id || `char_${Math.random().toString(36).slice(2, 8)}`,
                name: c.name || c.role || 'Character',
                description: c.description || ''
            }));
            const vipRes = await fetch(`${API_BASE_URL}/projects/${projectId}/visual-identity-pack`, {
                method: 'POST',
                headers: { ...headers, 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    art_style: anData.visual_style?.art_style || "Cinematic digital animation",
                    character_design: anData.visual_style?.character_design || anData.character_identities?.[0]?.description || "Characters as they appear in the source video",
                    characters: analysisChars.length > 0 ? analysisChars : undefined
                })
            });
            if (vipRes.ok) {
                const vipData = await vipRes.json();
                setVisualIdentityPack(vipData);
            }

            toast.success("Source video DNA extracted!");
            setStep(2);
        } catch (err: any) {
            console.error(err);
            toast.error(err.message || "Analysis failed.");
        } finally {
            setIsAnalyzing(false);
        }
    };

    // Step 4: Transform to Production Blueprint
    const handleTransform = async () => {
        if (!cloneBlueprint) return;
        setIsTransforming(true);
        setGateFindings([]); // P3 Phase D: clear prior gate findings on retry
        try {
            const headers = await getAuthHeaders();
            const storyTopic = customPrompt || `Viral ${selectedNiche} concept`;
            const res = await fetch(`${API_BASE_URL}/projects/${projectId}/clone-blueprints/${cloneBlueprint.clone_blueprint_id}/transform`, {
                method: 'POST',
                headers: { ...headers, 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    topic: storyTopic,
                    target_topic: storyTopic,
                    story_change: customPrompt ? `Create a new original story about: ${customPrompt}` : undefined,
                    niche: selectedNiche,
                    target_niche: selectedNiche,
                    language: targetLanguage,
                    target_language: targetLanguage,
                    target_duration_seconds: targetDuration,
                    tone: "High Energy & Humorous",
                    preserve_visual_style: preserveVisualStyle,
                    preserve_characters: preserveCharacters,
                    preserve_environment: preserveEnvironment,
                    preserve_camera_pacing: preserveCameraPacing,
                    preserve_trend_structure: cloneMode === 'trend_inspired',
                    clone_mode: cloneMode,
                    // ── P3 PHASE D DUAL-SEND ──────────────────────────
                    // Canonical profile rides ALONGSIDE legacy booleans for
                    // one release; backend profile-wins rule makes this the
                    // authoritative source (legacy fields = compat shim).
                    preservation_profile: {
                        preserve_visual_style: preserveVisualStyle,
                        preserve_characters: preserveCharacters,
                        preserve_environment: preserveEnvironment,
                        preserve_camera_language: preserveCameraPacing,
                        preserve_pacing_editing: preserveCameraPacing,
                        preserve_audio_style: false,
                        preserve_voice_style: false,
                        preserve_trend_structure: cloneMode === 'trend_inspired',
                    },
                    character_mode: preserveCharacters ? 'PRESERVE_SOURCE' : 'CREATE_NEW',
                    environment_mode: preserveEnvironment ? 'PRESERVE_SOURCE' : 'CREATE_NEW',
                    story_mode: cloneMode === 'trend_inspired' ? 'TREND_INSPIRED' : 'STRUCTURE_INSPIRED',
                })
            });
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                const detail: string = errData.detail || "";
                if (res.status === 422) {
                    // G2/G3/G4 gate rejection -> surface findings in Step 3
                    const findings = extractGateFindings(detail);
                    setGateFindings(findings);
                    throw new Error(
                        findings[0]
                            ? `Validation failed: ${findings[0]}`
                            : detail || "Validation failed."
                    );
                }
                throw new Error(detail || `Server returned ${res.status}: Transformation failed.`);
            }
            const pbData = await res.json();
            if (pbData && pbData.blueprint_id) {
                // Ensure lip sync mode is applied
                pbData.use_lip_sync = useLipSync;
                setProductionBlueprint(pbData);
                toast.success("Production Storyboard Generated!");
                setStep(4);
            } else {
                throw new Error("Failed to create production blueprint.");
            }
        } catch (err: any) {
            console.error(err);
            toast.error(err.message || "Transformation failed.");
        } finally {
            setIsTransforming(false);
        }
    };

    // Step 5: Approve and Generate Final Video
    const handleGenerate = async () => {
        if (!productionBlueprint) return;
        setIsGenerating(true);
        setGenerationProgress("Approving production blueprint...");
        try {
            const headers = await getAuthHeaders();

            // Set lip-sync selection on blueprint
            productionBlueprint.use_lip_sync = useLipSync;
            productionBlueprint.allow_lip_sync_fallback = true;

            // Approve blueprint
            await fetch(`${API_BASE_URL}/projects/${projectId}/production-blueprints/${productionBlueprint.blueprint_id}/approve`, {
                method: 'POST',
                headers
            });

            // Launch generation
            setGenerationProgress("Dispatching Veo & ElevenLabs generation loop...");
            const genRes = await fetch(`${API_BASE_URL}/projects/${projectId}/production-blueprints/${productionBlueprint.blueprint_id}/generate`, {
                method: 'POST',
                headers
            });
            const genData = await genRes.json();

            // Step 5: Start Live Telemetry Stream via SSE + Fallback Polling
            setStep(5);
            setTelemetryLogs([]);
            setCurrentSceneNum(1);
            setTotalScenesNum(productionBlueprint.scenes?.length || 1);
            setQualityScore(null);
            setCurrentStage("Initializing Orchestrator");
            setSseConnected(false);

            const token = user ? await user.getIdToken() : '';
            const sseUrl = `${API_BASE_URL}/projects/${projectId}/production-blueprints/${productionBlueprint.blueprint_id}/events?token=${encodeURIComponent(token)}`;

            // Helper to append telemetry log
            const addLog = (msg: string, type: string = "info") => {
                const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                setTelemetryLogs(prev => [...prev.slice(-40), { time, msg, type }]);
            };

            // Connect SSE EventSource
            try {
                closeEventSource();
                const es = new EventSource(sseUrl);
                eventSourceRef.current = es;

                es.onmessage = (e) => {
                    if (!e.data) return;
                    try {
                        const data = JSON.parse(e.data);
                        setSseConnected(true);

                        if (data.event === "STREAM_CONNECTED") {
                            addLog("Connected to backend telemetry stream", "system");
                        } else if (data.event === "SCENE_START") {
                            setCurrentSceneNum(data.scene_number || 1);
                            setCurrentStage(`Scene ${data.scene_id}: Synthesizing Voiceover`);
                            setGenerationProgress(`Rendering Scene ${data.scene_id}...`);
                            addLog(`Scene ${data.scene_id} started (${data.expected_duration || 5}s)`, "scene");
                        } else if (data.event === "AUDIO_SYNTH_COMPLETE") {
                            setCurrentStage("Generating Veo Clip");
                            addLog(`ElevenLabs audio ready (${Number(data.audio_duration || 0).toFixed(1)}s)`, "audio");
                        } else if (data.event === "VEO_CHUNK_SUBMITTED") {
                            setCurrentStage(`Veo 2.0 Video Gen (Attempt ${data.attempt_number || 1})`);
                            addLog(`Veo prompt submitted to Vertex AI (Attempt ${data.attempt_number || 1})`, "veo");
                        } else if (data.event === "QUALITY_REVIEW_SCORED") {
                            if (typeof data.score === 'number') {
                                setQualityScore(data.score);
                            }
                            const passed = data.passed;
                            addLog(`QualityReviewer: Score ${Number(data.score || 0).toFixed(1)}/10 (${passed ? 'ACCEPTED' : 'REJECTED'})`, passed ? 'success' : 'warning');
                        } else if (data.event === "RETRY_ATTEMPTED") {
                            setCurrentStage(`Quality Retry (${data.retry_number}/${data.max_retries})`);
                            addLog(`Adaptive retry ${data.retry_number} triggered: ${data.reason || 'Quality below threshold'}`, "warning");
                        } else if (data.event === "SCENE_NORMALIZED") {
                            setCurrentStage("Scene Normalized");
                            addLog(`Scene normalized to timeline (${Number(data.actual_duration || 0).toFixed(1)}s)`, "scene");
                        } else if (data.event === "ASSEMBLY_START") {
                            setCurrentStage("Assembling Final Video");
                            setGenerationProgress("Assembling timeline & normalising scene clips...");
                            addLog("All scenes complete. Normalizing & concatenating timeline...", "assembly");
                        } else if (data.event === "ASSEMBLY_COMPLETE") {
                            closeEventSource();
                            stopStatusPolling();
                            setIsGenerating(false);
                            setCurrentStage("Completed");
                            const finalUrl = data.output_uri || data.final_video_url;
                            setFinalVideoUrl(finalUrl);
                            addLog("Final video certified & generated successfully!", "success");
                            toast.success("Video generated successfully!");
                        } else if (data.event === "GENERATION_FAILED" || data.event === "JOB_FAILED") {
                            closeEventSource();
                            stopStatusPolling();
                            setIsGenerating(false);
                            setCurrentStage("Failed");
                            addLog(`Generation failed: ${data.error || 'Unknown error'}`, "error");
                            toast.error("Generation failed. Please check diagnostics.");
                        }
                    } catch (parseErr) {
                        console.debug("[VideoCloner SSE] Parse error:", parseErr);
                    }
                };

                es.onerror = () => {
                    console.debug("[VideoCloner SSE] Stream interrupted, continuing fallback polling.");
                    setSseConnected(false);
                };
            } catch (sseErr) {
                console.debug("[VideoCloner SSE] Connection error:", sseErr);
                setSseConnected(false);
            }

            // Fallback status polling (P2: bounded, leak-free polling)
            const POLL_INTERVAL_MS = 4000;
            const POLL_TIMEOUT_MS = 20 * 60 * 1000;
            const MAX_CONSECUTIVE_POLL_ERRORS = 5;
            const pollStartedAt = Date.now();
            let consecutivePollErrors = 0;

            pollIntervalRef.current = setInterval(async () => {
                if (pollIntervalRef.current === null) return;

                if (Date.now() - pollStartedAt > POLL_TIMEOUT_MS) {
                    stopStatusPolling();
                    closeEventSource();
                    setIsGenerating(false);
                    toast.error("Generation timed out after 20 minutes. Check diagnostics.");
                    return;
                }

                try {
                    const stRes = await fetch(`${API_BASE_URL}/projects/${projectId}/production-blueprints/${productionBlueprint.blueprint_id}/status`, {
                        headers
                    });
                    const stData = await stRes.json();
                    consecutivePollErrors = 0;

                    if (stData.status === "COMPLETED") {
                        stopStatusPolling();
                        closeEventSource();
                        setIsGenerating(false);
                        setFinalVideoUrl(stData.output_uri || stData.final_video_url);
                        toast.success("Video generated successfully!");
                    } else if (stData.status === "FAILED") {
                        stopStatusPolling();
                        closeEventSource();
                        setIsGenerating(false);
                        toast.error("Generation failed. Please check diagnostics.");
                    } else if (!sseConnected) {
                        setGenerationProgress(`Rendering scene clips (${stData.status})...`);
                    }
                } catch (e) {
                    console.error("[VideoCloner] Status poll failed:", e);
                    consecutivePollErrors += 1;
                    if (consecutivePollErrors >= MAX_CONSECUTIVE_POLL_ERRORS) {
                        stopStatusPolling();
                        closeEventSource();
                        setIsGenerating(false);
                        toast.error("Lost connection while checking render status. Please retry.");
                    }
                }
            }, POLL_INTERVAL_MS);

        } catch (err: any) {
            console.error(err);
            toast.error(err.message || "Generation dispatch failed.");
            setIsGenerating(false);
        }
    };

    return (
        <div className="max-w-6xl mx-auto p-4 md:p-8">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                    <div className="flex items-center gap-2.5 mb-1.5">
                        <span className="p-2 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 text-indigo-400">
                            <Zap size={20} />
                        </span>
                        <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white">Video Cloner</h1>
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                            PRO ARCHITECTURE
                        </span>
                    </div>
                    <p className="text-sm text-white/50">
                        Clone the visual DNA. Create something new.
                    </p>
                </div>

                {/* Stepper tabs */}
                <div className="flex items-center gap-1.5 p-1 bg-white/[0.03] border border-white/[0.08] rounded-xl self-start">
                    {[
                        { num: 1, label: 'Source' },
                        { num: 2, label: 'DNA & Style' },
                        { num: 3, label: 'Transform' },
                        { num: 4, label: 'Storyboard' },
                        { num: 5, label: 'Render' },
                    ].map((s) => (
                        <div
                            key={s.num}
                            className={cn(
                                "flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                                step === s.num
                                    ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30"
                                    : step > s.num
                                    ? "text-emerald-400"
                                    : "text-white/40"
                            )}
                        >
                            <span className={cn(
                                "w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold",
                                step === s.num
                                    ? "bg-indigo-500 text-white"
                                    : step > s.num
                                    ? "bg-emerald-500/20 text-emerald-400"
                                    : "bg-white/10 text-white/40"
                            )}>
                                {step > s.num ? "✓" : s.num}
                            </span>
                            <span className="hidden sm:inline">{s.label}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* STEP 1: SOURCE INGEST */}
            {step === 1 && (
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                    <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.08] space-y-6">
                        <div>
                            <h2 className="text-base font-semibold text-white flex items-center gap-2">
                                <Video size={18} className="text-indigo-400" /> Source Video Ingestion
                            </h2>
                            <p className="text-xs text-white/50 mt-1">
                                Upload a video or import from YouTube/Instagram/TikTok to extract its visual DNA, character models, and narrative rhythm.
                            </p>
                        </div>

                        <div className="space-y-4">
                            {/* URL or Upload */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-xs font-semibold text-white/80 flex items-center gap-1.5">
                                        <LinkIcon size={14} className="text-indigo-400" /> Public Video URL
                                    </label>
                                    <input
                                        type="url"
                                        placeholder="https://youtube.com/shorts/... or tiktok.com/..."
                                        value={videoUrl}
                                        onChange={(e) => { setVideoUrl(e.target.value); setVideoFile(null); }}
                                        className="w-full p-3 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <label className="text-xs font-semibold text-white/80 flex items-center gap-1.5">
                                        <UploadCloud size={14} className="text-indigo-400" /> Upload File Directly
                                    </label>
                                    <label className="w-full p-3 rounded-xl bg-white/[0.04] border border-white/[0.08] border-dashed hover:border-indigo-500/50 cursor-pointer flex items-center justify-between text-xs text-white/60 transition-colors">
                                        <span className="truncate">{videoFile ? videoFile.name : "Select .mp4 or .mov video file"}</span>
                                        <input
                                            type="file"
                                            accept="video/*"
                                            className="hidden"
                                            onChange={(e) => {
                                                if (e.target.files?.[0]) {
                                                    setVideoFile(e.target.files[0]);
                                                    setVideoUrl('');
                                                }
                                            }}
                                        />
                                        <FileIcon size={16} className="text-indigo-400 flex-shrink-0 ml-2" />
                                    </label>
                                </div>
                            </div>

                            {/* Niche Selection */}
                            <div className="space-y-2 pt-2">
                                <label className="text-xs font-semibold text-white/80 block">Target Content Niche</label>
                                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2.5">
                                    {NICHES.map((n) => (
                                        <button
                                            key={n.id}
                                            type="button"
                                            onClick={() => setSelectedNiche(n.id)}
                                            className={cn(
                                                "p-3 rounded-xl border text-left text-xs font-medium transition-all flex items-center justify-between",
                                                selectedNiche === n.id
                                                    ? `${n.bg} border-indigo-500/50 text-white shadow-sm`
                                                    : "bg-white/[0.02] border-white/[0.06] text-white/60 hover:text-white"
                                            )}
                                        >
                                            <span className={selectedNiche === n.id ? n.color : ""}>{n.label}</span>
                                            {selectedNiche === n.id && <CheckCircle2 size={14} className={n.color} />}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <button
                                onClick={handleAnalyze}
                                disabled={isAnalyzing || (!videoUrl && !videoFile)}
                                className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-sm font-semibold flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/25 transition-all disabled:opacity-50 mt-4"
                            >
                                {isAnalyzing ? (
                                    <>
                                        <Loader2 size={16} className="animate-spin" />
                                        <span>Extracting Video DNA...</span>
                                    </>
                                ) : (
                                    <>
                                        <span>Analyze Source Video</span>
                                        <ArrowRight size={16} />
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </motion.div>
            )}

            {/* STEP 2: VIDEO DNA & VISUAL IDENTITY PACK */}
            {step === 2 && (
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                    <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.08] space-y-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <h2 className="text-base font-semibold text-white flex items-center gap-2">
                                    <ShieldCheck size={18} className="text-emerald-400" /> Video DNA & Visual Identity Locked
                                </h2>
                                <p className="text-xs text-white/50 mt-1">
                                    Authoritative multi-angle character references and visual treatment extracted from source video.
                                </p>
                            </div>
                            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                IDENTITY VERSION 1 (LOCKED)
                            </span>
                        </div>

                        {/* DNA Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-1.5 flex flex-col justify-center items-center text-center">
                                <ShieldCheck size={20} className="text-emerald-400 mb-1" />
                                <span className="text-[11px] font-semibold text-white/60 uppercase tracking-wider">Visual Style Locked</span>
                                <p className="text-xs font-medium text-white line-clamp-2">
                                    {analysisData?.visual_style?.art_style || visualIdentityPack?.visual_treatment?.art_style || "3D Pixar Animation"}
                                </p>
                            </div>
                            <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-1.5 flex flex-col justify-center items-center text-center">
                                <ShieldCheck size={20} className="text-emerald-400 mb-1" />
                                <span className="text-[11px] font-semibold text-white/60 uppercase tracking-wider">Character Consistency Locked</span>
                                <p className="text-xs font-medium text-white line-clamp-2">
                                    {analysisData?.character_identities?.[0]?.description || "Anthropomorphic 3D Characters"}
                                </p>
                            </div>
                            <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-1.5 flex flex-col justify-center items-center text-center">
                                <ShieldCheck size={20} className="text-emerald-400 mb-1" />
                                <span className="text-[11px] font-semibold text-white/60 uppercase tracking-wider">Environment Consistency Locked</span>
                                <p className="text-xs font-medium text-white line-clamp-2">
                                    Maintained across all scenes
                                </p>
                            </div>
                        </div>

                        {/* Reference Sheet Visual Preview */}
                        {visualIdentityPack && (
                            <div className="p-5 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-3">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs font-semibold text-white/80 uppercase tracking-wider flex items-center gap-2">
                                        <Layers size={14} className="text-indigo-400" /> Persistent Multi-Angle Character Sheet
                                    </span>
                                    <span className="text-[11px] text-white/40">Zero-Drift Shot Conditioning</span>
                                </div>

                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                    {(() => {
                                        const charKey = visualIdentityPack?.characters ? Object.keys(visualIdentityPack.characters)[0] : null;
                                        const charData = charKey ? visualIdentityPack.characters[charKey] : null;
                                        const angleMap = [
                                            { label: 'Front View', uri: charData?.front_ref_uri },
                                            { label: '3/4 Angle', uri: charData?.three_quarter_left_uri },
                                            { label: 'Closeup Detail', uri: charData?.closeup_ref_uri },
                                            { label: 'Full Body', uri: charData?.full_body_ref_uri }
                                        ];
                                        return angleMap.map(({ label, uri }) => (
                                            <div key={label} className="rounded-lg bg-black/40 border border-white/[0.08] p-2.5 text-center space-y-2">
                                                <div className="h-24 rounded bg-indigo-500/5 border border-indigo-500/10 flex items-center justify-center text-indigo-400/60 overflow-hidden">
                                                    {uri ? (
                                                        <img src={uri} alt={label} className="h-full w-full object-cover rounded" />
                                                    ) : (
                                                        <Film size={20} />
                                                    )}
                                                </div>
                                                <span className="text-[11px] font-medium text-white/70 block">{label}</span>
                                            </div>
                                        ));
                                    })()}
                                </div>
                            </div>
                        )}

                        <div className="flex justify-end gap-3">
                            <button
                                onClick={() => setStep(3)}
                                className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 transition-colors"
                            >
                                <span>Proceed to Creative Transformation</span>
                                <ArrowRight size={14} />
                            </button>
                        </div>
                    </div>
                </motion.div>
            )}

            {/* STEP 3: CREATIVE TRANSFORMATION */}
            {step === 3 && (
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                    <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.08] space-y-6">
                        <div>
                            <h2 className="text-base font-semibold text-white flex items-center gap-2">
                                <Wand2 size={18} className="text-purple-400" /> Creative Transformation
                            </h2>
                            <p className="text-xs text-white/50 mt-1">
                                Clone the visual DNA. Create something new. The user decides what to preserve — CloneFrame creates the rest.
                            </p>
                        </div>

                        {/* PRESERVATION OPTIONS & PRESETS */}
                        <div className="p-5 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-4">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                                <div>
                                    <span className="text-xs font-bold text-white uppercase tracking-wider block">
                                        WHAT SHOULD CLONEFRAME PRESERVE?
                                    </span>
                                    <span className="text-[11px] text-white/40">
                                        Select individual options or choose a quick preset.
                                    </span>
                                </div>

                                {/* PRESETS BAR */}
                                <div className="flex flex-wrap gap-1.5">
                                    {[
                                        { id: 'style_only', label: 'Style Only' },
                                        { id: 'characters_only', label: 'Character Clone' },
                                        { id: 'characters_and_style', label: 'Characters + Style' },
                                        { id: 'full_visual_clone', label: 'Full Visual Clone' },
                                        { id: 'trend_inspired', label: 'Trend Inspired' }
                                    ].map((p) => (
                                        <button
                                            key={p.id}
                                            type="button"
                                            onClick={() => applyPreset(p.id as any)}
                                            className={cn(
                                                "px-3 py-1 rounded-lg text-xs font-medium transition-all border",
                                                cloneMode === p.id
                                                    ? "bg-indigo-600/30 border-indigo-500 text-indigo-300 shadow-sm"
                                                    : "bg-white/[0.03] border-white/[0.06] text-white/60 hover:text-white"
                                            )}
                                        >
                                            {p.label}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* 4 INTERACTIVE CHECKBOXES */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                                <label className={cn(
                                    "p-3.5 rounded-xl border cursor-pointer flex items-start gap-3 transition-all",
                                    preserveVisualStyle 
                                        ? "bg-indigo-500/10 border-indigo-500/40 text-white" 
                                        : "bg-white/[0.02] border-white/[0.06] text-white/50 hover:border-white/20"
                                )}>
                                    <input 
                                        type="checkbox" 
                                        checked={preserveVisualStyle} 
                                        onChange={(e) => {
                                            setPreserveVisualStyle(e.target.checked);
                                            setCloneMode('custom');
                                        }} 
                                        className="mt-0.5 rounded border-white/20 text-indigo-600 focus:ring-0"
                                    />
                                    <div>
                                        <span className="text-xs font-semibold block">Visual Style</span>
                                        <span className="text-[11px] opacity-70">Keep art style, lighting, render language, and color palette.</span>
                                    </div>
                                </label>

                                <label className={cn(
                                    "p-3.5 rounded-xl border cursor-pointer flex items-start gap-3 transition-all",
                                    preserveCharacters 
                                        ? "bg-indigo-500/10 border-indigo-500/40 text-white" 
                                        : "bg-white/[0.02] border-white/[0.06] text-white/50 hover:border-white/20"
                                )}>
                                    <input 
                                        type="checkbox" 
                                        checked={preserveCharacters} 
                                        onChange={(e) => {
                                            setPreserveCharacters(e.target.checked);
                                            setCloneMode('custom');
                                        }} 
                                        className="mt-0.5 rounded border-white/20 text-indigo-600 focus:ring-0"
                                    />
                                    <div>
                                        <span className="text-xs font-semibold block">Characters</span>
                                        <span className="text-[11px] opacity-70">Keep source character visual appearance & identities.</span>
                                    </div>
                                </label>

                                <label className={cn(
                                    "p-3.5 rounded-xl border cursor-pointer flex items-start gap-3 transition-all",
                                    preserveEnvironment 
                                        ? "bg-indigo-500/10 border-indigo-500/40 text-white" 
                                        : "bg-white/[0.02] border-white/[0.06] text-white/50 hover:border-white/20"
                                )}>
                                    <input 
                                        type="checkbox" 
                                        checked={preserveEnvironment} 
                                        onChange={(e) => {
                                            setPreserveEnvironment(e.target.checked);
                                            setCloneMode('custom');
                                        }} 
                                        className="mt-0.5 rounded border-white/20 text-indigo-600 focus:ring-0"
                                    />
                                    <div>
                                        <span className="text-xs font-semibold block">Environment</span>
                                        <span className="text-[11px] opacity-70">Keep source background world setting and architectural mood.</span>
                                    </div>
                                </label>

                                <label className={cn(
                                    "p-3.5 rounded-xl border cursor-pointer flex items-start gap-3 transition-all",
                                    preserveCameraPacing 
                                        ? "bg-indigo-500/10 border-indigo-500/40 text-white" 
                                        : "bg-white/[0.02] border-white/[0.06] text-white/50 hover:border-white/20"
                                )}>
                                    <input 
                                        type="checkbox" 
                                        checked={preserveCameraPacing} 
                                        onChange={(e) => {
                                            setPreserveCameraPacing(e.target.checked);
                                            setCloneMode('custom');
                                        }} 
                                        className="mt-0.5 rounded border-white/20 text-indigo-600 focus:ring-0"
                                    />
                                    <div>
                                        <span className="text-xs font-semibold block">Camera & Pacing</span>
                                        <span className="text-[11px] opacity-70">Keep shot durations, cut frequency, and dynamic camera angles.</span>
                                    </div>
                                </label>
                            </div>
                        </div>

                        {/* NEW STORY INPUT */}
                        <div className="space-y-4">
                            <div>
                                <label className="text-xs font-semibold text-white/80 block mb-1.5 uppercase tracking-wide">
                                    WHAT SHOULD THE NEW STORY BE ABOUT?
                                </label>
                                <textarea
                                    rows={3}
                                    placeholder="e.g. A high-stakes comedic bank heist where the characters try to crack a high-security vault..."
                                    value={customPrompt}
                                    onChange={(e) => setCustomPrompt(e.target.value)}
                                    className="w-full p-3 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors"
                                />
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="text-xs font-semibold text-white/80 block mb-1.5">Language / Accent</label>
                                    <select
                                        value={targetLanguage}
                                        onChange={(e) => setTargetLanguage(e.target.value)}
                                        className="w-full p-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-xs text-white focus:outline-none focus:border-indigo-500"
                                    >
                                        <option value="Hinglish / Hindi">Hinglish / Hindi (Viral Punchy)</option>
                                        <option value="English (US)">English (US Standard)</option>
                                        <option value="English (UK)">English (British)</option>
                                        <option value="Spanish">Spanish</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="text-xs font-semibold text-white/80 block mb-1.5">Target Duration</label>
                                    <select
                                        value={targetDuration}
                                        onChange={(e) => setTargetDuration(Number(e.target.value))}
                                        className="w-full p-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-xs text-white focus:outline-none focus:border-indigo-500"
                                    >
                                        <option value={20}>15–20s</option>
                                        <option value={30}>~30s</option>
                                        <option value={45}>~45s</option>
                                        <option value={60}>~60s</option>
                                    </select>
                                </div>
                            </div>

                            <div className="p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex gap-3 items-start mt-2">
                                <Sparkles size={16} className="text-indigo-400 mt-0.5 flex-shrink-0" />
                                <p className="text-xs text-indigo-200/80 leading-relaxed">
                                    CloneFrame extracts and preserves only your selected DNA, generating a completely original storyboard with fresh characters, locations, and dialogue based on your prompt.
                                </p>
                            </div>
                        </div>

                        {/* P3 PHASE D: VALIDATION GATE FINDINGS (422 handler) */}
                        <AnimatePresence>
                            {gateFindings.length > 0 && (
                                <motion.div
                                    initial={{ opacity: 0, y: -6 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0 }}
                                    className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 space-y-2"
                                >
                                    <div className="flex items-center gap-2">
                                        <ShieldAlert size={16} className="text-red-400 flex-shrink-0" />
                                        <span className="text-xs font-bold text-red-300 uppercase tracking-wider">
                                            Validation Gate Findings
                                        </span>
                                    </div>
                                    <ul className="space-y-1 list-disc list-inside">
                                        {gateFindings.map((finding, idx) => (
                                            <li key={idx} className="text-[11px] text-red-200/80 leading-relaxed">
                                                {finding}
                                            </li>
                                        ))}
                                    </ul>
                                    <p className="text-[11px] text-white/50 pt-1">
                                        Adjust your topic or preservation toggles above, then transform again.
                                    </p>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        <div className="flex justify-between items-center pt-2">
                            <button
                                onClick={() => setStep(2)}
                                className="px-4 py-2 rounded-xl text-xs font-semibold text-white/60 hover:text-white"
                            >
                                Back
                            </button>
                            <button
                                onClick={handleTransform}
                                disabled={isTransforming}
                                className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-indigo-600/20 disabled:opacity-50"
                            >
                                {isTransforming ? (
                                    <>
                                        <Loader2 size={14} className="animate-spin" />
                                        <span>Director Drafting Storyboard...</span>
                                    </>
                                ) : (
                                    <>
                                        <span>Generate Storyboard</span>
                                        <ArrowRight size={14} />
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </motion.div>
            )}

            {/* STEP 4: STORYBOARD & SHOT PLANNING */}
            {step === 4 && productionBlueprint && (
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                    <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.08] space-y-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <h2 className="text-base font-semibold text-white flex items-center gap-2">
                                    <Film size={18} className="text-indigo-400" /> Storyboard Breakdown ({productionBlueprint.scenes?.length || 0} Scenes)
                                </h2>
                                <p className="text-xs text-white/50 mt-1">
                                    Review individual shot actions, camera directions, dialogue, and timing before rendering.
                                </p>
                            </div>
                            <span className="text-xs font-semibold text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-1 rounded-full">
                                ~{productionBlueprint.target_duration_seconds || 30}s Estimated Final Duration
                            </span>
                        </div>

                        {/* Scene Cards */}
                        <div className="space-y-3">
                            {productionBlueprint.scenes?.map((scn: any, idx: number) => (
                                <div key={scn.scene_id || idx} className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2.5">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="font-bold text-white/90">Scene {scn.scene_number || idx + 1}: {scn.narrative_purpose || "Action beat"}</span>
                                        <span className="text-white/40 bg-white/[0.05] px-2 py-0.5 rounded">~{scn.estimated_duration_seconds || 8.0}s Expected</span>
                                    </div>
                                    <p className="text-xs text-white/60 italic">{scn.action || "Character performs action"}</p>
                                    {scn.dialogue?.[0]?.text && (
                                        <div className="flex items-center gap-2 p-2 rounded-lg bg-indigo-500/5 border border-indigo-500/10 text-xs text-indigo-200">
                                            <Volume2 size={13} className="text-indigo-400 flex-shrink-0" />
                                            <span>"{scn.dialogue[0].text}"</span>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>

                        <div className="flex justify-between items-center pt-2">
                            <button
                                onClick={() => setStep(3)}
                                className="px-4 py-2 rounded-xl text-xs font-semibold text-white/60 hover:text-white"
                            >
                                Back to Transform
                            </button>
                            <button
                                onClick={handleGenerate}
                                disabled={isGenerating}
                                className="px-7 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg shadow-emerald-600/25 transition-all"
                            >
                                <Zap size={14} />
                                <span>Approve & Render Final Video</span>
                            </button>
                        </div>
                    </div>
                </motion.div>
            )}

            {/* STEP 5: PRODUCTION & FINAL VIDEO */}
            {step === 5 && (
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                    <div className="p-6 md:p-8 rounded-2xl bg-white/[0.02] border border-white/[0.08] text-center space-y-6">
                        {isGenerating && (
                            <div className="space-y-6 py-4">
                                {/* Header badge & SSE indicator */}
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <Loader2 size={18} className="animate-spin text-indigo-400" />
                                        <h3 className="text-base font-bold text-white">Live Production Engine</h3>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className={cn(
                                            "w-2 h-2 rounded-full",
                                            sseConnected ? "bg-emerald-400 animate-pulse" : "bg-yellow-400"
                                        )} />
                                        <span className="text-[11px] font-mono text-white/50">
                                            {sseConnected ? "SSE LIVE STREAM" : "POLLING ACTIVE"}
                                        </span>
                                    </div>
                                </div>

                                {/* Active Stage and Scene Counters */}
                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                    <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] text-left">
                                        <span className="text-[10px] uppercase font-bold text-white/40 tracking-wider block">Current Stage</span>
                                        <span className="text-sm font-semibold text-indigo-300 truncate block mt-0.5">{currentStage}</span>
                                    </div>
                                    <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] text-left">
                                        <span className="text-[10px] uppercase font-bold text-white/40 tracking-wider block">Scene Progress</span>
                                        <span className="text-sm font-semibold text-white block mt-0.5">
                                            Scene {currentSceneNum} <span className="text-white/40">/ {totalScenesNum}</span>
                                        </span>
                                    </div>
                                    <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] text-left">
                                        <span className="text-[10px] uppercase font-bold text-white/40 tracking-wider block">Quality Review</span>
                                        <span className={cn(
                                            "text-sm font-bold block mt-0.5",
                                            qualityScore !== null
                                                ? qualityScore >= 7.0 ? "text-emerald-400" : "text-yellow-400"
                                                : "text-white/40"
                                        )}>
                                            {qualityScore !== null ? `${qualityScore.toFixed(1)} / 10.0` : "Pending Review"}
                                        </span>
                                    </div>
                                </div>

                                {/* Live Progress Bar */}
                                <div className="space-y-1.5 text-left">
                                    <div className="flex justify-between text-xs text-white/60">
                                        <span>Pipeline Progress</span>
                                        <span>{Math.round((currentSceneNum / Math.max(1, totalScenesNum)) * 100)}%</span>
                                    </div>
                                    <div className="w-full h-2 rounded-full bg-white/[0.05] overflow-hidden">
                                        <motion.div
                                            className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-500"
                                            animate={{ width: `${Math.min(100, Math.round((currentSceneNum / Math.max(1, totalScenesNum)) * 100))}%` }}
                                            transition={{ duration: 0.5 }}
                                        />
                                    </div>
                                </div>

                                {/* Live Telemetry Logs Terminal */}
                                <div className="p-4 rounded-xl bg-black/60 border border-white/[0.08] text-left font-mono space-y-2">
                                    <div className="flex items-center justify-between text-[11px] text-white/40 border-b border-white/[0.06] pb-2">
                                        <span>REAL-TIME TELEMETRY LOGS</span>
                                        <span>FAIL-CLOSED ARCHITECTURE</span>
                                    </div>
                                    <div className="max-h-40 overflow-y-auto space-y-1.5 text-xs">
                                        {telemetryLogs.length === 0 ? (
                                            <p className="text-white/30 text-[11px]">Connecting to generation stream...</p>
                                        ) : (
                                            telemetryLogs.map((log, i) => (
                                                <div key={i} className="flex items-start gap-2 text-[11px]">
                                                    <span className="text-white/30 flex-shrink-0">{log.time}</span>
                                                    <span className={cn(
                                                        log.type === "success" && "text-emerald-400",
                                                        log.type === "warning" && "text-yellow-400",
                                                        log.type === "error" && "text-red-400",
                                                        log.type === "veo" && "text-purple-300",
                                                        log.type === "audio" && "text-blue-300",
                                                        log.type === "scene" && "text-indigo-300",
                                                        log.type === "system" && "text-white/60",
                                                        log.type === "info" && "text-white/80"
                                                    )}>
                                                        {log.msg}
                                                    </span>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}

                        {!isGenerating && finalVideoUrl && (
                            <div className="space-y-6">
                                <div className="flex items-center justify-center gap-2 text-emerald-400">
                                    <CheckCircle2 size={24} />
                                    <h3 className="text-xl font-bold text-white">Generation Certified & Complete</h3>
                                </div>

                                <div className="max-w-sm mx-auto rounded-2xl overflow-hidden border border-white/[0.1] shadow-2xl bg-black">
                                    <video
                                        src={finalVideoUrl}
                                        controls
                                        autoPlay
                                        className="w-full aspect-[9/16] object-cover"
                                    />
                                </div>

                                <div className="flex justify-center gap-3">
                                    <a
                                        href={finalVideoUrl}
                                        download="cloneframe_video.mp4"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-indigo-600/20"
                                    >
                                        <Download size={14} />
                                        <span>Download MP4</span>
                                    </a>
                                    <button
                                        onClick={() => {
                                            setStep(1);
                                            setFinalVideoUrl(null);
                                        }}
                                        className="px-5 py-2.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.08] text-white text-xs font-semibold flex items-center gap-2 border border-white/[0.08]"
                                    >
                                        <RefreshCw size={14} />
                                        <span>Clone Another Video</span>
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </motion.div>
            )}
        </div>
    );
}
