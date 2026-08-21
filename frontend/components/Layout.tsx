'use client';

import React, { useState, useEffect } from 'react';
import { Menu } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import IdeaStudio from './IdeaStudio';
import VideoCloner from './VideoCloner';
import ViralRepurposer from './ViralRepurposer';
import GlobalDubber from './GlobalDubber';
import Gallery from './Gallery';
import { useAuth } from '../context/AuthContext';
import Sidebar from './Sidebar';
import DashboardHome from './DashboardHome';
import Pricing from './landing/Pricing';
import VoiceLab from './VoiceLab';
import { cn } from '@/lib/utils';

const TAB_META: Record<string, { label: string; description: string }> = {
  dashboard:      { label: 'Dashboard',        description: 'Your AI content workspace' },
  'idea-studio':  { label: 'Idea Studio',      description: 'Generate viral videos from a topic' },
  'video-cloner': { label: 'Video Cloner',     description: 'Clone viral videos with persistent visual identity and Veo AI' },
  repurposer:     { label: 'Viral Repurposer', description: 'Long video to high-retention clips' },
  'voice-lab':    { label: 'AI Voice Artist',  description: 'Professional AI voiceovers' },
  dubber:         { label: 'Global Dubber',    description: 'Dub content into 30+ languages' },
  gallery:        { label: 'My Projects',      description: 'Browse and manage your content' },
  pricing:        { label: 'Plans & Billing',  description: 'Upgrade your plan' },
};

const pageVariants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.28, ease: [0.16, 1, 0.3, 1] as any } },
  exit:    { opacity: 0, y: -4, transition: { duration: 0.18 } },
};

export default function Layout({ children }: { children?: React.ReactNode }) {
  const [activeTab, setActiveTab] = useState('dashboard');
  const { user } = useAuth();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isFocusMode, setIsFocusMode] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('sidebar-collapsed');
    if (saved) setIsCollapsed(saved === 'true');
  }, []);

  const toggleSidebar = () => {
    const next = !isCollapsed;
    setIsCollapsed(next);
    localStorage.setItem('sidebar-collapsed', String(next));
  };

  const toggleFocusMode = () => setIsFocusMode(v => !v);

  useEffect(() => { setIsMobileMenuOpen(false); }, [activeTab]);

  const currentMeta = TAB_META[activeTab] || { label: activeTab, description: '' };

  const pages = [
    { id: 'dashboard',   component: <DashboardHome setActiveTab={setActiveTab} /> },
    { id: 'idea-studio', component: <IdeaStudio onNavigate={setActiveTab} /> },
    { id: 'video-cloner', component: <VideoCloner onNavigate={setActiveTab} /> },
    { id: 'repurposer',  component: <ViralRepurposer onNavigate={setActiveTab} /> },
    { id: 'voice-lab',   component: <VoiceLab onNavigate={setActiveTab} /> },
    { id: 'dubber',      component: <GlobalDubber onNavigate={setActiveTab} /> },
    { id: 'gallery',     component: <Gallery /> },
    { id: 'pricing',     component: <Pricing /> },
  ];

  return (
    <div className="flex min-h-screen bg-black text-white">

      {/* Mobile header */}
      <header className="fixed top-0 left-0 right-0 h-12 bg-black/90 border-b border-white/[0.07] z-40 flex items-center justify-between px-4 md:hidden backdrop-blur-2xl">
        <button
          onClick={() => setIsMobileMenuOpen(true)}
          className="w-8 h-8 rounded-xl bg-white/[0.06] border border-white/[0.08] flex items-center justify-center text-white/60 hover:text-white transition-colors"
        >
          <Menu size={15} />
        </button>
        <span className="text-sm font-semibold tracking-tight">Clone<span className="text-indigo-400">Frame</span></span>
        <div className="w-8 h-8 rounded-full border border-white/[0.09] overflow-hidden bg-white/[0.05]">
          {user?.photoURL
            ? <img src={user.photoURL} alt="" className="w-full h-full object-cover" />
            : <span className="flex items-center justify-center h-full text-white/40 text-xs">{user?.email?.[0]?.toUpperCase() || '?'}</span>
          }
        </div>
      </header>

      {/* Sidebar */}
      {!isFocusMode && (
        <Sidebar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          isOpen={isMobileMenuOpen}
          onClose={() => setIsMobileMenuOpen(false)}
          isCollapsed={isCollapsed}
          toggleSidebar={toggleSidebar}
          toggleFocusMode={toggleFocusMode}
        />
      )}

      {isFocusMode && (
        <motion.button
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          onClick={toggleFocusMode}
          className="fixed bottom-6 left-6 z-50 px-3 py-2 glass rounded-xl text-xs font-medium text-white/50 hover:text-white transition-colors"
        >
          ← Exit Focus
        </motion.button>
      )}

      {/* Main area */}
      <main className={cn(
        'flex-1 w-full pt-12 md:pt-0 min-h-screen transition-all duration-300 ease-out',
        isFocusMode ? 'pl-0' : isCollapsed ? 'md:pl-[68px]' : 'md:pl-[240px]'
      )}>
        <div className="fixed inset-0 bg-black -z-10 pointer-events-none" />

        {/* macOS-style thin title bar */}
        {activeTab !== 'idea-studio' && (
          <div className="hidden md:flex items-center justify-between h-11 px-8 border-b border-white/[0.06] bg-black/70 sticky top-0 z-30 backdrop-blur-2xl">
            <div className="flex items-center gap-2.5">
              <span className="text-[10px] font-semibold tracking-[0.10em] uppercase text-white/25">CloneFrame</span>
              <span className="text-white/15 text-xs">/</span>
              <span className="text-[13px] font-medium text-white/70 tracking-tight">{currentMeta.label}</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-[11px] text-white/25 hidden lg:block tracking-wide">{currentMeta.description}</span>
              {user && (
                <div className="w-6 h-6 rounded-full border border-white/[0.12] overflow-hidden bg-white/[0.05]">
                  {user.photoURL
                    ? <img src={user.photoURL} alt="" className="w-full h-full object-cover" />
                    : <span className="flex items-center justify-center h-full text-white/40 text-[9px]">{user.email?.[0]?.toUpperCase()}</span>
                  }
                </div>
              )}
            </div>
          </div>
        )}

        <div className="p-5 md:p-8 w-full max-w-[1600px] mx-auto relative min-h-[80vh]">
          {pages.map(page => (
            <div
              key={page.id}
              className={cn(
                "w-full",
                page.id === activeTab
                  ? "block animate-in fade-in slide-in-from-bottom-4 duration-500"
                  : "hidden"
              )}
            >
              {page.component}
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
