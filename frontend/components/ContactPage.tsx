'use client';

import React from 'react';
import { Mail, Clock, Send, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function ContactPage() {
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

            <main className="max-w-7xl mx-auto px-6 py-24">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-20">

                    {/* Left: Headline & Form */}
                    <div>
                        <h1 className="text-5xl font-bold text-white mb-4 tracking-tighter">Get in touch.</h1>
                        <p className="text-zinc-500 text-lg mb-12">For enterprise inquiries or technical support.</p>

                        <form className="space-y-6 max-w-md">
                            <div>
                                <label className="block text-xs font-mono text-zinc-500 mb-2 uppercase">Name</label>
                                <input type="text" className="w-full bg-zinc-900/50 border border-white/10 rounded-lg p-3 text-white focus:outline-none focus:border-indigo-500/50 transition-colors" placeholder="Your Name" />
                            </div>
                            <div>
                                <label className="block text-xs font-mono text-zinc-500 mb-2 uppercase">Email</label>
                                <input type="email" className="w-full bg-zinc-900/50 border border-white/10 rounded-lg p-3 text-white focus:outline-none focus:border-indigo-500/50 transition-colors" placeholder="name@company.com" />
                            </div>
                            <div>
                                <label className="block text-xs font-mono text-zinc-500 mb-2 uppercase">Message</label>
                                <textarea className="w-full bg-zinc-900/50 border border-white/10 rounded-lg p-3 text-white focus:outline-none focus:border-indigo-500/50 transition-colors h-32 resize-none" placeholder="How can we help?"></textarea>
                            </div>
                            <button className="px-6 py-3 bg-white text-black font-bold rounded-lg hover:bg-zinc-200 transition-colors flex items-center gap-2">
                                Send Message <Send size={16} />
                            </button>
                        </form>
                    </div>

                    {/* Right: Info Card */}
                    <div className="flex items-center justify-center lg:justify-end">
                        <div className="w-full max-w-sm bg-zinc-900/30 border border-white/10 rounded-3xl p-8 backdrop-blur-sm">
                            <h3 className="text-white font-bold text-xl mb-6">Support Channels</h3>

                            <div className="space-y-6">
                                <div className="flex items-start gap-4">
                                    <div className="p-3 bg-indigo-500/10 rounded-xl">
                                        <Mail className="text-indigo-400" size={24} />
                                    </div>
                                    <div>
                                        <p className="text-xs font-mono text-zinc-500 uppercase mb-1">Email Us</p>
                                        <a href="mailto:mdkaifbabanagar60@gmail.com" className="text-white font-medium hover:text-indigo-400 transition-colors block break-all">
                                            mdkaifbabanagar60@gmail.com
                                        </a>
                                    </div>
                                </div>

                                <div className="flex items-start gap-4">
                                    <div className="p-3 bg-emerald-500/10 rounded-xl">
                                        <Clock className="text-emerald-400" size={24} />
                                    </div>
                                    <div>
                                        <p className="text-xs font-mono text-zinc-500 uppercase mb-1">Response Time</p>
                                        <p className="text-white font-medium">
                                            We typically reply within 24 hours.
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="mt-8 pt-8 border-t border-white/5 text-xs text-zinc-600">
                                Need faster support? Join our <a href="#" className="underline hover:text-white">Discord Community</a>.
                            </div>
                        </div>
                    </div>

                </div>
            </main>
        </div>
    );
}
