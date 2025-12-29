'use client';

import React from 'react';
import { ArrowLeft, AlertCircle } from 'lucide-react';
import Link from 'next/link';

export default function RefundPolicy() {
    return (
        <div className="min-h-screen bg-[#030303] text-zinc-300 font-sans selection:bg-red-500/30">
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
                <h1 className="text-4xl font-bold text-white mb-8 tracking-tight">Refund & Cancellation Policy</h1>

                <div className="p-6 bg-red-500/10 border border-red-500/20 rounded-2xl mb-12 flex items-start gap-4">
                    <AlertCircle className="text-red-500 flex-shrink-0" />
                    <div>
                        <h3 className="text-red-400 font-bold mb-2">Digital Goods Policy</h3>
                        <p className="text-red-300/80 text-sm">
                            Since AI Studio provides non-tangible, irrevocable digital goods (AI Credits), we do not issue refunds once an order is confirmed and credits are sent.
                        </p>
                    </div>
                </div>

                <div className="prose prose-invert prose-zinc max-w-none">
                    <h3 className="text-white font-bold text-xl mb-4">1. Cancellations</h3>
                    <p>You may cancel your subscription at any time to prevent future billing. Your credits will remain accessible until the end of your current billing cycle.</p>

                    <h3 className="text-white font-bold text-xl mt-12 mb-4">2. Technical Errors</h3>
                    <p>In case of technical errors such as double billing or credit delivery failure, please contact support immediately at <strong>mdkaifbabanagar60@gmail.com</strong>. We will investigate and resolve verified technical issues promptly.</p>

                    <h3 className="text-white font-bold text-xl mt-12 mb-4">3. Usage Acceptance</h3>
                    <p>By purchasing a subscription or credit pack, you acknowledge that you have read and agree to this no-refund policy. Free trials are provided to ensure the system meets your needs before purchase.</p>
                </div>
            </main>
        </div>
    );
}
