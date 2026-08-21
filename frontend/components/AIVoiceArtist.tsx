'use client';
import { useState, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Mic, Play, Wand2, Loader2, FileVideo, Edit2, Volume2, ChevronRight, ChevronLeft, Check, Download, Video } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { API_BASE_URL } from '@/lib/config';
import { toast } from 'sonner';

const VOICES = [
    { id: 'en-US-Journey-D', label: 'American Male', gender: 'Male', style: 'Deep Narrator' },
    { id: 'en-US-Journey-F', label: 'American Female', gender: 'Female', style: 'Casual' },
    { id: 'en-GB-Journey-D', label: 'British Male', gender: 'Male', style: 'Elegant' },
    { id: 'en-AU-Journey-F', label: 'Australian Female', gender: 'Female', style: 'Friendly' },
];

export default function AIVoiceArtist() {
    const { user } = useAuth();
    const [step, setStep] = useState(1);
    const [script, setScript] = useState(''); // text
    const [analyzeFile, setAnalyzeFile] = useState<File | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [isGenerating, setIsGenerating] = useState(false);

    // Merge State
    const [isMerging, setIsMerging] = useState(false);
    const [finalVideoUrl, setFinalVideoUrl] = useState('');

    // Customize State
    const [platform, setPlatform] = useState('TikTok');
    const [duration, setDuration] = useState('30 seconds');
    const [mood, setMood] = useState('Informative');

    const [audioUrl, setAudioUrl] = useState<string | null>(null);
    const [selectedVoice, setSelectedVoice] = useState('en-US-Journey-D'); // Default

    // 1. 🧠 AI SCRIPT GENERATOR
    const handleAnalyzeVideo = async () => {
        if (!analyzeFile || !user) return;
        setIsAnalyzing(true);

        const formData = new FormData();
        formData.append('file', analyzeFile);
        formData.append('video_format', platform);
        formData.append('duration', duration);
        formData.append('mood', mood);
        try {
            const token = await user.getIdToken();
            const res = await fetch(`${API_BASE_URL}/analyze-vision`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData,
            });
            const data = await res.json();
            if (data.script) {
                setScript(data.script);
                setStep(1); // Ensure we are on script step
            } else {
                toast.error("AI couldn't write a script.", { description: 'Try a different video or style.' });
            }
        } catch (err) {
            console.error(err);
            toast.error('Analysis failed. Please try again.');
        } finally {
            setIsAnalyzing(false);
        }
    };

    // 2. 🗣️ VOICE GENERATOR
    const handleGenerate = async () => {
        if (!script || !user) return;
        setIsGenerating(true);

        try {
            const token = await user.getIdToken();
            const res = await fetch(`${API_BASE_URL}/generate-voiceover`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    text: script,
                    voice_name: selectedVoice
                }),
            });
            const data = await res.json();
            if (data.audio_url) {
                setAudioUrl(data.audio_url);
                setStep(3);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setIsGenerating(false);
        }
    };

    const WaveformVisualizer = ({ isPlaying }: { isPlaying: boolean }) => (
        <div className="flex items-center justify-center gap-1 h-12 w-full max-w-md mx-auto my-6">
            {[...Array(20)].map((_, i) => (
                <motion.div
                    key={i}
                    animate={{
                        height: isPlaying ? [10, Math.random() * 40 + 10, 10] : 8,
                        opacity: isPlaying ? 1 : 0.3
                    }}
                    transition={{
                        duration: 0.5,
                        repeat: Infinity,
                        delay: i * 0.05,
                        ease: "easeInOut"
                    }}
                    className="w-1.5 bg-cyan-400 rounded-full"
                />
            ))}
        </div>
    );

    const VoiceCard = ({ v, selected, onSelect }: { v: any, selected: boolean, onSelect: () => void }) => (
        <div
            onClick={onSelect}
            className={cn(
                "cursor-pointer group relative p-4 rounded-xl border transition-all overflow-hidden bg-zinc-900 border-zinc-800",
                selected
                    ? "bg-cyan-950/30 border-cyan-400 shadow-[0_0_20px_rgba(34,211,238,0.2)]"
                    : "hover:border-zinc-700 hover:bg-zinc-800/50"
            )}
        >
            <div className="flex items-center gap-4 relative z-10">
                <div className={cn(
                    "w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold border transition-colors",
                    selected ? "bg-cyan-400 text-black border-cyan-400" : "bg-zinc-800 text-zinc-400 border-zinc-700 group-hover:bg-zinc-700"
                )}>
                    {v.label.charAt(0)}
                </div>
                <div>
                    <h4 className={cn("font-bold text-sm", selected ? "text-cyan-400" : "text-zinc-200")}>{v.label}</h4>
                    <p className="text-xs text-zinc-500">{v.gender} • {v.style}</p>
                </div>
            </div>
            {selected && <div className="absolute inset-0 bg-gradient-to-r from-cyan-400/10 to-transparent pointer-events-none" />}
        </div>
    );

    const renderScriptStep = () => (
        <div className="space-y-6 animate-in fade-in slide-in-from-right-8 duration-500">
            <div className="flex items-center justify-between">
                <h3 className="text-2xl font-bold text-white flex items-center gap-3">
                    <span className="p-2 bg-zinc-800 rounded-lg"><Edit2 size={20} className="text-cyan-400" /></span>
                    Script Analysis
                </h3>
                <span className="text-xs font-mono text-zinc-500 uppercase tracking-widest">PHASE 1/3</span>
            </div>

            {/* Video Upload Analysis Section */}
            <div className="bg-zinc-900/50 p-6 rounded-2xl border border-zinc-800 mb-6">
                <h4 className="text-sm font-bold text-zinc-400 mb-4 uppercase tracking-wider flex items-center gap-2">
                    <Video size={14} /> AI Vision Analysis (Optional)
                </h4>
                <div className="flex items-center gap-4">
                    <input
                        type="file"
                        accept="video/mp4"
                        onChange={(e) => setAnalyzeFile(e.target.files?.[0] || null)}
                        className="flex-1 text-sm text-zinc-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-zinc-800 file:text-cyan-400 hover:file:bg-zinc-700 cursor-pointer"
                    />
                    <button
                        onClick={handleAnalyzeVideo}
                        disabled={!analyzeFile || isAnalyzing}
                        className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg text-sm font-bold flex items-center gap-2 transition-colors disabled:opacity-50"
                    >
                        {isAnalyzing ? <Loader2 className="animate-spin" size={14} /> : <Wand2 size={14} />}
                        {isAnalyzing ? 'Analyzing...' : 'Auto-Generate Script'}
                    </button>
                </div>
            </div>

            <div className="relative group">
                <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-2xl blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
                <div className="relative bg-zinc-950 rounded-2xl border border-zinc-800 p-1">
                    <textarea
                        value={script}
                        onChange={(e) => setScript(e.target.value)}
                        className="w-full h-64 bg-zinc-900/50 p-6 rounded-xl text-lg text-zinc-300 font-mono leading-relaxed focus:outline-none resize-none custom-scrollbar placeholder-zinc-700"
                        placeholder="Paste your script here manually or use the AI Vision tool above to generate one from a video..."
                    />
                </div>
            </div>

            <div className="flex justify-end">
                <button
                    onClick={() => setStep(2)}
                    disabled={!script}
                    className="px-8 py-3 bg-white hover:bg-zinc-200 text-black font-bold rounded-lg shadow-lg flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    Next Phase <ChevronRight size={18} />
                </button>
            </div>
        </div>
    );

    const renderVoiceStep = () => (
        <div className="space-y-8 animate-in fade-in slide-in-from-right-8 duration-500">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <button onClick={() => setStep(1)} className="p-2 hover:bg-zinc-800 rounded-lg transition-colors"><ChevronLeft size={20} /></button>
                    <h3 className="text-2xl font-bold text-white flex items-center gap-3">
                        <span className="p-2 bg-zinc-800 rounded-lg"><Mic size={20} className="text-cyan-400" /></span>
                        Voice Selection
                    </h3>
                </div>
                <span className="text-xs font-mono text-zinc-500 uppercase tracking-widest">PHASE 2/3</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {VOICES.map((v) => (
                    <VoiceCard
                        key={v.id}
                        v={v}
                        selected={selectedVoice === v.id}
                        onSelect={() => setSelectedVoice(v.id)}
                    />
                ))}
            </div>

            <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="w-full py-6 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-black text-xl rounded-2xl shadow-xl hover:shadow-cyan-500/20 transform transition-all active:scale-[0.98] flex items-center justify-center gap-3"
            >
                {isGenerating ? <Loader2 className="animate-spin" /> : <Wand2 />}
                {isGenerating ? 'Synthesizing Audio...' : 'Generate Voiceover'}
            </button>
        </div>
    );

    const renderReviewStep = () => (
        <div className="space-y-8 animate-in fade-in slide-in-from-right-8 duration-500 text-center max-w-2xl mx-auto">
            <div className="w-24 h-24 mx-auto bg-green-500/10 rounded-full flex items-center justify-center border border-green-500/20 shadow-[0_0_40px_rgba(34,197,94,0.1)] mb-6">
                <Check size={48} className="text-green-500" />
            </div>

            <h3 className="text-3xl font-bold text-white">Audio Synthesized</h3>

            <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-8 shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 right-0 p-20 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none -translate-y-10 translate-x-10"></div>

                <WaveformVisualizer isPlaying={true} />

                <div className="mt-8 flex justify-center">
                    <audio src={audioUrl!} controls className="w-full" />
                </div>
            </div>

            <div className="flex gap-4 justify-center">
                <button
                    onClick={() => { setStep(1); setAudioUrl(null); }}
                    className="px-6 py-3 rounded-xl border border-zinc-700 hover:bg-zinc-800 text-zinc-300 font-bold transition-colors"
                >
                    Start Over
                </button>
                <button
                    onClick={() => window.open(audioUrl!, '_blank')}
                    className="px-8 py-3 bg-cyan-500 hover:bg-cyan-400 text-black font-bold rounded-xl shadow-lg shadow-cyan-500/20 transition-transform hover:-translate-y-1 flex items-center gap-2"
                >
                    <Download size={18} /> Download
                </button>
            </div>
        </div>
    );

    return (
        <div className="max-w-[1200px] mx-auto p-4 md:p-8 min-h-[calc(100vh-100px)]">
            {/* Main Studio Container */}
            <div className="bg-black/80 backdrop-blur-xl border border-zinc-800 rounded-[40px] shadow-2xl overflow-hidden min-h-[600px] flex flex-col md:flex-row">

                {/* Sidebar Navigation */}
                <div className="w-full md:w-64 bg-zinc-950 border-r border-zinc-800 p-8 flex flex-col justify-between">
                    <div>
                        <h2 className="text-xl font-black text-white tracking-tighter mb-8 flex items-center gap-2">
                            <div className="w-8 h-8 rounded bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white">
                                <Volume2 size={16} />
                            </div>
                            <span>VOICE<br />STUDIO</span>
                        </h2>

                        <nav className="space-y-2">
                            {[
                                { s: 1, label: 'Script', icon: Edit2 },
                                { s: 2, label: 'Voice', icon: Mic },
                                { s: 3, label: 'Review', icon: Play }
                            ].map((item) => (
                                <div
                                    key={item.s}
                                    onClick={() => setStep(item.s)}
                                    className={cn(
                                        "flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold transition-all cursor-pointer",
                                        step === item.s
                                            ? "bg-cyan-950/50 text-cyan-400 border border-cyan-500/20"
                                            : "text-zinc-500 hover:bg-zinc-900 hover:text-zinc-300"
                                    )}
                                >
                                    <item.icon size={16} />
                                    {item.label}
                                </div>
                            ))}
                        </nav>
                    </div>

                    <div className="text-xs text-zinc-600 font-mono">
                        STATUS: READY<br />
                        LATENCY: 12ms
                    </div>
                </div>

                {/* Content Area */}
                <div className="flex-1 p-8 md:p-12 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-zinc-900/50 via-black to-black relative">
                    {/* Background Noise Texture */}
                    <div className="absolute inset-0 opacity-[0.03] pointer-events-none bg-[url('https://grainy-gradients.vercel.app/noise.svg')]"></div>

                    {step === 1 && renderScriptStep()}
                    {step === 2 && renderVoiceStep()}
                    {step === 3 && renderReviewStep()}
                </div>
            </div>
        </div>
    );
}
