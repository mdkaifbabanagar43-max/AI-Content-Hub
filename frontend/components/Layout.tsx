'use client';

import React, { useState, useEffect } from 'react';
import { Lightbulb, Scissors, Mic, Globe, Menu, LogOut, LogIn, Minimize2 } from 'lucide-react';
import IdeaStudio from './IdeaStudio';
import ViralRepurposer from './ViralRepurposer';
import GlobalDubber from './GlobalDubber';
import { useAuth } from '../context/AuthContext';

import Sidebar from './Sidebar';
import DashboardHome from './DashboardHome';
import Pricing from './landing/Pricing';
// import IdeaStudio from './IdeaStudio'; // Already imported
// import ViralRepurposer from './ViralRepurposer'; // Already imported
// import AIVoiceArtist from './AIVoiceArtist'; // Already imported

import { cn } from '@/lib/utils';

export default function Layout({ children }: { children?: React.ReactNode }) {
  const [activeTab, setActiveTab] = useState('dashboard'); // Default to dashboard
  const { user } = useAuth();

  // Sidebar States
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isFocusMode, setIsFocusMode] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Initialize from LocalStorage (Client-side only)
  useEffect(() => {
    const saved = localStorage.getItem('sidebar-collapsed');
    if (saved) {
      setIsCollapsed(saved === 'true');
    }
  }, []);

  const toggleSidebar = () => {
    const newState = !isCollapsed;
    setIsCollapsed(newState);
    localStorage.setItem('sidebar-collapsed', String(newState));
  };

  const toggleFocusMode = () => {
    setIsFocusMode(!isFocusMode);
  };

  // Close mobile menu when tab changes
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [activeTab]);

  return (
    <div className="flex min-h-screen bg-[#030303] text-white font-sans">
      {/* ... (Header logic unchanged) ... */}

      {/* Sidebar Component */}
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

      {/* Floating Exit Focus Mode Button */}
      {isFocusMode && (
        <button
          onClick={toggleFocusMode}
          className="fixed bottom-6 left-6 z-50 p-3 bg-zinc-900 border border-white/10 text-zinc-400 hover:text-white rounded-full shadow-2xl transition-all duration-300 hover:scale-110 group"
          title="Exit Focus Mode"
        >
          <Minimize2 size={20} />
          <span className="absolute left-full ml-3 px-2 py-1 bg-black border border-white/10 rounded text-xs text-white opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
            Exit Focus Mode
          </span>
        </button>
      )}

      {/* Main Content Area */}
      <main
        className={cn(
          "flex-1 w-full pt-16 md:pt-0 min-h-screen relative transition-all duration-300 ease-in-out",
          isFocusMode ? "pl-0" : isCollapsed ? "md:pl-[80px]" : "md:pl-[260px]"
        )}
      >
        {/* Subtle Grid Background */}
        <div className={cn(
          "fixed inset-0 bg-[linear-gradient(to_right,#ffffff_1px,transparent_1px),linear-gradient(to_bottom,#ffffff_1px,transparent_1px)] bg-[size:40px_40px] opacity-[0.02] pointer-events-none md:ml-0 transition-all duration-300",
          isFocusMode ? "ml-0" : isCollapsed ? "md:ml-[80px]" : "md:ml-[260px]"
        )} />

        <div className="relative z-10 p-6 md:p-12 w-full max-w-[1920px] mx-auto">

          {/* Top Bar / Header - HIDE for immersive apps like IdeaStudio */}
          {activeTab !== 'idea-studio' && (
            <header className="mb-8 md:mb-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">{
                  activeTab === 'dashboard' ? 'Mission Control' :
                    activeTab === 'repurposer' ? 'Viral Repurposer' :
                      activeTab === 'dubber' ? 'Global Dubber' :
                        activeTab === 'gallery' ? 'My Masterpieces' : activeTab
                }</h2>
                <p className="text-zinc-400 mt-2 text-sm md:text-[16px]">Manage your viral empire from here.</p>
              </div>

              <div className="flex gap-4 self-end md:self-auto">
                <div className="h-10 w-10 rounded-full bg-zinc-900 border border-white/10 flex items-center justify-center text-zinc-400 hover:text-white cursor-pointer transition-colors">
                  <Globe size={18} />
                </div>
              </div>
            </header>
          )}

          {/* Dynamic Content Rendering (Keep-Alive Mode) */}
          <div className="mt-4">
            {/* Mission Control */}
            <div className={cn("animate-in fade-in duration-500", activeTab === 'dashboard' ? 'block' : 'hidden')}>
              <DashboardHome setActiveTab={setActiveTab} />
            </div>

            {/* Idea Studio */}
            <div className={cn("animate-in fade-in duration-500", activeTab === 'idea-studio' ? 'block' : 'hidden')}>
              <IdeaStudio />
            </div>

            {/* Viral Repurposer */}
            <div className={cn("animate-in fade-in duration-500", activeTab === 'repurposer' ? 'block' : 'hidden')}>
              <ViralRepurposer />
            </div>

            {/* Global Dubber */}
            <div className={cn("animate-in fade-in duration-500", activeTab === 'dubber' ? 'block' : 'hidden')}>
              <GlobalDubber />
            </div>

            {/* Gallery (Placeholder) */}
            <div className={cn("animate-in fade-in duration-500", activeTab === 'gallery' ? 'block' : 'hidden')}>
              <div className="text-center py-20 bg-zinc-900/30 border border-white/5 rounded-3xl">
                <h3 className="text-2xl font-bold text-white mb-2">My Masterpieces</h3>
                <p className="text-zinc-500">Your generated content gallery is coming soon.</p>
              </div>
            </div>

            {/* Pricing / Upgrade View */}
            <div className={cn("animate-in fade-in duration-500", activeTab === 'pricing' ? 'block' : 'hidden')}>
              <Pricing />
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
