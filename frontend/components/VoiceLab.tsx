'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Mic, Play, Download, Sliders, Activity, Disc, Loader2, Lock } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { API_BASE_URL } from '@/lib/config';
import { handleAppError } from '@/lib/errorHandler';
import { usePermission } from '@/hooks/usePermission';
import { usePlan } from '@/context/PlanContext';

import VoiceCloningModal from './VoiceCloningModal';
import { useAuth } from '@/context/AuthContext';

export default function VoiceLab() {
    const [script, setScript] = useState('');
    const [voiceModel, setVoiceModel] = useState('Adam');
    const [stability, setStability] = useState(50);
    const [isGenerating, setIsGenerating] = useState(false);
    const [audioUrl, setAudioUrl] = useState<string | null>(null);
    const { canUse } = usePermission();

    const { deductCredits, refundCredits, capabilities } = usePlan();
    const [showPremiumModal, setShowPremiumModal] = useState(false);

    // Cloning State
    const [showCloneModal, setShowCloneModal] = useState(false);
    const [clonedVoiceId, setClonedVoiceId] = useState<string | null>(null); // In real app, fetch from DB
    const { user } = useAuth();

    // Audio Player Refs
    const audioRef = useRef<HTMLAudioElement | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);

    // Auto-play when audioUrl changes
    useEffect(() => {
        if (audioUrl && audioRef.current) {
            audioRef.current.src = audioUrl;
            audioRef.current.play().then(() => setIsPlaying(true)).catch(console.error);
        }
    }, [audioUrl]);

    const handleVoiceChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const val = e.target.value;
        if (val === 'Clone') {
            if (!clonedVoiceId) {
                // If no voice cloned yet, show modal
                setShowCloneModal(true);
            }
            setVoiceModel('Clone');
        } else {
            setVoiceModel(val);
        }
    };

    const handleCloneSuccess = (voiceId: string) => {
        setClonedVoiceId(voiceId);
        setVoiceModel('Clone');
        // Ideally save to user profile here or re-fetch profile
    };

    const handleGenerate = async () => {
        if (!script) return;

        const cost = 2; // Fixed cost for voice
        if (!deductCredits(cost)) return;

        setIsGenerating(true);
        setAudioUrl(null);
        setIsPlaying(false);

        // Network Safety
        const handleBeforeUnload = (e: BeforeUnloadEvent) => {
            e.preventDefault();
            e.returnValue = '';
        };
        window.addEventListener('beforeunload', handleBeforeUnload);

        try {
            const res = await fetch(`${API_BASE_URL}/generate-voiceover`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: script,
                    voice_name: voiceModel === 'Clone' && clonedVoiceId ? clonedVoiceId :
                        voiceModel === 'Adam' ? 'en-US-Journey-D' :
                            voiceModel === 'James' ? 'en-US-Studio-M' :
                                voiceModel === 'Aditi' ? 'en-IN-Wavenet-C' : 'en-US-Journey-F'
                })
            });

            window.removeEventListener('beforeunload', handleBeforeUnload);

            if (!res.ok) throw new Error('Voice generation failed');
            const data = await res.json();
            setAudioUrl(data.audio_url);
        } catch (err) {
            window.removeEventListener('beforeunload', handleBeforeUnload);
            handleAppError(err, () => refundCredits(cost));
        } finally {
            setIsGenerating(false);
        }
    };

    const togglePlay = () => {
        if (!audioRef.current || !audioUrl) return;
        if (isPlaying) {
            audioRef.current.pause();
            setIsPlaying(false);
        } else {
            audioRef.current.play();
            setIsPlaying(true);
        }
    };

    return (
        <div className="flex h-[calc(100vh-100px)] gap-6 animate-in fade-in zoom-in-95 duration-500">
            <VoiceCloningModal
                isOpen={showCloneModal}
                onClose={() => setShowCloneModal(false)}
                onSuccess={handleCloneSuccess}
                userId={user?.uid || 'anon'}
            />

            {/* Hidden Audio Element */}
            <audio
                ref={audioRef}
                onEnded={() => setIsPlaying(false)}
                onError={(e) => console.error("Audio Error:", e)}
            />

            {/* LEFT COLUMN: Controls */}
            <div className="w-1/2 flex flex-col gap-6">
                <div className="space-y-1">
                    <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-blue-600">
                        Voice Lab
                    </h1>
                    <p className="text-zinc-400">Professional Neural Text-to-Speech Studio</p>
                </div>

                {/* Input Area */}
                <div className="flex-1 bg-zinc-900/50 border border-zinc-800 rounded-3xl p-6 relative group focus-within:ring-2 focus-within:ring-cyan-500/50 transition-all">
                    <textarea
                        value={script}
                        onChange={(e) => setScript(e.target.value)}
                        placeholder="Type your script here..."
                        className="w-full h-full bg-transparent resize-none outline-none text-lg text-white font-mono placeholder:text-zinc-600"
                        maxLength={5000}
                    />
                    <div className="absolute bottom-4 right-6 text-xs font-mono text-zinc-500 group-focus-within:text-cyan-500">
                        {script.length} / 5000
                    </div>
                </div>

                {/* Controls Row */}
                <div className="grid grid-cols-2 gap-4">
                    {/* Voice Selection */}
                    <div className="bg-zinc-900 border border-zinc-800 p-4 rounded-xl flex flex-col gap-2">
                        <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-2">
                            <Mic size={14} className="text-cyan-500" /> Voice Model
                        </label>
                        <select
                            value={voiceModel}
                            onChange={(e) => {
                                const val = e.target.value;

                                // Logic: Gate Premium Voices
                                // Adam (Journey) & James (Studio) are Premium. Aditi (Standard) is free-ish.
                                const isPremium = ['Adam', 'James'].includes(val);
                                const isLocked = isPremium && !capabilities?.premium_voices;

                                if (isLocked) {
                                    // Trigger Upgrade Modal
                                    // We'll use a local state for this since we can't easily inject a modal from inside select
                                    // But wait, we need to render the modal. 
                                    // We will set a state variable 'showPremiumModal'
                                    setShowPremiumModal(true);
                                    return;
                                }

                                if (val === 'Clone') {
                                    if (!clonedVoiceId) {
                                        setShowCloneModal(true);
                                    }
                                    setVoiceModel('Clone');
                                } else {
                                    setVoiceModel(val);
                                }
                            }}
                            className="bg-zinc-950 border border-zinc-800 text-white text-sm rounded-lg p-3 outline-none focus:border-cyan-500 transition-all"
                        >
                            <option value="Aditi">Aditi (Standard)</option>
                            <option value="Adam">
                                Adam (Premium Journey) {!capabilities?.premium_voices ? '🔒' : ''}
                            </option>
                            <option value="James">
                                James (Premium Studio) {!capabilities?.premium_voices ? '🔒' : ''}
                            </option>
                            <option value="Clone">
                                {clonedVoiceId ? "My AI Voice (Ready) ✅" : "Clone My Voice (Beta)"}
                                {!canUse('voice_cloning') ? '🔒' : ''}
                            </option>
                        </select>
                    </div>

                    {/* Stability Slider */}
                    <div className="bg-zinc-900 border border-zinc-800 p-4 rounded-xl flex flex-col gap-2">
                        <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-2">
                            <Sliders size={14} className="text-blue-500" /> Stability: {stability}%
                        </label>
                        <input
                            type="range"
                            min="0"
                            max="100"
                            value={stability}
                            onChange={(e) => setStability(Number(e.target.value))}
                            className="w-full h-2 bg-zinc-950 rounded-full appearance-none cursor-pointer accent-cyan-500"
                        />
                    </div>
                </div>

                {/* Generate Button / Coming Soon */}
                <button
                    onClick={handleGenerate}
                    disabled={isGenerating || !script}
                    className="w-full py-5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-bold text-lg rounded-2xl shadow-lg shadow-cyan-500/20 transition-all transform active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
                >
                    {isGenerating ? <Loader2 className="animate-spin" size={24} /> : <Activity size={24} />}
                    {isGenerating ? 'Synthesizing...' : 'Generate Voice'}
                </button>
            </div>

            {/* RIGHT COLUMN: Visualizer */}
            <div className="w-1/2 flex flex-col">
                <div className="flex-1 bg-zinc-950 border border-zinc-800 rounded-3xl relative overflow-hidden flex flex-col items-center justify-center p-12">
                    {/* Cyan Glow Background */}
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px] bg-cyan-500/20 blur-[100px] rounded-full pointer-events-none" />

                    {/* Waveform Visualizer */}
                    <div className="flex items-center gap-1 h-32 mb-8">
                        {Array.from({ length: 40 }).map((_, i) => (
                            <motion.div
                                key={i}
                                className="w-2 bg-cyan-400 rounded-full"
                                initial={{ height: 4 }}
                                animate={{
                                    height: isGenerating || isPlaying ? [8, 64, 16, 48, 8] : 4, // Animate on play too!
                                    backgroundColor: isGenerating || isPlaying ? '#22d3ee' : '#3f3f46'
                                }}
                                transition={{
                                    repeat: Infinity,
                                    duration: 1,
                                    delay: i * 0.05,
                                    ease: "linear"
                                }}
                            />
                        ))}
                    </div>

                    <div className="text-center z-10">
                        {isGenerating ? (
                            <p className="text-cyan-400 font-mono animate-pulse">Processing Neural Audio...</p>
                        ) : audioUrl ? (
                            <div className="flex flex-col items-center animate-in slide-in-from-bottom-5">
                                <div className="w-20 h-20 bg-cyan-500 rounded-full flex items-center justify-center text-black mb-4 shadow-lg shadow-cyan-500/50">
                                    <Disc size={40} className={isPlaying ? "animate-spin" : ""} />
                                </div>
                                <h3 className="text-2xl font-bold text-white mb-2">Audio Ready</h3>
                                <p className="text-zinc-500 mb-6">Generated with {voiceModel === 'Clone' ? 'Your AI Voice' : voiceModel}</p>
                            </div>
                        ) : (
                            <p className="text-zinc-600 font-medium">Ready to Synthesize</p>
                        )}
                    </div>
                </div>

                {/* Player Bar */}
                {audioUrl && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mt-6 bg-zinc-900 border border-zinc-800 rounded-2xl p-4 flex items-center gap-4 shadow-2xl"
                    >
                        <button
                            onClick={togglePlay}
                            className="w-12 h-12 bg-cyan-500 rounded-full flex items-center justify-center text-black hover:bg-cyan-400 transition-colors"
                        >
                            {isPlaying ? (
                                <div className="w-4 h-4 flex gap-1 justify-center items-center">
                                    <div className="w-1 h-full bg-black rounded-full" />
                                    <div className="w-1 h-full bg-black rounded-full" />
                                </div>
                            ) : (
                                <Play size={20} fill="currentColor" />
                            )}
                        </button>

                        <div className="flex-1">
                            <div className="h-10 bg-zinc-950 rounded-lg overflow-hidden relative">
                                {/* Fake progress bar for look */}
                                <div className="absolute top-0 left-0 bottom-0 w-1/3 bg-cyan-500/20 border-r-2 border-cyan-500" />
                                <div className="absolute inset-0 flex items-center justify-between px-3">
                                    <span className="text-xs font-mono text-cyan-500">0:12</span>
                                    <span className="text-xs font-mono text-zinc-600">0:34</span>
                                </div>
                            </div>
                        </div>

                        <a
                            href={audioUrl}
                            download="voiceover.mp3"
                            className="p-3 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-all"
                        >
                            <Download size={20} />
                        </a>
                    </motion.div>
                )}
            </div>

            {/* PREMIUM UPGRADE MODAL */}
            {showPremiumModal && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
                    onClick={() => setShowPremiumModal(false)}
                >
                    <div
                        className="w-full max-w-md bg-zinc-900 border border-zinc-700 rounded-3xl p-8 relative overflow-hidden text-center space-y-6"
                        onClick={e => e.stopPropagation()}
                    >
                        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500" />
                        <div className="w-16 h-16 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/25 mx-auto">
                            <Mic size={32} className="text-white" />
                        </div>
                        <div>
                            <h3 className="text-2xl font-black text-white mb-2">Unlock Premium Voices</h3>
                            <p className="text-zinc-400 text-sm">
                                Ultra-realistic 'Journey' and 'Studio' voices are exclusive to the <strong>Creator Plan</strong>.
                            </p>
                        </div>
                        <button
                            onClick={() => window.location.href = '/pricing'}
                            className="w-full py-4 bg-white text-black font-bold rounded-xl hover:bg-zinc-200 transition-colors"
                        >
                            Upgrade to Creator
                        </button>
                        <button
                            onClick={() => setShowPremiumModal(false)}
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
