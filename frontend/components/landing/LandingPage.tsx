'use client';

import React, { useRef, useState, useEffect } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { Sparkles, Zap, Mic, Globe, ArrowRight, Play, Terminal, CheckCircle2, XCircle, Users, Briefcase, Lock, Eye, Video } from 'lucide-react';
import Navbar from './Navbar';
import Footer from './Footer';
import Pricing from './Pricing';
import { cn } from '@/lib/utils'; // Assuming cn utility exists

// --- HELPER COMPONENTS ---

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
    return (
        <div className="text-center mb-16 md:mb-20">
            <h2 className="text-[40px] md:text-[56px] font-[800] text-white tracking-tight leading-[1.1] mb-6">
                {title}
            </h2>
            {subtitle && (
                <p className="text-[20px] md:text-[24px] text-zinc-300 max-w-2xl mx-auto leading-relaxed font-medium">
                    {subtitle}
                </p>
            )}
        </div>
    );
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
    return (
        <div className={cn(
            "bg-[#0A0A0A] border border-white/10 rounded-3xl p-8 md:p-10 hover:border-indigo-500/30 transition-colors duration-300",
            className
        )}>
            {children}
        </div>
    );
}

// --- MAIN PAGE ---

export default function LandingPage({ onSignInClick }: { onSignInClick: () => void }) {
    const heroRef = useRef(null);

    // --- HERO COMPONENT ---
    const HeroSection = () => (
        <section ref={heroRef} className="relative z-10 pt-24 pb-20 lg:pt-36 lg:pb-32 overflow-hidden">
            <div className="w-full max-w-[1600px] mx-auto px-6 md:px-12 text-center">

                {/* Headline */}
                <h1 className="text-[56px] sm:text-[72px] lg:text-[96px] font-[900] tracking-tighter leading-[1.05] text-white mb-8 max-w-5xl mx-auto">
                    Turn Any Idea into <br className="hidden md:block" />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">Viral Reels</span> in Minutes
                </h1>

                {/* Sub-headline */}
                <p className="text-[22px] md:text-[28px] text-zinc-200 font-medium max-w-3xl mx-auto mb-10 leading-relaxed">
                    Write an idea <span className="text-zinc-500">→</span> AI creates script, voice, visuals, and ready-to-post videos.
                </p>

                {/* Primary CTA */}
                <div className="flex flex-col items-center gap-4 mb-16">
                    <button
                        onClick={onSignInClick}
                        className="group relative px-12 py-6 bg-white text-black font-[800] text-[22px] rounded-full hover:bg-indigo-50 transition-all transform hover:-translate-y-1 shadow-[0_0_40px_-10px_rgba(255,255,255,0.3)] flex items-center gap-3"
                    >
                        Get Started Free
                        <ArrowRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" />
                    </button>
                    <p className="text-zinc-400 text-[15px] font-medium flex items-center gap-2">
                        <CheckCircle2 size={16} className="text-green-500" /> No editing skills required
                        <span className="w-1 h-1 bg-zinc-700 rounded-full mx-1"></span>
                        <Eye size={16} className="text-indigo-400" /> Preview before credits are used
                    </p>
                </div>

                {/* Demo Placeholder / Visual */}
                <div className="relative w-full max-w-5xl mx-auto">
                    {/* Glow */}
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] h-[120%] bg-indigo-600/20 blur-[120px] rounded-full -z-10 pointer-events-none"></div>

                    {/* Interface Container */}
                    <div className="rounded-2xl overflow-hidden border border-white/10 shadow-2xl bg-[#050505] aspect-video flex items-center justify-center relative group">
                        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent z-10"></div>

                        {/* Fake UI Elements */}
                        <div className="text-center z-20 transform transition-transform duration-500 group-hover:scale-105">
                            <div className="w-20 h-20 bg-white/10 backdrop-blur-md rounded-full flex items-center justify-center mb-6 mx-auto border border-white/20">
                                <Play size={32} className="text-white fill-white" />
                            </div>
                            <p className="text-xl font-bold text-white">See it in action</p>
                        </div>

                        {/* Background Video Simulation */}
                        <div className="absolute inset-0 z-0 opacity-40">
                            {/* Abstract animated geometric shapes or a blurred video loop would go here */}
                            <div className="w-full h-full bg-[url('https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=2564&auto=format&fit=crop')] bg-cover bg-center"></div>
                        </div>
                    </div>
                </div>

            </div>
        </section>
    );

    // --- PROBLEM SECTION ---
    const ProblemSection = () => (
        <section className="py-24 bg-[#050505] border-t border-white/5">
            <div className="w-full max-w-[1400px] mx-auto px-6 md:px-12">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-16 items-center">
                    <div>
                        <div className="inline-block px-4 py-1.5 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 font-bold text-sm tracking-wide uppercase mb-6">
                            The Struggle
                        </div>
                        <h2 className="text-[40px] md:text-[50px] font-bold text-white mb-6 leading-tight">
                            Why creating content feels like a <span className="text-red-500">full-time job</span>.
                        </h2>
                        <div className="space-y-6">
                            {[
                                "Spending 4+ hours editing a single 30-second reel.",
                                "Juggling 5 different tools for scripts, voice, and stock footage.",
                                "Burnout from trying to post daily to grow your channel."
                            ].map((pain, i) => (
                                <div key={i} className="flex items-start gap-4">
                                    <XCircle className="text-zinc-600 shrink-0 mt-1" size={24} />
                                    <p className="text-[20px] text-zinc-400 font-medium leading-relaxed">{pain}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                    <div className="relative">
                        <div className="absolute inset-0 bg-gradient-to-r from-red-500/10 to-transparent blur-3xl opacity-30 rounded-full"></div>
                        <Card className="relative z-10 border-indigo-500/30 bg-[#0A0A0A]/80 backdrop-blur">
                            <div className="flex items-center gap-3 mb-6">
                                <Sparkles className="text-indigo-400" size={28} />
                                <h3 className="text-2xl font-bold text-white">The Solution</h3>
                            </div>
                            <p className="text-[22px] text-zinc-100 leading-relaxed mb-6">
                                <span className="text-white font-bold">One tool.</span> Zero editing. <br />
                                Just type your topic, and our AI handles the boring stuff.
                            </p>
                            <div className="h-2 w-full bg-zinc-800 rounded-full overflow-hidden">
                                <div className="h-full bg-indigo-500 w-[85%]"></div>
                            </div>
                            <p className="text-right text-sm text-indigo-400 mt-2 font-mono">Efficiency +85%</p>
                        </Card>
                    </div>
                </div>
            </div>
        </section>
    );

    // --- HOW IT WORKS ---
    const HowItWorksSection = () => (
        <section className="py-24 border-t border-white/5">
            <div className="w-full max-w-[1600px] mx-auto px-6 md:px-12">
                <SectionHeader title="How It Works" subtitle="Three steps. From blank page to viral page." />

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {[
                        { icon: Terminal, title: "1. Write an idea", desc: "Just enter a topic. No scripts needed." },
                        { icon: Zap, title: "2. AI Builds it", desc: "We generate script, voice, & visuals instantly." },
                        { icon: ArrowRight, title: "3. Download", desc: "Get a finished 9:16 video ready to post." }
                    ].map((step, i) => (
                        <Card key={i} className="flex flex-col items-center text-center py-16 hover:bg-white/[0.02]">
                            <div className="w-20 h-20 rounded-2xl bg-indigo-500/10 flex items-center justify-center mb-8 text-indigo-400">
                                <step.icon size={40} />
                            </div>
                            <h3 className="text-[28px] font-bold text-white mb-4">{step.title}</h3>
                            <p className="text-[20px] text-zinc-400 leading-relaxed max-w-xs">{step.desc}</p>
                        </Card>
                    ))}
                </div>
            </div>
        </section>
    );

    // --- FEATURES ---
    const FeaturesSection = () => (
        <section className="py-24 bg-[#050505] border-t border-white/5">
            <div className="w-full max-w-[1400px] mx-auto px-6 md:px-12">
                <SectionHeader title="Everything You Need" subtitle="Powerful tools for the modern creator." />

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {[
                        { icon: Sparkles, title: "Idea Studio", desc: "Viral scripts from trending topics." },
                        { icon: Mic, title: "Voice Lab", desc: "Ultra-realistic AI voiceovers." },
                        { icon: Globe, title: "Global Dubber", desc: "Translate content into 30+ languages." },
                        { icon: Video, title: "Auto-Editor", desc: "Smart pacing and b-roll selection." },
                        { icon: Users, title: "Face Clone", desc: "Use your own AI avatar (Coming Soon)." },
                        { icon: Zap, title: "Fast Render", desc: "1080p outputs in under 60 seconds." }
                    ].map((feature, i) => (
                        <div key={i} className="p-8 rounded-2xl border border-white/5 bg-white/[0.01] hover:bg-white/[0.03] transition-colors flex flex-col gap-4">
                            <div className="w-12 h-12 rounded-lg bg-zinc-900 border border-white/10 flex items-center justify-center text-zinc-300">
                                <feature.icon size={24} />
                            </div>
                            <div>
                                <h3 className="text-xl font-bold text-white mb-2">{feature.title}</h3>
                                <p className="text-lg text-zinc-400">{feature.desc}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );

    // --- AUDIENCE ---
    const AudienceSection = () => (
        <section className="py-24 border-t border-white/5">
            <div className="w-full max-w-[1200px] mx-auto px-6 md:px-12">
                <SectionHeader title="Who Is This For?" />
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* Solo Creator */}
                    <Card className="border-indigo-500/20 bg-gradient-to-b from-indigo-900/10 to-transparent">
                        <div className="flex items-center gap-4 mb-8">
                            <div className="p-3 rounded-xl bg-indigo-500 text-white">
                                <Users size={28} />
                            </div>
                            <h3 className="text-3xl font-bold text-white">Solo Creators</h3>
                        </div>
                        <ul className="space-y-4">
                            {[
                                "Scale your personal brand without hiring editors.",
                                "Post 3x daily without burnout.",
                                "Test new niches instantly."
                            ].map((item, i) => (
                                <li key={i} className="flex items-start gap-3 text-lg text-zinc-300">
                                    <CheckCircle2 size={20} className="text-indigo-400 mt-1 shrink-0" />
                                    <span>{item}</span>
                                </li>
                            ))}
                        </ul>
                    </Card>

                    {/* Agencies */}
                    <Card className="border-white/10">
                        <div className="flex items-center gap-4 mb-8">
                            <div className="p-3 rounded-xl bg-zinc-800 text-white">
                                <Briefcase size={28} />
                            </div>
                            <h3 className="text-3xl font-bold text-white">Agencies</h3>
                        </div>
                        <ul className="space-y-4">
                            {[
                                "Manage unlimited client accounts.",
                                "Reduce production costs by 90%.",
                                "Deliver videos in minutes, not days."
                            ].map((item, i) => (
                                <li key={i} className="flex items-start gap-3 text-lg text-zinc-300">
                                    <CheckCircle2 size={20} className="text-zinc-500 mt-1 shrink-0" />
                                    <span>{item}</span>
                                </li>
                            ))}
                        </ul>
                    </Card>
                </div>
            </div>
        </section>
    );

    // --- TRUST & CONFIDENCE ---
    const TrustSection = () => (
        <section className="py-20 bg-[#080808] border-y border-white/5">
            <div className="w-full max-w-[1400px] mx-auto px-6 md:px-12 text-center">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-12 text-center">
                    <div>
                        <h4 className="text-white text-lg font-bold mb-2 flex items-center justify-center gap-2"><Lock size={18} className="text-zinc-500" /> Private & Secure</h4>
                        <p className="text-zinc-400">Your ideas and scripts belong to you. We don't train on your data without permission.</p>
                    </div>
                    <div>
                        <h4 className="text-white text-lg font-bold mb-2 flex items-center justify-center gap-2"><Eye size={18} className="text-zinc-500" /> Preview First</h4>
                        <p className="text-zinc-400">See the generated script and visuals before you spend any extensive rendering credits.</p>
                    </div>
                    <div>
                        <h4 className="text-white text-lg font-bold mb-2 flex items-center justify-center gap-2"><CheckCircle2 size={18} className="text-zinc-500" /> Built for Creators</h4>
                        <p className="text-zinc-400">Designed specifically for the fast-paced world of Shorts, Reels, and TikTok.</p>
                    </div>
                </div>
            </div>
        </section>
    );

    // --- FINAL CTA ---
    const FinalCTA = () => (
        <section className="py-32 relative overflow-hidden">
            {/* Background Glow */}
            <div className="absolute inset-0 bg-indigo-600/5 z-0"></div>
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-indigo-500/10 blur-[150px] rounded-full pointer-events-none"></div>

            <div className="relative z-10 w-full max-w-4xl mx-auto px-6 text-center">
                <h2 className="text-[48px] md:text-[64px] font-[900] text-white tracking-tight leading-none mb-8">
                    Start Creating <br /> Your Empire Today.
                </h2>
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                    <button
                        onClick={onSignInClick}
                        className="px-10 py-5 bg-white text-black font-[800] text-[20px] rounded-full hover:bg-zinc-200 transition-colors shadow-2xl shadow-indigo-500/20"
                    >
                        Get Started Free
                    </button>
                    <button
                        onClick={onSignInClick} // Or navigate to pricing/demo
                        className="px-10 py-5 bg-transparent border border-white/20 text-white font-[700] text-[20px] rounded-full hover:bg-white/5 transition-colors"
                    >
                        View Pricing
                    </button>
                </div>
                <p className="text-zinc-500 mt-6 font-medium">No credit card required · Cancel anytime</p>
            </div>
        </section>
    );

    return (
        <div className="min-h-screen bg-[#030303] text-white font-sans selection:bg-indigo-500/30 overflow-x-hidden">
            <Navbar onSignInClick={onSignInClick} />

            <HeroSection />

            {/* Social Proof Strip - Simple */}
            <div className="border-b border-white/5 bg-black py-6 overflow-hidden">
                <div className="w-full max-w-[1400px] mx-auto px-6 flex flex-wrap justify-center gap-12 md:gap-20 opacity-50 grayscale transition-all duration-500 hover:grayscale-0 hover:opacity-100">
                    {['TubeWorks', 'VidAI', 'StreamPro', 'CreatorLabs', 'ViralFlow'].map(logo => (
                        <span key={logo} className="text-xl md:text-2xl font-bold font-mono text-zinc-400 tracking-wider flex items-center gap-2">
                            <div className="w-6 h-6 bg-zinc-800 rounded-full"></div> {logo}
                        </span>
                    ))}
                </div>
            </div>

            <ProblemSection />
            <HowItWorksSection />
            <FeaturesSection />
            <AudienceSection />
            <TrustSection />
            <FinalCTA />

            <Pricing />
            <Footer />
        </div>
    );
}

// Ensure the render_diffs function (if any) or existing diffs are clean.
// I am replacing the entire file for the overhaul.
// I kept 'Navbar', 'Footer', 'Pricing' imports as they were in the original file.
// I removed the complex 'BentoCard' and other local components that are no longer needed or replaced them with cleaner versions. 

