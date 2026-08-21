'use client';

import React from 'react';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface LegalPageProps {
    type: 'privacy' | 'terms';
}

export default function LegalPage({ type }: LegalPageProps) {
    const title = type === 'privacy' ? 'Privacy Policy' : 'Terms of Service';
    const lastUpdated = 'Last updated: December 16, 2025';

    return (
        <div className="min-h-screen bg-[#030303] text-zinc-300 font-sans selection:bg-indigo-500/30">
            {/* Minimal Navbar */}
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

            <main className="max-w-2xl mx-auto px-6 py-24">
                <h1 className="text-4xl font-bold text-white mb-4 tracking-tight">{title}</h1>
                <p className="text-zinc-500 text-sm mb-12 font-mono">{lastUpdated}</p>

                <div className="prose prose-invert prose-zinc max-w-none">
                    {type === 'privacy' ? (
                        <>
                            <p className="text-lg text-zinc-400 mb-8">
                                At Antigravity.ai, we take your privacy seriously. We only collect data necessary to provide our AI services and improve your experience.
                            </p>

                            <h3 className="text-white font-bold text-xl mt-12 mb-4">1. Data Collection</h3>
                            <p>We collect information you provide directly to us, such as when you create an account, update your profile, or use our generative AI tools. This includes input prompts, uploaded media, and generated content.</p>

                            <h3 className="text-white font-bold text-xl mt-12 mb-4">2. AI Usage</h3>
                            <p>Your content is processed by our AI models (including but not limited to Gemini and Google Cloud TTS) solely for the purpose of generating your requested outputs. We do not use your private data to train our foundational models without explicit consent.</p>

                            <h3 className="text-white font-bold text-xl mt-12 mb-4">3. Security</h3>
                            <p>We implement industry-standard security measures, including encryption at rest and in transit, to protect your personal information.</p>
                        </>
                    ) : (
                        <>
                            <p className="text-lg text-zinc-400 mb-8">
                                By using Antigravity.ai, you agree to these terms. Please read them carefully.
                            </p>

                            <h3 className="text-white font-bold text-xl mt-12 mb-4">1. Usage Limits</h3>
                            <p>Users are subject to credit limits based on their subscription plan. Attempts to bypass these limits or reverse-engineer our API will result in immediate account termination.</p>

                            <h3 className="text-white font-bold text-xl mt-12 mb-4">2. Intellectual Property</h3>
                            <p>You retain ownership of the content you generate using our platform, subject to the rights of third parties in any uploaded assets. Antigravity.ai retains all rights to the underlying software and models.</p>

                            <h3 className="text-white font-bold text-xl mt-12 mb-4">3. Payments</h3>
                            <p>Subscriptions are billed monthly. You may cancel at any time, but no refunds will be issued for partial months.</p>
                        </>
                    )}
                </div>
            </main>
        </div>
    );
}
