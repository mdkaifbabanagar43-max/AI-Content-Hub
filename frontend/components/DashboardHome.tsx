import { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePlan } from '@/context/PlanContext';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Video, Zap, Scissors, Mic, Globe, ArrowRight,
    Play, X, Download, Plus, Film, TrendingUp, Clock
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { API_BASE_URL } from '@/lib/config';
import { forceDownload } from '@/lib/download';

interface DashboardHomeProps { setActiveTab: (tab: string) => void; }

function timeAgo(d: string) {
    const s = Math.floor((Date.now() - new Date(d).getTime()) / 1000);
    if (s < 60) return 'just now';
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
    return `${Math.floor(s / 86400)}d ago`;
}

const stagger = (i: number) => ({ initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0, transition: { delay: 0.05 + i * 0.04, duration: 0.3, ease: [0.16, 1, 0.3, 1] as any } } });

export default function DashboardHome({ setActiveTab }: DashboardHomeProps) {
    const { user } = useAuth();
    const { credits, userPlan } = usePlan();
    const [projectCount, setProjectCount] = useState(0);
    const [recentProjects, setRecentProjects] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedProject, setSelectedProject] = useState<any>(null);

    const planLimit = userPlan === 'starter' ? 500 : (userPlan === 'creator' || userPlan === 'pro') ? 2000 : userPlan === 'agency' ? 10000 : 500;

    useEffect(() => {
        if (!user) { setIsLoading(false); return; }
        let alive = true;
        (async () => {
            try {
                const token = await user.getIdToken();
                const res = await fetch(`${API_BASE_URL}/my-projects`, { headers: { 'Authorization': `Bearer ${token}` } });
                if (res.ok && alive) {
                    const data = await res.json();
                    if (data.projects) { setProjectCount(data.projects.length); setRecentProjects(data.projects.slice(0, 6)); }
                }
            } catch { } finally { if (alive) setIsLoading(false); }
        })();
        return () => { alive = false; };
    }, [user]);

    const actions = [
        { id: 'idea-studio', name: 'Idea Studio',      desc: 'AI video from any topic',       icon: Video,    badge: 'Popular' },
        { id: 'repurposer',  name: 'Viral Repurposer', desc: 'Long video → viral clips',      icon: Scissors, badge: null },
        { id: 'dubber',      name: 'Global Dubber',    desc: 'Dub into 30+ languages',         icon: Globe,    badge: null },
        { id: 'voice-lab',   name: 'AI Voice Artist',  desc: 'Professional AI voiceovers',    icon: Mic,      badge: null },
    ];

    const stats = [
        { label: 'Projects',    value: projectCount, icon: Film,       suffix: '' },
        { label: 'Hours Saved', value: 42,           icon: Clock,      suffix: 'h' },
        { label: 'Est. Reach',  value: '1.2',        icon: TrendingUp, suffix: 'M' },
        { label: 'Credits',     value: credits.toLocaleString(), icon: Zap, suffix: '' },
    ];

    if (isLoading) return (
        <div className="space-y-8 pb-8">
            <div className="h-7 w-56 rounded-2xl animate-shimmer" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[...Array(4)].map((_, i) => <div key={i} className="h-24 rounded-2xl animate-shimmer" />)}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[...Array(4)].map((_, i) => <div key={i} className="h-40 rounded-2xl animate-shimmer" />)}
            </div>
        </div>
    );

    return (
        <div className="space-y-8 pb-12">
            {/* Video preview modal */}
            <AnimatePresence>
                {selectedProject && (
                    <motion.div
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-black/80 backdrop-blur-2xl"
                        onClick={() => setSelectedProject(null)}
                    >
                        <motion.div
                            initial={{ scale: 0.94, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.94, opacity: 0 }}
                            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                            className="w-full max-w-3xl rounded-3xl overflow-hidden shadow-[0_40px_80px_rgba(0,0,0,0.8)] border border-white/[0.08] bg-[#111113]"
                            onClick={e => e.stopPropagation()}
                        >
                            <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
                                <div>
                                    <h2 className="text-sm font-semibold text-white">{selectedProject.topic || 'Untitled'}</h2>
                                    <p className="text-[11px] text-white/35 mt-0.5">{new Date(selectedProject.created_at).toLocaleDateString()}</p>
                                </div>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => forceDownload(selectedProject.video_url, `project-${selectedProject.id}.mp4`)}
                                        className="flex items-center gap-1.5 px-3 py-1.5 bg-white text-black font-semibold text-xs rounded-xl hover:bg-zinc-100 transition-colors"
                                    >
                                        <Download size={11} /> Download
                                    </button>
                                    <button onClick={() => setSelectedProject(null)} className="p-2 text-white/40 hover:text-white rounded-xl hover:bg-white/[0.06] transition-colors">
                                        <X size={15} />
                                    </button>
                                </div>
                            </div>
                            <div className="bg-black aspect-video">
                                {selectedProject.video_url
                                    ? <video src={selectedProject.video_url} controls autoPlay className="w-full h-full object-contain" />
                                    : <div className="flex items-center justify-center h-full text-white/20"><Film size={40} /></div>
                                }
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pt-1">
                <div>
                    <motion.p {...stagger(0)} className="label-mono mb-2">
                        {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
                    </motion.p>
                    <motion.h1
                        initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
                        className="text-3xl font-semibold text-white tracking-tight"
                    >
                        {user?.displayName?.split(' ')[0] ? `Good morning, ${user.displayName.split(' ')[0]}` : 'Your Workspace'}
                    </motion.h1>
                    <motion.p {...stagger(1)} className="text-sm text-white/40 mt-1 font-normal">
                        {projectCount > 0 ? `${projectCount} project${projectCount > 1 ? 's' : ''} created · Ready to create more?` : 'Start by creating your first AI video'}
                    </motion.p>
                </div>

                <motion.button
                    initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.1 }}
                    whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                    onClick={() => setActiveTab('idea-studio')}
                    className="flex items-center gap-2 px-5 h-10 bg-white text-black font-semibold text-sm rounded-2xl transition-colors hover:bg-zinc-100 shrink-0 shadow-[0_4px_20px_rgba(255,255,255,0.12)]"
                >
                    <Plus size={15} strokeWidth={2.5} />
                    New Video
                </motion.button>
            </div>

            {/* Stats — Bento row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {stats.map((s, i) => {
                    const Icon = s.icon;
                    return (
                        <motion.div key={s.label} {...stagger(i)} className="bento-card p-5">
                            <div className="flex items-center justify-between mb-4">
                                <p className="label-mono">{s.label}</p>
                                <div className="w-7 h-7 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
                                    <Icon size={13} className="text-white/40" />
                                </div>
                            </div>
                            <p className="text-2xl font-semibold text-white tracking-tight">
                                {s.value}<span className="text-white/30 text-base font-normal ml-0.5">{s.suffix}</span>
                            </p>
                        </motion.div>
                    );
                })}
            </div>

            {/* Quick Actions — Bento grid */}
            <div>
                <p className="label-mono mb-3">Quick Actions</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    {actions.map((a, i) => {
                        const Icon = a.icon;
                        return (
                            <motion.button
                                key={a.id}
                                {...stagger(i + 4)}
                                whileHover={{ y: -2, scale: 1.01 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={() => setActiveTab(a.id)}
                                className="bento-card group p-5 text-left"
                            >
                                <div className="flex items-start justify-between mb-4">
                                    <div className="w-10 h-10 rounded-2xl bg-white/[0.04] border border-white/[0.07] flex items-center justify-center text-white/50 group-hover:text-white/90 group-hover:bg-white/[0.08] transition-all">
                                        <Icon size={18} />
                                    </div>
                                    {a.badge && (
                                        <span className="text-[9px] font-semibold px-2 py-0.5 rounded-full bg-indigo-500/15 border border-indigo-500/25 text-indigo-400 uppercase tracking-wider">
                                            {a.badge}
                                        </span>
                                    )}
                                </div>
                                <h3 className="text-[13px] font-semibold text-white/90 group-hover:text-white mb-1 transition-colors">{a.name}</h3>
                                <p className="text-[11px] text-white/35 leading-relaxed">{a.desc}</p>
                                <div className="mt-4 flex items-center gap-1 text-[11px] font-medium text-white/30 group-hover:text-indigo-400 transition-colors">
                                    <span>Launch</span>
                                    <ArrowRight size={10} className="group-hover:translate-x-0.5 transition-transform" />
                                </div>
                            </motion.button>
                        );
                    })}
                </div>
            </div>

            {/* Recent Projects */}
            <div>
                <div className="flex items-center justify-between mb-3">
                    <p className="label-mono">Recent Projects</p>
                    {recentProjects.length > 0 && (
                        <button onClick={() => setActiveTab('gallery')} className="text-[11px] text-white/35 hover:text-white/70 transition-colors">
                            View all →
                        </button>
                    )}
                </div>

                {recentProjects.length > 0 ? (
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                        {recentProjects.map((proj, i) => (
                            <motion.div key={proj.id} {...stagger(i + 8)} onClick={() => setSelectedProject(proj)} className="group cursor-pointer">
                                <div className="relative aspect-[9/16] rounded-2xl overflow-hidden bg-white/[0.03] border border-white/[0.07] group-hover:border-white/[0.15] transition-all duration-200 shadow-[0_4px_24px_rgba(0,0,0,0.4)]">
                                    {proj.video_url ? (
                                        <video src={proj.video_url} className="w-full h-full object-cover opacity-60 group-hover:opacity-90 transition-opacity duration-300" preload="metadata" muted />
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center text-white/15"><Film size={20} /></div>
                                    )}
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex flex-col items-center justify-center gap-2">
                                        <div className="w-9 h-9 rounded-full glass-strong border border-white/20 flex items-center justify-center">
                                            <Play size={13} className="translate-x-0.5 fill-white text-white" />
                                        </div>
                                    </div>
                                    {proj.platform && (
                                        <div className="absolute top-2 left-2">
                                            <span className="text-[8px] font-semibold px-1.5 py-0.5 rounded-lg bg-black/70 border border-white/[0.08] text-white/60 uppercase tracking-wider backdrop-blur-sm">
                                                {proj.platform}
                                            </span>
                                        </div>
                                    )}
                                </div>
                                <div className="mt-2 px-0.5">
                                    <p className="text-[11px] font-medium text-white/50 group-hover:text-white/80 truncate transition-colors">{proj.topic || 'Untitled'}</p>
                                    <p className="text-[10px] text-white/25 mt-0.5">{timeAgo(proj.created_at)}</p>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                ) : (
                    <div className="bento-card border-dashed p-12 text-center">
                        <div className="w-12 h-12 rounded-2xl bg-white/[0.03] border border-white/[0.07] flex items-center justify-center text-white/20 mx-auto mb-4">
                            <Video size={20} />
                        </div>
                        <p className="text-sm font-medium text-white/40 mb-1">No projects yet</p>
                        <p className="text-xs text-white/20 mb-5">Your AI-generated videos will appear here</p>
                        <button
                            onClick={() => setActiveTab('idea-studio')}
                            className="px-5 h-9 bg-white text-black font-semibold text-xs rounded-xl hover:bg-zinc-100 transition-colors"
                        >
                            Create First Video
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
