'use client';

import React from 'react';
import { Video, Scissors, Mic, Globe, LogOut, LogIn, Film, LayoutDashboard, Sparkles, ChevronLeft, ChevronRight, Minimize2, Maximize2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { usePlan } from '../context/PlanContext';
import { cn } from '@/lib/utils';
import Tooltip from './ui/Tooltip';

interface SidebarProps {
    activeTab: string;
    setActiveTab: (tab: string) => void;
    isOpen: boolean;
    onClose: () => void;
    isCollapsed: boolean;
    toggleSidebar: () => void;
    toggleFocusMode: () => void;
}

export default function Sidebar({ activeTab, setActiveTab, isOpen, onClose, isCollapsed, toggleSidebar, toggleFocusMode }: SidebarProps) {
    const { user, loginWithGoogle, logout } = useAuth();
    const { userPlan } = usePlan();

    const planDisplayNames: Record<string, string> = {
        'starter': 'Starter Plan',
        'pro': 'Pro Plan',
        'creator': 'Creator Pro',
        'agency': 'Agency Plan'
    };

    const menuItems = [
        { id: 'dashboard', name: 'Mission Control', icon: LayoutDashboard },
        { id: 'idea-studio', name: 'Idea Studio', icon: Video },
        { id: 'repurposer', name: 'Viral Repurposer', icon: Scissors },
        { id: 'dubber', name: 'Global Dubber', icon: Globe },
        { id: 'gallery', name: 'My Masterpieces', icon: Film },
    ];

    return (
        <>
            {/* Mobile Backdrop */}
            {isOpen && (
                <div
                    onClick={onClose}
                    className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden animate-in fade-in duration-200"
                />
            )}

            {/* Sidebar */}
            <aside
                className={cn(
                    "bg-[#050505] border-r border-white/5 flex flex-col h-screen fixed left-0 top-0 z-50 transition-all duration-300 ease-in-out shadow-2xl md:shadow-none",
                    isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
                    isCollapsed ? "w-[80px]" : "w-[260px]"
                )}
            >
                {/* 1. Header & Logo */}
                <div className={cn("h-16 flex items-center border-b border-white/5 transition-all duration-300", isCollapsed ? "justify-center px-0" : "justify-between px-6")}>
                    <div className="flex items-center gap-3 overflow-hidden">
                        <div className="w-8 h-8 min-w-[32px] rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white font-bold shadow-lg shadow-blue-500/20">
                            AI
                        </div>
                        <span className={cn("text-lg font-bold text-white tracking-tight whitespace-nowrap transition-opacity duration-200", isCollapsed ? "opacity-0 w-0 hidden" : "opacity-100")}>
                            Antigravity<span className="text-zinc-600">.OS</span>
                        </span>
                    </div>
                </div>

                {/* 2. Navigation */}
                <nav className="flex-1 px-3 py-6 space-y-1 overflow-y-auto custom-scrollbar overflow-x-hidden">
                    {!isCollapsed && (
                        <p className="px-3 text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-3 animate-in fade-in duration-300">Apps</p>
                    )}
                    {isCollapsed && <div className="h-4" />}

                    {menuItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = activeTab === item.id;

                        const ButtonContent = (
                            <button
                                onClick={() => {
                                    setActiveTab(item.id);
                                    if (window.innerWidth < 768) onClose(); // Close on mobile click
                                }}
                                className={cn(
                                    "w-full flex items-center rounded-lg font-medium transition-all duration-200 group relative cursor-pointer",
                                    isCollapsed ? "justify-center p-3" : "gap-3 px-3 py-2.5 text-[14px]",
                                    isActive
                                        ? "bg-white/5 text-white"
                                        : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.02]"
                                )}
                            >
                                {isActive && (
                                    <div className={cn("absolute bg-blue-500 rounded-r-full", isCollapsed ? "left-0 top-1/2 -translate-y-1/2 w-1 h-3" : "left-0 top-1/2 -translate-y-1/2 w-1 h-6")} />
                                )}

                                <Icon
                                    size={isCollapsed ? 22 : 18}
                                    className={cn(
                                        "transition-colors",
                                        isActive ? "text-blue-500" : "text-zinc-500 group-hover:text-zinc-300"
                                    )}
                                />
                                {!isCollapsed && <span className="whitespace-nowrap">{item.name}</span>}
                            </button>
                        );

                        return isCollapsed ? (
                            <Tooltip key={item.id} content={item.name} side="right">
                                {ButtonContent}
                            </Tooltip>
                        ) : (
                            <React.Fragment key={item.id}>
                                {ButtonContent}
                            </React.Fragment>
                        );
                    })}
                </nav>

                {/* Toggle & Focus Actions */}
                <div className="px-3 py-2 border-t border-white/5 flex flex-col gap-1">
                    {/* Focus Mode */}
                    <button
                        onClick={toggleFocusMode}
                        className={cn(
                            "w-full flex items-center rounded-lg text-zinc-500 hover:text-white hover:bg-white/5 transition-all duration-200 cursor-pointer",
                            isCollapsed ? "justify-center p-3" : "gap-3 px-3 py-2 text-xs"
                        )}
                        title="Enter Focus Mode"
                    >
                        <Maximize2 size={16} />
                        {!isCollapsed && <span>Focus Mode</span>}
                    </button>

                    {/* Collapse Toggle */}
                    <button
                        onClick={toggleSidebar}
                        className={cn(
                            "w-full flex items-center rounded-lg text-zinc-500 hover:text-white hover:bg-white/5 transition-all duration-200 cursor-pointer hidden md:flex",
                            isCollapsed ? "justify-center p-3" : "gap-3 px-3 py-2 text-xs"
                        )}
                    >
                        {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
                        {!isCollapsed && <span>Collapse Sidebar</span>}
                    </button>
                </div>

                {/* 3. User Profile Footer */}
                <div className="p-4 border-t border-white/5 bg-[#0A0A0A]">
                    {user ? (
                        <div className={cn("flex items-center group transition-colors", isCollapsed ? "justify-center flex-col gap-4" : "justify-between p-2 rounded-xl hover:bg-white/5")}>
                            {/* User Avatar */}
                            <div className={cn("flex items-center overflow-hidden transition-all", isCollapsed ? "justify-center" : "gap-3")}>
                                {user.photoURL ? (
                                    <img src={user.photoURL} alt="User" className="w-9 h-9 min-w-[36px] rounded-full border border-white/10" />
                                ) : (
                                    <div className="w-9 h-9 min-w-[36px] rounded-full bg-gradient-to-br from-zinc-700 to-zinc-600 flex items-center justify-center text-white font-bold text-xs">
                                        {user.email?.[0].toUpperCase() || 'U'}
                                    </div>
                                )}

                                {!isCollapsed && (
                                    <div className="flex flex-col min-w-0">
                                        <span className="text-[14px] font-bold text-white truncate max-w-[100px]">{user.displayName || 'Creator'}</span>
                                        <span className="text-[10px] text-zinc-500 font-medium uppercase">{planDisplayNames[userPlan] || 'Starter'}</span>
                                    </div>
                                )}
                            </div>

                            {/* Actions */}
                            <div className={cn("flex items-center", isCollapsed ? "flex-col gap-2 w-full border-t border-white/5 pt-3" : "gap-1")}>
                                {isCollapsed ? (
                                    <>
                                        <Tooltip content="Upgrade Plan">
                                            <button onClick={() => setActiveTab('pricing')} className="p-2 bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 rounded-lg transition-colors">
                                                <Sparkles size={16} />
                                            </button>
                                        </Tooltip>
                                        <Tooltip content="Sign Out">
                                            <button onClick={logout} className="p-2 text-zinc-500 hover:text-red-400 transition-colors">
                                                <LogOut size={16} />
                                            </button>
                                        </Tooltip>
                                    </>
                                ) : (
                                    <>
                                        <button
                                            onClick={() => setActiveTab('pricing')}
                                            className="p-1.5 bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 rounded-lg transition-colors group/upgrade" title="Upgrade Plan"
                                        >
                                            <Sparkles size={14} />
                                        </button>
                                        <button onClick={logout} className="p-1.5 text-zinc-500 hover:text-red-400 transition-colors cursor-pointer" title="Sign Out">
                                            <LogOut size={16} />
                                        </button>
                                    </>
                                )}
                            </div>
                        </div>
                    ) : (
                        <button
                            onClick={loginWithGoogle}
                            className={cn(
                                "w-full bg-white text-black rounded-xl font-bold hover:bg-zinc-200 transition-colors flex items-center justify-center cursor-pointer",
                                isCollapsed ? "p-3" : "py-3 gap-2 text-[15px]"
                            )}
                            title={isCollapsed ? "Sign In" : ""}
                        >
                            <LogIn size={18} />
                            {!isCollapsed && "Sign In"}
                        </button>
                    )}
                </div>
            </aside>
        </>
    );
}
