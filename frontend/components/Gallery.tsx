'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { motion } from 'framer-motion';
import { Play, Download, Clock, Film, Youtube, Smartphone, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { API_BASE_URL } from '@/lib/config';

// --- TYPES ---
interface Project {
    id: string;
    topic: string;
    video_url: string;
    thumbnail_url: string;
    platform: 'tiktok' | 'youtube';
    mood: string;
    created_at: string;
}

// --- HELPER: TIME AGO ---
function timeAgo(dateString: string) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + " years ago";
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + " months ago";
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + " days ago";
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + " hours ago";
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + " mins ago";
    return Math.floor(seconds) + " seconds ago";
}

export default function Gallery() {
    const { user } = useAuth();
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchProjects = async () => {
        if (!user) return;
        try {
            const res = await fetch(`${API_BASE_URL}/my-projects/${user.uid}`);
            const data = await res.json();
            if (data.projects) {
                setProjects(data.projects);
            }
        } catch (error) {
            console.error("Failed to fetch gallery:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (user) {
            fetchProjects();
        } else {
            setLoading(false);
        }
    }, [user]);

    if (!user) {
        return (
            <div className="flex flex-col items-center justify-center p-12 text-zinc-500">
                <p>Please sign in to view your gallery.</p>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center p-20 text-purple-500">
                <Loader2 className="animate-spin w-10 h-10" />
            </div>
        );
    }

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <h2 className="text-3xl font-bold bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">
                    Your Masterpieces
                </h2>
                <div className="text-zinc-500 text-sm font-mono">
                    {projects.length} PROJECTS
                </div>
            </div>

            {projects.length === 0 ? (
                <div className="text-center py-20 bg-zinc-900/30 rounded-3xl border border-zinc-800 border-dashed">
                    <Film className="w-16 h-16 text-zinc-700 mx-auto mb-4" />
                    <p className="text-zinc-400 text-lg">Your canvas is empty.</p>
                    <p className="text-zinc-600 text-sm">Head to the Studio to create something viral.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {projects.map((project, index) => (
                        <motion.div
                            key={project.id}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.1 }}
                            className="group relative bg-zinc-900 rounded-2xl overflow-hidden border border-zinc-800 hover:border-purple-500/50 transition-all hover:shadow-2xl hover:shadow-purple-900/20"
                        >
                            {/* THUMBNAIL AREA */}
                            <div className="aspect-video bg-black relative overflow-hidden">
                                <video
                                    src={project.video_url}
                                    className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
                                />

                                {/* OVERLAY PLAY BUTTON */}
                                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/40 backdrop-blur-[2px]">
                                    <a
                                        href={project.video_url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="w-16 h-16 bg-white/10 rounded-full flex items-center justify-center backdrop-blur-md border border-white/20 hover:scale-110 transition-transform text-white"
                                    >
                                        <Play fill="currentColor" size={24} />
                                    </a>
                                </div>

                                {/* BADGE */}
                                <div className="absolute top-4 right-4">
                                    {project.platform === 'tiktok' ? (
                                        <span className="bg-pink-500/90 text-white text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1 shadow-lg backdrop-blur-sm">
                                            <Smartphone size={12} /> TikTok
                                        </span>
                                    ) : (
                                        <span className="bg-red-600/90 text-white text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1 shadow-lg backdrop-blur-sm">
                                            <Youtube size={12} /> YouTube
                                        </span>
                                    )}
                                </div>
                            </div>

                            {/* INFO AREA */}
                            <div className="p-5 space-y-4">
                                <div>
                                    <h3 className="font-bold text-lg text-white truncate group-hover:text-purple-400 transition-colors">
                                        {project.topic || "Untitled Project"}
                                    </h3>
                                    <div className="flex items-center gap-2 text-xs text-zinc-500 mt-1 font-mono">
                                        <Clock size={12} />
                                        {timeAgo(project.created_at)}
                                        <span className="w-1 h-1 bg-zinc-700 rounded-full" />
                                        <span className={cn(
                                            "capitalize",
                                            project.mood === 'funny' ? "text-yellow-500" :
                                                project.mood === 'scary' ? "text-purple-500" :
                                                    "text-blue-500"
                                        )}>
                                            {project.mood} Mode
                                        </span>
                                    </div>
                                </div>

                                <div className="pt-4 border-t border-zinc-800 flex justify-end">
                                    <a
                                        href={project.video_url}
                                        download
                                        className="flex items-center gap-2 text-xs font-bold text-zinc-400 hover:text-white transition-colors bg-zinc-800 hover:bg-zinc-700 px-4 py-2 rounded-lg"
                                    >
                                        <Download size={14} />
                                        DOWNLOAD MP4
                                    </a>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>
            )}
        </div>
    );
}
