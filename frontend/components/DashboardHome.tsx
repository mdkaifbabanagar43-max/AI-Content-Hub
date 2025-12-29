import { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePlan } from '@/context/PlanContext';
import { motion } from 'framer-motion';
import {
    Video, Zap, HardDrive,
    Scissors, Mic, Globe, ArrowRight, Activity,
    Cpu, Wifi, Server, CheckCircle2, Play, LayoutDashboard, X, Download, Sparkles, Plus
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { API_BASE_URL } from '@/lib/config';
import { forceDownload } from '@/lib/download';
import { Skeleton } from './ui/Skeleton';

interface DashboardHomeProps {
    setActiveTab: (tab: string) => void;
}

export default function DashboardHome({ setActiveTab }: DashboardHomeProps) {
    const { user } = useAuth();
    const { credits, userPlan } = usePlan();
    const [projectCount, setProjectCount] = useState(0);
    const [recentProjects, setRecentProjects] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    // Plan Limits for Progress Bar
    // Plan Limits for Progress Bar (Synced with backend/config.py)
    // Starter: 500, Creator: 2000, Agency: 10000
    // Logic: Map 'pro' to 'creator' or 'starter' depending on business logic. 
    // Assuming 'pro' was old name for 'creator' or strictly intermediate. 
    // Given user said "creators 2000", we align with that.
    const planLimit = userPlan === 'starter' ? 500 : (userPlan === 'creator' || userPlan === 'pro') ? 2000 : userPlan === 'agency' ? 10000 : 500;
    const usagePercent = Math.min(100, Math.max(0, ((planLimit - credits) / planLimit) * 100)); // Assuming credits starts at max and decreases. 
    // Wait, typical credit systems: you start with X and it goes down. So usage = (Max - Current) / Max.
    // However, if credits is simply "Available Credits", the bar should probably show "Remaining".
    // Let's show "Credits Remaining" as a bar that is full and empties? Or "Credits Used" (Empty -> Full).
    // User asked for "Credits used / remaining".
    // Let's do a "Fuel Gauge" style: Full bar = 100% credits.

    useEffect(() => {
        if (!user) return;

        // Fetch Stats
        user.getIdToken().then(token => {
            fetch(`${API_BASE_URL}/my-projects`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })
                .then(res => res.json())
                .then(data => {
                    if (data.projects) {
                        setProjectCount(data.projects.length);
                        setRecentProjects(data.projects.slice(0, 3)); // Top 3
                    }
                })
                .catch(err => console.error("Stats fetch error:", err))
                .finally(() => setIsLoading(false));
        });
    }, [user]);


    // --- MODAL LOGIC ---
    const [selectedProject, setSelectedProject] = useState<any>(null);

    // --- SKELETON ---
    if (isLoading) {
        return (
            <div className="space-y-10 animate-in fade-in duration-500 pb-12">
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div className="space-y-3">
                        <Skeleton className="h-10 w-64 md:w-96" />
                        <Skeleton className="h-6 w-48" />
                    </div>
                    <Skeleton className="h-24 w-full md:w-64 rounded-2xl" />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2 h-[300px] rounded-[32px] overflow-hidden">
                        <Skeleton className="w-full h-full" />
                    </div>
                    <div className="flex flex-col gap-4">
                        {[1, 2, 3].map(i => (
                            <Skeleton key={i} className="flex-1 h-24 rounded-[24px]" />
                        ))}
                    </div>
                </div>

                <div>
                    <div className="flex justify-between items-center mb-6 px-2">
                        <Skeleton className="h-8 w-40" />
                        <Skeleton className="h-4 w-16" />
                    </div>
                    <div className="bg-[#0A0A0A] border border-white/5 rounded-[32px] p-2 space-y-2">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="flex items-center gap-5 p-4">
                                <Skeleton className="w-32 h-20 rounded-xl shrink-0" />
                                <div className="flex-1 space-y-2">
                                    <Skeleton className="h-5 w-48" />
                                    <div className="flex gap-3">
                                        <Skeleton className="h-4 w-16" />
                                        <Skeleton className="h-4 w-24" />
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-10 animate-in fade-in duration-700 pb-12">

            {/* MODAL OVERLAY */}
            {selectedProject && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200" onClick={() => setSelectedProject(null)}>
                    <div
                        className="bg-[#0A0A0A] border border-white/10 rounded-3xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden shadow-2xl relative animate-in zoom-in-95 duration-200"
                        onClick={e => e.stopPropagation()}
                    >
                        <button
                            onClick={() => setSelectedProject(null)}
                            className="absolute top-4 right-4 z-10 p-2 bg-black/50 hover:bg-black/80 rounded-full text-white transition-colors"
                        >
                            <X size={20} />
                        </button>

                        <div className="flex-1 bg-black relative aspect-video flex items-center justify-center">
                            {selectedProject.video_url ? (
                                <video src={selectedProject.video_url} controls autoPlay className="w-full h-full object-contain" />
                            ) : (
                                <div className="text-zinc-500 flex flex-col items-center">
                                    <Video size={48} className="mb-4 opacity-50" />
                                    <p>No video source available.</p>
                                </div>
                            )}
                        </div>

                        <div className="p-6 bg-[#0A0A0A]">
                            <h2 className="text-2xl font-bold text-white mb-2">{selectedProject.topic || selectedProject.title || "Untitled Project"}</h2>
                            <div className="flex items-center gap-4 text-sm text-zinc-400 font-mono">
                                <span className="px-2 py-1 bg-white/5 rounded border border-white/5 uppercase">{selectedProject.platform || 'Unknown'}</span>
                                <span className="px-2 py-1 bg-white/5 rounded border border-white/5 uppercase">{selectedProject.mood || 'Standard'}</span>
                                <span>{new Date(selectedProject.created_at).toLocaleDateString()}</span>
                            </div>
                            <div className="mt-6 flex justify-end gap-3">
                                <button
                                    onClick={() => forceDownload(selectedProject.video_url, `project-${selectedProject.id}.mp4`)}
                                    className="px-6 py-2 bg-white text-black font-bold rounded-lg hover:bg-zinc-200 transition-colors flex items-center gap-2"
                                >
                                    <Download size={16} /> Download
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* 1. TOP SECTION: WELCOME & USAGE */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div>
                    <h1 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight mb-2">
                        👋 Welcome back, <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">{user?.displayName?.split(' ')[0] || 'Creator'}</span>
                    </h1>
                    <p className="text-zinc-400 text-lg">
                        Ready to create your next viral video?
                    </p>
                </div>

                {/* Usage Indicator */}
                <div className="bg-white/5 border border-white/5 rounded-2xl p-4 w-full md:w-64">
                    <div className="flex justify-between items-center mb-2">
                        <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Credits</span>
                        <span className="text-sm font-bold text-white">{credits} <span className="text-zinc-500">/ {planLimit}</span></span>
                    </div>
                    {/* Progress Bar */}
                    <div className="h-2 w-full bg-white/10 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
                            style={{ width: `${(credits / planLimit) * 100}%` }}
                        />
                    </div>
                    <p className="text-[10px] text-zinc-500 mt-2 text-center">
                        Credits deducted only after preview.
                    </p>
                </div>
            </div>

            {/* 2. PRIMARY ACTION & QUICK ACTIONS GRID */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* Primary Action Card (Span 2 cols on large screens) */}
                <div className="lg:col-span-2 group relative overflow-hidden rounded-[32px] bg-gradient-to-br from-indigo-900/40 to-[#0A0A0A] border border-indigo-500/20 hover:border-indigo-500/40 transition-all p-8 md:p-10 flex flex-col justify-between min-h-[300px]">
                    <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20"></div>
                    <div className="absolute top-0 right-0 p-12 opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110 duration-700">
                        <Sparkles size={200} className="text-indigo-500" />
                    </div>

                    <div className="relative z-10 max-w-lg">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 text-xs font-bold uppercase tracking-wider mb-4">
                            <Sparkles size={12} /> Most Popular
                        </div>
                        <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 leading-tight">
                            Idea Studio
                        </h2>
                        <p className="text-lg text-zinc-300 leading-relaxed mb-8">
                            Turn a simple text idea into a ready-to-post video with AI scripting, voice, and visuals.
                        </p>
                    </div>

                    <div className="relative z-10">
                        <button
                            onClick={() => setActiveTab('idea-studio')}
                            className="px-8 py-4 bg-white text-black font-bold text-lg rounded-xl hover:bg-zinc-200 transition-all shadow-xl shadow-indigo-500/10 flex items-center gap-3 transform group-hover:translate-x-1"
                        >
                            <span>Start Creating</span>
                            <ArrowRight size={20} />
                        </button>
                    </div>
                </div>

                {/* Quick Actions Column */}
                <div className="flex flex-col gap-4">
                    {/* Repurpose */}
                    <button
                        onClick={() => setActiveTab('repurposer')}
                        className="flex-1 bg-[#0A0A0A] border border-white/5 hover:border-white/20 p-6 rounded-[24px] text-left transition-all hover:-translate-y-1 group flex flex-col justify-center"
                    >
                        <div className="flex items-center gap-4 mb-2">
                            <div className="w-10 h-10 rounded-full bg-pink-500/10 flex items-center justify-center text-pink-400 group-hover:scale-110 transition-transform">
                                <Scissors size={20} />
                            </div>
                            <h3 className="font-bold text-white text-lg">Repurpose Video</h3>
                        </div>
                        <p className="text-sm text-zinc-500 pl-14">Long form → Viral shorts</p>
                    </button>

                    {/* Dubbing */}
                    <button
                        onClick={() => setActiveTab('dubber')}
                        className="flex-1 bg-[#0A0A0A] border border-white/5 hover:border-white/20 p-6 rounded-[24px] text-left transition-all hover:-translate-y-1 group flex flex-col justify-center"
                    >
                        <div className="flex items-center gap-4 mb-2">
                            <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-400 group-hover:scale-110 transition-transform">
                                <Globe size={20} />
                            </div>
                            <h3 className="font-bold text-white text-lg">AI Dubbing</h3>
                        </div>
                        <p className="text-sm text-zinc-500 pl-14">Translate to 30+ languages</p>
                    </button>

                    {/* Past Projects */}
                    <button
                        onClick={() => setActiveTab('gallery')}
                        className="flex-1 bg-[#0A0A0A] border border-white/5 hover:border-white/20 p-6 rounded-[24px] text-left transition-all hover:-translate-y-1 group flex flex-col justify-center"
                    >
                        <div className="flex items-center gap-4 mb-2">
                            <div className="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center text-zinc-400 group-hover:text-white transition-colors">
                                <LayoutDashboard size={20} />
                            </div>
                            <h3 className="font-bold text-white text-lg">View Projects</h3>
                        </div>
                        <p className="text-sm text-zinc-500 pl-14 opacity-60">Manage your gallery</p>
                    </button>
                </div>
            </div>

            {/* 3. RECENT PROJECTS SECTION */}
            <div>
                <div className="flex items-center justify-between mb-6 px-2">
                    <h2 className="text-xl font-bold text-white">Recent Projects</h2>
                    {recentProjects.length > 0 && (
                        <button onClick={() => setActiveTab('gallery')} className="text-sm text-zinc-400 hover:text-white transition-colors">
                            View all
                        </button>
                    )}
                </div>

                {recentProjects.length === 0 ? (
                    /* EMPTY STATE */
                    <div className="bg-gradient-to-b from-[#0F0F0F] to-[#0A0A0A] border border-dashed border-white/10 rounded-3xl p-12 text-center">
                        <div className="w-16 h-16 bg-white/5 rounded-2xl flex items-center justify-center mx-auto mb-6 text-zinc-500">
                            <Video size={32} />
                        </div>
                        <h3 className="text-xl font-bold text-white mb-2">You haven't created anything yet.</h3>
                        <p className="text-zinc-500 max-w-sm mx-auto mb-8">
                            Your first viral masterpiece is just 2 minutes away. No editing skills required.
                        </p>
                    </div>
                ) : (
                    /* FILLED STATE */
                    <div className="bg-[#0A0A0A] border border-white/5 rounded-[32px] p-2">
                        {recentProjects.map((project, i) => (
                            <div
                                key={project.id}
                                onClick={() => setSelectedProject(project)}
                                className="flex items-center gap-5 p-4 rounded-[24px] hover:bg-white/5 transition-colors cursor-pointer group"
                            >
                                {/* Thumbnail */}
                                <div className="w-32 h-20 rounded-xl bg-zinc-900 overflow-hidden relative border border-white/5 shrink-0">
                                    {project.thumbnail_url || project.video_url ? (
                                        <video src={project.thumbnail_url || project.video_url} className="w-full h-full object-cover opacity-60 group-hover:opacity-100 transition-opacity" />
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center text-zinc-700">
                                            <Video size={24} />
                                        </div>
                                    )}
                                    <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/40">
                                        <Play size={24} className="text-white drop-shadow-md" fill="currentColor" />
                                    </div>
                                </div>

                                {/* Info */}
                                <div className="flex-1 min-w-0 py-1">
                                    <h4 className="text-base font-bold text-white truncate mb-1.5">{project.topic || "Untitled Project"}</h4>
                                    <div className="flex items-center gap-3">
                                        <span className="flex items-center gap-1.5 text-xs font-semibold text-zinc-400 bg-white/5 px-2 py-1 rounded-md border border-white/5 uppercase tracking-wider">
                                            {project.platform === 'youtube' ? <Video size={10} /> : <Zap size={10} />}
                                            {project.platform}
                                        </span>
                                        <span className="text-xs text-zinc-600">{new Date(project.created_at).toLocaleDateString()}</span>
                                    </div>
                                </div>

                                <div className="hidden sm:block pr-4">
                                    <div className="p-2 rounded-full border border-white/10 text-zinc-500 opacity-0 group-hover:opacity-100 transition-all group-hover:translate-x-1">
                                        <ArrowRight size={16} />
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

        </div>
    );
}
