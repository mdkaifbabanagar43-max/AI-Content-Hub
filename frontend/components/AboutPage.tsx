'use client';

import React from 'react';
import { ArrowLeft, Zap, Users, Globe } from 'lucide-react';
import Link from 'next/link';

export default function AboutPage() {
    return (
        <div className="min-h-screen bg-[#030303] text-zinc-300 font-sans selection:bg-indigo-500/30">
            <nav className="border-b border-white/5 bg-black/40 backdrop-blur-md sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
                    <Link href="/" className="text-sm font-bold text-white hover:text-zinc-300 transition-colors">
                        Antigravity.ai
                    </Link>
                    <Link href="/" className="flex items-center gap-2 text-xs text-zinc-500 hover:text-white transition-colors">
                        <ArrowLeft size={14} /> Back to Home
                    </Link>
                </div>
            </nav>

            <main className="max-w-4xl mx-auto px-6 py-24 text-center">
                <h1 className="text-5xl md:text-7xl font-bold text-white mb-8 tracking-tighter">
                    Built for the <span className="text-indigo-500">Future.</span>
                </h1>

                <p className="text-xl text-zinc-400 max-w-2xl mx-auto mb-20 leading-relaxed font-light">
                    Founded in 2025, AI Studio helps creators scale their output using LLMs and Neural Audio. We are democratizing viral video creation with Generative AI.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <div className="p-8 border border-white/10 rounded-3xl bg-zinc-900/20 backdrop-blur-sm">
                        <Zap className="mx-auto text-indigo-400 mb-4" size={32} />
                        <div className="text-4xl font-bold text-white mb-2">1M+</div>
                        <div className="text-xs font-mono uppercase text-zinc-500">Frames Generated</div>
                    </div>
                    <div className="p-8 border border-white/10 rounded-3xl bg-zinc-900/20 backdrop-blur-sm">
                        <Users className="mx-auto text-emerald-400 mb-4" size={32} />
                        <div className="text-4xl font-bold text-white mb-2">10k+</div>
                        <div className="text-xs font-mono uppercase text-zinc-500">Active Creators</div>
                    </div>
                    <div className="p-8 border border-white/10 rounded-3xl bg-zinc-900/20 backdrop-blur-sm">
                        <Globe className="mx-auto text-purple-400 mb-4" size={32} />
                        <div className="text-4xl font-bold text-white mb-2">150+</div>
                        <div className="text-xs font-mono uppercase text-zinc-500">Countries Served</div>
                    </div>
                </div>

                <div className="mt-24">
                    <p className="text-zinc-600 font-mono text-sm uppercase tracking-widest mb-4">Our Offices</p>
                    <p className="text-white text-lg">San Francisco • Bangalore • Remote</p>
                </div>
            </main>
        </div>
    );
}
