'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Download, Film, Loader2, Trash2, X, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import { API_BASE_URL } from '@/lib/config';
import { toast } from 'sonner';

interface Project {
    id: string; topic: string; video_url: string;
    thumbnail_url: string; platform: string; mood: string; created_at: string;
}

function timeAgo(d: string) {
    const s = Math.floor((Date.now() - new Date(d).getTime()) / 1000);
    if (s < 60) return 'just now';
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
    return `${Math.floor(s / 86400)}d ago`;
}

export default function Gallery() {
    const { user } = useAuth();
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const [previewProject, setPreviewProject] = useState<Project | null>(null);
    const [search, setSearch] = useState('');

    const fetchProjects = async () => {
        if (!user) return;
        try {
            const token = await user.getIdToken();
            const res = await fetch(`${API_BASE_URL}/my-projects`, { headers: { 'Authorization': `Bearer ${token}` } });
            const data = await res.json();
            if (data.projects) setProjects(data.projects);
        } catch { console.error('Gallery fetch failed'); } finally { setLoading(false); }
    };

    useEffect(() => { if (user) fetchProjects(); else setLoading(false); }, [user]);

    const handleDelete = async (id: string) => {
        if (!user) return;
        setDeletingId(id);
        try {
            const token = await user.getIdToken();
            const res = await fetch(`${API_BASE_URL}/api/projects/${id}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
            if (res.ok) {
                setProjects(prev => prev.filter(p => p.id !== id));
                toast.success('Deleted');
                if (previewProject?.id === id) setPreviewProject(null);
            } else throw new Error();
        } catch { toast.error('Delete failed'); } finally { setDeletingId(null); }
    };

    const handleDownload = async (url: string, title: string) => {
        try {
            toast.info('Starting download…');
            const res = await fetch(url);
            const blob = await res.blob();
            const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: `${title.replace(/[^a-zA-Z0-9]/g, '_')}_${Date.now()}.mp4` });
            document.body.appendChild(a); a.click(); document.body.removeChild(a);
            toast.success('Download complete!');
        } catch { toast.error('Download failed'); }
    };

    const filtered = projects.filter(p => !search || p.topic?.toLowerCase().includes(search.toLowerCase()) || p.platform?.includes(search.toLowerCase()));

    if (!user) return (
        <div className="flex flex-col items-center justify-center py-32 text-white/20">
            <Film size={36} className="mb-4" />
            <p className="text-sm">Sign in to view your gallery</p>
        </div>
    );

    if (loading) return (
        <div className="space-y-6 pb-8">
            <div className="h-7 w-40 rounded-2xl animate-shimmer" />
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
                {Array.from({ length: 10 }).map((_, i) => <div key={i} className="aspect-[9/16] rounded-2xl animate-shimmer" />)}
            </div>
        </div>
    );

    return (
        <div className="space-y-6 pb-12">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-1">
                <div>
                    <h1 className="text-2xl font-semibold text-white tracking-tight">My Projects</h1>
                    <p className="label-mono mt-1">{projects.length} video{projects.length !== 1 ? 's' : ''} · all time</p>
                </div>

                {/* Search */}
                <div className="relative flex-1 sm:max-w-xs">
                    <Search size={12} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30" />
                    <input
                        type="text" value={search} onChange={e => setSearch(e.target.value)}
                        placeholder="Search projects…"
                        className="w-full h-9 bg-white/[0.04] border border-white/[0.08] rounded-xl pl-9 pr-3 text-[13px] text-white/80 placeholder:text-white/25 focus:outline-none focus:ring-2 focus:ring-white/[0.12] transition-all"
                    />
                </div>
            </div>

            {/* Grid */}
            {filtered.length === 0 ? (
                <div className="bento-card border-dashed py-24 text-center">
                    <Film size={28} className="mx-auto mb-4 text-white/15" />
                    <p className="text-sm font-medium text-white/35 mb-1">{search ? 'No results found' : 'Your canvas is empty'}</p>
                    <p className="text-xs text-white/20">{search ? 'Try a different search' : 'Head to Idea Studio to create your first video'}</p>
                </div>
            ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
                    {filtered.map((project, i) => (
                        <motion.div
                            key={project.id}
                            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.035, duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                            className="group cursor-pointer"
                        >
                            <div
                                className="relative aspect-[9/16] rounded-2xl overflow-hidden bg-white/[0.03] border border-white/[0.07] group-hover:border-white/[0.15] transition-all duration-200 shadow-[0_4px_24px_rgba(0,0,0,0.4)]"
                                onClick={() => setPreviewProject(project)}
                            >
                                <video src={project.video_url} className="w-full h-full object-cover opacity-55 group-hover:opacity-85 transition-opacity duration-300" preload="metadata" muted />

                                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/10 to-transparent" />
                                    <div className="absolute inset-0 flex items-center justify-center">
                                        <div className="w-11 h-11 rounded-full bg-white/10 backdrop-blur-sm border border-white/25 flex items-center justify-center shadow-[0_4px_24px_rgba(0,0,0,0.4)]">
                                            <Play size={15} className="fill-white text-white translate-x-0.5" />
                                        </div>
                                    </div>
                                    <div className="absolute bottom-0 left-0 right-0 p-2.5 flex items-center gap-1.5">
                                        <button
                                            onClick={e => { e.stopPropagation(); handleDownload(project.video_url, project.topic || 'video'); }}
                                            className="flex-1 flex items-center justify-center gap-1 h-7 bg-white text-black text-[10px] font-bold rounded-xl hover:bg-zinc-100 transition-colors"
                                        >
                                            <Download size={10} /> MP4
                                        </button>
                                        <button
                                            onClick={e => { e.stopPropagation(); handleDelete(project.id); }}
                                            disabled={deletingId === project.id}
                                            className="h-7 w-7 flex items-center justify-center bg-black/40 border border-white/[0.10] rounded-xl text-red-400 hover:bg-red-500/20 transition-colors disabled:opacity-50"
                                        >
                                            {deletingId === project.id ? <Loader2 size={10} className="animate-spin" /> : <Trash2 size={10} />}
                                        </button>
                                    </div>
                                </div>

                                {project.platform && (
                                    <div className="absolute top-2 left-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <span className="text-[8px] font-semibold px-1.5 py-0.5 rounded-lg bg-black/70 border border-white/[0.08] text-white/60 uppercase tracking-wider backdrop-blur-sm">
                                            {project.platform}
                                        </span>
                                    </div>
                                )}
                            </div>

                            <div className="mt-2 px-0.5">
                                <p className="text-[11px] font-medium text-white/45 group-hover:text-white/75 truncate transition-colors">{project.topic || 'Untitled'}</p>
                                <p className="text-[10px] text-white/20 mt-0.5">{timeAgo(project.created_at)}</p>
                            </div>
                        </motion.div>
                    ))}
                </div>
            )}

            {/* Preview Modal */}
            <AnimatePresence>
                {previewProject && (
                    <motion.div
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-2xl p-6"
                        onClick={() => setPreviewProject(null)}
                    >
                        <motion.div
                            initial={{ scale: 0.94, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.94, opacity: 0 }}
                            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                            className="relative w-full max-w-xs"
                            onClick={e => e.stopPropagation()}
                        >
                            <button onClick={() => setPreviewProject(null)} className="absolute -top-10 right-0 p-2 text-white/35 hover:text-white transition-colors">
                                <X size={18} />
                            </button>
                            <div className="aspect-[9/16] bg-black rounded-3xl overflow-hidden border border-white/[0.10] shadow-[0_40px_80px_rgba(0,0,0,0.8)]">
                                <video key={previewProject.video_url} controls autoPlay className="w-full h-full object-contain" src={previewProject.video_url} playsInline />
                            </div>
                            <div className="mt-3 flex items-center justify-between gap-3">
                                <div className="min-w-0">
                                    <p className="text-sm font-semibold text-white truncate">{previewProject.topic || 'Untitled'}</p>
                                    <p className="text-[10px] text-white/30 mt-0.5">{timeAgo(previewProject.created_at)}</p>
                                </div>
                                <div className="flex items-center gap-2 shrink-0">
                                    <button
                                        onClick={() => handleDownload(previewProject.video_url, previewProject.topic || 'video')}
                                        className="flex items-center gap-1.5 px-4 h-8 bg-white text-black font-semibold text-xs rounded-xl hover:bg-zinc-100 transition-colors"
                                    >
                                        <Download size={11} /> Download
                                    </button>
                                    <button
                                        onClick={() => handleDelete(previewProject.id)}
                                        className="h-8 w-8 flex items-center justify-center glass rounded-xl text-red-400 hover:bg-red-500/15 transition-colors"
                                    >
                                        <Trash2 size={13} />
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
