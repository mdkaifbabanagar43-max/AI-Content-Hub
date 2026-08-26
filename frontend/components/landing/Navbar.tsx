'use client';

import React, { useState, useEffect } from 'react';
import { Menu, X, ArrowRight, Cpu, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/navigation';

interface NavbarProps {
    onSignInClick: () => void;
    onWaitlistClick?: () => void;
}

export default function Navbar({ onSignInClick, onWaitlistClick }: NavbarProps) {
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [scrolled, setScrolled] = useState(false);
    const router = useRouter();

    useEffect(() => {
        const handleScroll = () => {
            setScrolled(window.scrollY > 20);
        };
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    const links = [
        { name: 'Pipeline', id: 'pipeline' },
        { name: 'Agency Solutions', id: 'solutions' },
        { name: 'Cloud Architecture', id: 'architecture' },
        { name: 'Developer API', id: 'api' },
        { name: 'Pricing', id: 'pricing' }
    ];

    const scrollToSection = (id: string) => {
        const element = document.getElementById(id);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth' });
        }
        setMobileMenuOpen(false);
    };

    return (
        <>
            {/* Top Ecosystem Bar for Google Cloud & Startup Program Reviewers */}
            <aside aria-label="Ecosystem Announcement" className="w-full bg-gradient-to-r from-indigo-950/80 via-purple-950/80 to-slate-950/80 border-b border-indigo-500/20 text-xs py-1.5 px-4 text-center text-zinc-300 flex items-center justify-center gap-2.5 z-50 relative">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-semibold tracking-wider uppercase text-[10px]">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    GCP Live
                </span>
                <span className="hidden sm:inline text-zinc-400">Powered by Google Cloud & Vertex AI ·</span>
                <span className="font-medium text-white">Gemini 2.0 Flash + Veo Video Orchestration Engine</span>
                <span className="hidden md:inline-flex items-center gap-1 text-indigo-300 ml-2 font-mono text-[11px]">
                    <Cpu size={12} /> B2B SMMA Private Beta
                </span>
            </aside>

            <header className={`sticky top-0 left-0 right-0 z-40 transition-all duration-300 w-full ${
                scrolled 
                    ? 'bg-black/85 backdrop-blur-xl border-b border-white/10 shadow-[0_10px_30px_rgba(0,0,0,0.8)]' 
                    : 'bg-black/40 backdrop-blur-md border-b border-white/5'
            }`}>
                <div className="w-full max-w-[1600px] mx-auto px-4 sm:px-6 md:px-12 h-16 sm:h-20 flex items-center justify-between">
                    {/* Logo */}
                    <div
                        className="flex items-center gap-3 cursor-pointer group"
                        onClick={() => router.push('/')}
                    >
                        <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-600 to-pink-500 p-[1px] shadow-lg shadow-indigo-500/20 group-hover:shadow-indigo-500/40 transition-shadow">
                            <div className="w-full h-full bg-[#07070d] rounded-[11px] flex items-center justify-center">
                                <Sparkles className="w-5 h-5 text-indigo-400 group-hover:scale-110 transition-transform" />
                            </div>
                        </div>
                        <div>
                            <div className="text-xl sm:text-2xl font-[900] tracking-tight text-white flex items-center gap-1">
                                Clone<span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400">Frame</span>
                            </div>
                            <div className="text-[10px] uppercase font-mono tracking-widest text-zinc-400 -mt-1 hidden sm:block">
                                AI Video Pipeline API
                            </div>
                        </div>
                    </div>

                    {/* Desktop Navigation Links */}
                    <div className="hidden lg:flex items-center gap-7">
                        {links.map((link) => (
                            <button
                                key={link.name}
                                onClick={() => scrollToSection(link.id)}
                                className="text-[14px] font-medium text-zinc-300 hover:text-white transition-colors hover:scale-105 active:scale-95"
                            >
                                {link.name}
                            </button>
                        ))}
                    </div>

                    {/* Desktop Actions */}
                    <div className="hidden sm:flex items-center gap-3">
                        <button
                            onClick={onSignInClick}
                            className="px-4 py-2 rounded-xl text-sm font-medium text-zinc-300 hover:text-white hover:bg-white/5 border border-transparent hover:border-white/10 transition-all"
                        >
                            Sign In
                        </button>
                        <button
                            onClick={onWaitlistClick || onSignInClick}
                            className="group relative px-5 py-2.5 rounded-xl text-sm font-bold bg-white text-black hover:bg-zinc-100 transition-all shadow-[0_0_25px_-5px_rgba(255,255,255,0.4)] flex items-center gap-2 hover:-translate-y-0.5 active:translate-y-0"
                        >
                            Join Private Beta
                            <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                        </button>
                    </div>

                    {/* Mobile Menu Toggle */}
                    <div className="flex sm:hidden items-center gap-2">
                        <button
                            onClick={onSignInClick}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-white text-black"
                        >
                            Beta
                        </button>
                        <button
                            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                            className="p-2 text-zinc-400 hover:text-white rounded-lg bg-white/5 border border-white/10"
                            aria-label="Toggle Menu"
                        >
                            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
                        </button>
                    </div>
                </div>

                {/* Mobile Dropdown */}
                <AnimatePresence>
                    {mobileMenuOpen && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="lg:hidden bg-[#0a0a10]/95 border-b border-white/10 overflow-hidden backdrop-blur-2xl"
                        >
                            <div className="px-6 py-6 flex flex-col gap-4">
                                {links.map((link) => (
                                    <button
                                        key={link.name}
                                        onClick={() => scrollToSection(link.id)}
                                        className="text-base font-medium text-zinc-300 hover:text-white text-left py-1"
                                    >
                                        {link.name}
                                    </button>
                                ))}
                                <div className="pt-4 border-t border-white/10 flex flex-col gap-3">
                                    <button
                                        onClick={() => {
                                            onSignInClick();
                                            setMobileMenuOpen(false);
                                        }}
                                        className="w-full py-3 rounded-xl font-bold bg-white text-black text-center"
                                    >
                                        Join Private Beta / Sign In
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </header>
        </>
    );
}
