'use client';

import React, { useState, useEffect } from 'react';
import {
    Video, Scissors, Mic, Globe, LogOut, LogIn,
    Film, LayoutDashboard, Zap, PanelLeft, Clock,
    Play, ChevronDown, Plus, Maximize2, Crown, Coins
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { usePlan } from '../context/PlanContext';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { API_BASE_URL } from '@/lib/config';

interface SidebarProps {
    activeTab: string;
    setActiveTab: (tab: string) => void;
    isOpen: boolean;
    onClose: () => void;
    isCollapsed: boolean;
    toggleSidebar: () => void;
    toggleFocusMode: () => void;
}

interface RecentProject {
    id: string; topic: string; video_url: string; created_at: string;
}

export default function Sidebar({
    activeTab, setActiveTab, isOpen, onClose,
    isCollapsed, toggleSidebar, toggleFocusMode
}: SidebarProps) {
    const { user, loginWithGoogle, logout } = useAuth();
    const { userPlan, credits } = usePlan();
    const [recentProjects, setRecentProjects] = useState<RecentProject[]>([]);
    const [showProfileMenu, setShowProfileMenu] = useState(false);

    useEffect(() => {
        if (!user) return;
        (async () => {
            try {
                const token = await user.getIdToken();
                const res = await fetch(`${API_BASE_URL}/my-projects`, { headers: { 'Authorization': `Bearer ${token}` } });
                const data = await res.json();
                if (data.projects) setRecentProjects(data.projects.slice(0, 4));
            } catch { /* silent */ }
        })();
    }, [user]);

    const planLimit = userPlan === 'starter' ? 500 : (userPlan === 'creator' || userPlan === 'pro') ? 2000 : userPlan === 'agency' ? 10000 : 500;
    const creditsRemaining = Math.min(credits, planLimit);
    const usagePct = Math.min(100, Math.max(0, ((planLimit - creditsRemaining) / planLimit) * 100));

    const planLabels: Record<string, string> = { starter: 'Starter', pro: 'Pro', creator: 'Creator', agency: 'Agency' };

    const navItems = [
        { id: 'dashboard',   label: 'Dashboard',        icon: LayoutDashboard, shortcut: '⌘1' },
        { id: 'idea-studio', label: 'Idea Studio',       icon: Video,           shortcut: '⌘2', badge: 'AI' },
        { id: 'video-cloner',label: 'Video Cloner',      icon: Zap,             shortcut: '⌘3', badge: 'PRO' },
        { id: 'repurposer',  label: 'Viral Repurposer',  icon: Scissors,        shortcut: '⌘4' },
        { id: 'dubber',      label: 'Global Dubber',     icon: Globe,           shortcut: '⌘5' },
        { id: 'voice-lab',   label: 'AI Voice Artist',   icon: Mic,             shortcut: '⌘6' },
    ];

    const navItem = (item: typeof navItems[0]) => {
        const isActive = activeTab === item.id;
        return (
            <motion.button
                key={item.id}
                whileTap={{ scale: 0.97 }}
                onClick={() => { setActiveTab(item.id); if (typeof window !== 'undefined' && window.innerWidth < 768) onClose(); }}
                className={cn(
                    'relative w-full flex items-center rounded-xl transition-all duration-150 select-none group',
                    isCollapsed ? 'justify-center h-10 w-10 mx-auto' : 'gap-3 h-9 px-3',
                    isActive
                        ? 'bg-white/[0.09] text-white'
                        : 'text-white/40 hover:text-white/80 hover:bg-white/[0.05]'
                )}
            >
                {/* Active indicator */}
                {isActive && (
                    <motion.div
                        layoutId="nav-pill"
                        className="absolute inset-0 rounded-xl bg-white/[0.08] border border-white/[0.10]"
                        transition={{ type: 'spring', bounce: 0.2, duration: 0.3 }}
                    />
                )}

                <item.icon
                    size={15}
                    className={cn('relative z-10 shrink-0 transition-colors', isActive ? 'text-white' : '')}
                />

                {!isCollapsed && (
                    <span className="relative z-10 flex-1 flex items-center justify-between">
                        <span className={cn('text-[13px] tracking-tight', isActive ? 'font-medium text-white' : 'font-normal')}>{item.label}</span>
                        <span className="flex items-center gap-1.5">
                            {item.badge && (
                                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-md bg-indigo-500/15 border border-indigo-500/25 text-indigo-400 uppercase tracking-wider">
                                    {item.badge}
                                </span>
                            )}
                            {item.shortcut && (
                                <span className="text-[10px] text-white/20 group-hover:text-white/35 transition-colors font-mono">{item.shortcut}</span>
                            )}
                        </span>
                    </span>
                )}
            </motion.button>
        );
    };

    return (
        <>
            {/* Mobile backdrop */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden"
                    />
                )}
            </AnimatePresence>

            {/* Sidebar shell — macOS style: transparent with right border */}
            <aside className={cn(
                'fixed left-0 top-0 h-screen z-50 flex flex-col transition-all duration-300 ease-out',
                'bg-black/90 backdrop-blur-3xl border-r border-white/[0.07]',
                isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
                isCollapsed ? 'w-[68px]' : 'w-[240px]'
            )}>

                {/* Logo + collapse toggle */}
                <div className={cn(
                    'flex border-b border-white/[0.05] shrink-0',
                    isCollapsed ? 'flex-col items-center justify-center py-3 gap-3 h-auto' : 'h-11 items-center justify-between px-4'
                )}>
                    <button
                        onClick={() => setActiveTab('dashboard')}
                        className="flex items-center gap-2"
                    >
                        <div className="w-6 h-6 rounded-lg bg-indigo-600 flex items-center justify-center text-white text-[9px] font-bold tracking-tight shrink-0 shadow-[0_0_12px_rgba(99,102,241,0.4)]">
                            SC
                        </div>
                        {!isCollapsed && (
                            <span className="font-semibold text-[13px] text-white tracking-tight">
                                ShortCut<span className="text-indigo-400">AI</span>
                            </span>
                        )}
                    </button>

                    <button
                        onClick={toggleSidebar}
                        className={cn(
                            "p-1.5 text-white/25 hover:text-white/70 rounded-lg hover:bg-white/[0.05] transition-all",
                            isCollapsed && "mx-auto"
                        )}
                        title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
                    >
                        <PanelLeft size={isCollapsed ? 16 : 13} className={cn(isCollapsed && "text-white/50")} />
                    </button>
                </div>

                {/* New creation CTA */}
                <div className={cn('px-3 pt-3 pb-2 shrink-0', isCollapsed && 'flex justify-center')}>
                    <motion.button
                        whileTap={{ scale: 0.97 }}
                        whileHover={{ backgroundColor: 'rgba(99,102,241,0.85)' }}
                        onClick={() => setActiveTab('idea-studio')}
                        className={cn(
                            'bg-indigo-600 text-white text-xs font-semibold rounded-xl transition-all flex items-center justify-center gap-1.5 shadow-[0_4px_16px_rgba(99,102,241,0.25)]',
                            isCollapsed ? 'w-10 h-10' : 'w-full h-9 px-3'
                        )}
                    >
                        <Plus size={13} strokeWidth={2.5} />
                        {!isCollapsed && 'New Video'}
                    </motion.button>
                </div>

                {/* Navigation */}
                <nav className="flex-1 px-3 py-1 space-y-4 overflow-y-auto overflow-x-hidden custom-scrollbar">
                    <div className="space-y-0.5">
                        {!isCollapsed && (
                            <p className="px-3 pb-1.5 text-[10px] font-semibold text-white/25 uppercase tracking-[0.12em]">Studio</p>
                        )}
                        {navItems.map(item => navItem(item))}
                    </div>

                    <div className="space-y-0.5">
                        {!isCollapsed && (
                            <p className="px-3 pb-1.5 text-[10px] font-semibold text-white/25 uppercase tracking-[0.12em]">Library</p>
                        )}
                        <motion.button
                            whileTap={{ scale: 0.97 }}
                            onClick={() => setActiveTab('gallery')}
                            className={cn(
                                'relative w-full flex items-center rounded-xl transition-all duration-150 group',
                                isCollapsed ? 'justify-center h-10 w-10 mx-auto' : 'gap-3 h-9 px-3',
                                activeTab === 'gallery'
                                    ? 'bg-white/[0.09] text-white'
                                    : 'text-white/40 hover:text-white/80 hover:bg-white/[0.05]'
                            )}
                        >
                            {activeTab === 'gallery' && (
                                <motion.div layoutId="nav-pill" className="absolute inset-0 rounded-xl bg-white/[0.08] border border-white/[0.10]" transition={{ type: 'spring', bounce: 0.2, duration: 0.3 }} />
                            )}
                            <Film size={15} className={cn('relative z-10 shrink-0', activeTab === 'gallery' ? 'text-white' : '')} />
                            {!isCollapsed && (
                                <span className={cn('relative z-10 text-[13px] tracking-tight', activeTab === 'gallery' ? 'font-medium text-white' : '')}>
                                    My Projects
                                </span>
                            )}
                        </motion.button>
                    </div>

                    {/* Recent projects */}
                    {user && !isCollapsed && recentProjects.length > 0 && (
                        <div className="border-t border-white/[0.04] pt-3">
                            <p className="px-3 pb-1.5 text-[10px] font-semibold text-white/25 uppercase tracking-[0.12em] flex items-center justify-between">
                                <span>Recent</span>
                                <Clock size={9} className="text-white/20" />
                            </p>
                            <div className="space-y-0.5">
                                {recentProjects.map(proj => (
                                    <button
                                        key={proj.id}
                                        onClick={() => setActiveTab('gallery')}
                                        className="w-full flex items-center gap-2.5 px-3 h-8 rounded-lg text-left text-white/30 hover:text-white/70 hover:bg-white/[0.04] transition-all group"
                                    >
                                        <Play size={8} className="shrink-0 text-white/20 group-hover:text-indigo-400 transition-colors" />
                                        <span className="truncate text-[12px]">{proj.topic || 'Untitled'}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </nav>

                {/* Credits widget */}
                {user && !isCollapsed && (
                    <div className="mx-3 mb-2 p-3.5 rounded-2xl glass border border-white/[0.07]">
                        <div className="flex items-center justify-between mb-2.5">
                            <span className="text-[11px] font-medium text-white/50 flex items-center gap-1.5">
                                <Zap size={10} className="text-indigo-400" />
                                Credits
                            </span>
                            <span className="text-[11px] font-mono text-white/70">
                                {credits.toLocaleString()}<span className="text-white/25">/{planLimit.toLocaleString()}</span>
                            </span>
                        </div>
                        <div className="h-[2px] w-full bg-white/[0.06] rounded-full overflow-hidden mb-2.5">
                            <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${100 - usagePct}%` }}
                                transition={{ duration: 0.8, ease: 'easeOut' }}
                                className="h-full bg-gradient-to-r from-indigo-500 to-indigo-400 rounded-full"
                            />
                        </div>
                        <button
                            onClick={() => setActiveTab('pricing')}
                            className="text-[11px] font-medium text-indigo-400/80 hover:text-indigo-300 transition-colors"
                        >
                            + Top Up Credits
                        </button>
                    </div>
                )}

                {/* Profile footer */}
                <div className="p-2 border-t border-white/[0.05] shrink-0">
                    {user ? (
                        <div className="relative">
                            <button
                                onClick={() => setShowProfileMenu(v => !v)}
                                className={cn(
                                    'w-full flex items-center p-2 rounded-xl hover:bg-white/[0.05] transition-all group',
                                    isCollapsed && 'justify-center'
                                )}
                            >
                                <div className="relative shrink-0">
                                    {user.photoURL
                                        ? <img src={user.photoURL} alt="" className="w-7 h-7 rounded-full object-cover" />
                                        : <div className="w-7 h-7 rounded-full bg-indigo-600/20 border border-indigo-500/20 flex items-center justify-center text-indigo-300 font-bold text-xs">
                                            {user.email?.[0].toUpperCase() || 'U'}
                                          </div>
                                    }
                                    <span className="absolute bottom-0 right-0 w-1.5 h-1.5 bg-green-500 rounded-full border border-black" />
                                </div>
                                {!isCollapsed && (
                                    <>
                                        <div className="flex flex-col text-left min-w-0 ml-2.5 flex-1">
                                            <span className="text-[12px] font-medium text-white/80 truncate leading-tight">
                                                {user.displayName?.split(' ')[0] || 'Creator'}
                                            </span>
                                            <span className="text-[10px] text-white/30">
                                                {planLabels[userPlan] || 'Starter'}
                                            </span>
                                        </div>
                                        <ChevronDown size={11} className={cn('text-white/30 transition-transform', showProfileMenu && 'rotate-180')} />
                                    </>
                                )}
                            </button>

                            <AnimatePresence>
                                {showProfileMenu && (
                                    <motion.div
                                        initial={{ opacity: 0, y: 6, scale: 0.96 }}
                                        animate={{ opacity: 1, y: 0, scale: 1 }}
                                        exit={{ opacity: 0, y: 6, scale: 0.96 }}
                                        transition={{ duration: 0.15, ease: 'easeOut' }}
                                        className={cn(
                                            'fixed bottom-14 z-[999] w-56 p-1.5 rounded-2xl space-y-0.5',
                                            'bg-[#111113] border border-white/[0.10] shadow-[0_20px_60px_rgba(0,0,0,0.7)]',
                                            isCollapsed ? 'left-16' : 'left-3'
                                        )}
                                    >
                                        <div className="px-3 py-2.5 border-b border-white/[0.06] mb-1">
                                            <p className="text-xs font-semibold text-white truncate">{user.displayName || 'Creator'}</p>
                                            <p className="text-[10px] text-white/30 truncate mt-0.5">{user.email}</p>
                                        </div>

                                        {[
                                            { label: 'Credits & Plan', icon: Coins, onClick: () => { setActiveTab('pricing'); setShowProfileMenu(false); }, accent: 'text-indigo-400' },
                                            { label: 'Zen Focus Mode', icon: Maximize2, onClick: () => { toggleFocusMode(); setShowProfileMenu(false); }, accent: 'text-white/50' },
                                        ].map(item => (
                                            <button
                                                key={item.label}
                                                onClick={item.onClick}
                                                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-[12px] font-medium text-white/60 hover:bg-white/[0.05] hover:text-white/90 transition-all"
                                            >
                                                <item.icon size={13} className={item.accent} />
                                                {item.label}
                                            </button>
                                        ))}

                                        <div className="h-px bg-white/[0.05] my-1" />
                                        <button
                                            onClick={() => { logout(); setShowProfileMenu(false); }}
                                            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-[12px] font-medium text-red-400/80 hover:bg-red-500/[0.08] hover:text-red-400 transition-all"
                                        >
                                            <LogOut size={13} />
                                            Sign Out
                                        </button>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    ) : (
                        <motion.button
                            whileTap={{ scale: 0.97 }}
                            onClick={loginWithGoogle}
                            className={cn(
                                'w-full bg-white text-black rounded-xl font-semibold text-xs transition-all flex items-center justify-center gap-2 hover:bg-zinc-100',
                                isCollapsed ? 'h-10 w-10' : 'h-9 px-3'
                            )}
                        >
                            <LogIn size={13} />
                            {!isCollapsed && 'Sign In'}
                        </motion.button>
                    )}
                </div>
            </aside>
        </>
    );
}
