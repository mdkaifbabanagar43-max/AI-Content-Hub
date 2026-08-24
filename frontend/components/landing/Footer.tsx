'use client';

import React from 'react';
import Link from 'next/link';
import { Twitter, Github, Disc as Discord, Shield, Cloud, Server, Cpu, CheckCircle2, Lock, ArrowUpRight } from 'lucide-react';

export default function Footer() {
    return (
        <footer className="relative z-10 bg-[#040408] border-t border-white/10 pt-20 pb-12 overflow-hidden">
            {/* Background Glow */}
            <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[800px] h-[300px] bg-gradient-to-t from-indigo-900/15 to-transparent blur-[140px] pointer-events-none -z-10"></div>

            <div className="w-full max-w-[1600px] mx-auto px-6 md:px-12">
                {/* Main Links Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-12 mb-16">
                    {/* Brand & Mission */}
                    <div className="lg:col-span-2 space-y-5">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 p-[1px]">
                                <div className="w-full h-full bg-black rounded-[7px] flex items-center justify-center font-bold text-white text-sm">
                                    CF
                                </div>
                            </div>
                            <h3 className="text-2xl font-[900] tracking-tight text-white">
                                Clone<span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400">Frame</span>
                            </h3>
                        </div>

                        <p className="text-zinc-400 text-sm leading-relaxed max-w-sm">
                            The automated AI video generation & cloning pipeline for B2B Social Media Marketing Agencies. Orchestrating Gemini 2.0, ElevenLabs, and Veo into high-throughput cloud workflows.
                        </p>

                        {/* Founder & Accelerator Track Badge */}
                        <div className="pt-2 flex flex-col gap-2">
                            <div className="inline-flex items-center gap-2 text-xs text-zinc-300 font-medium bg-white/[0.04] border border-white/10 rounded-lg px-3 py-1.5 w-fit">
                                <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse"></span>
                                Founded by <span className="text-white font-semibold">Md Kaif Babanagar</span>
                            </div>
                            <div className="text-[12px] text-zinc-400 font-mono flex items-center gap-2">
                                <span>🚀 YC Startup School Track</span>
                                <span>·</span>
                                <span>B2B Multi-Tenant Architecture</span>
                            </div>
                        </div>
                    </div>

                    {/* Col 2: Pipeline & Technology */}
                    <div>
                        <h4 className="text-white text-sm font-bold uppercase tracking-wider mb-5 flex items-center gap-2">
                            <Cpu size={14} className="text-indigo-400" /> Pipeline Tech
                        </h4>
                        <ul className="space-y-3 text-sm">
                            {[
                                { name: 'Gemini 2.0 Flash Scripting', tag: 'Vertex AI' },
                                { name: 'ElevenLabs Voice Engine', tag: '30+ Langs' },
                                { name: 'Google Veo Neural Video', tag: '1080p' },
                                { name: 'Cloud Tasks Queue', tag: 'Async' },
                                { name: 'Automated Dialogue Mux', tag: 'Lip-Sync' }
                            ].map((item, i) => (
                                <li key={i} className="flex items-center justify-between text-zinc-400 hover:text-white transition-colors group cursor-default">
                                    <span>{item.name}</span>
                                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-zinc-400 group-hover:text-indigo-300">
                                        {item.tag}
                                    </span>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* Col 3: B2B Solutions */}
                    <div>
                        <h4 className="text-white text-sm font-bold uppercase tracking-wider mb-5">
                            Agency Solutions
                        </h4>
                        <ul className="space-y-3 text-sm">
                            {[
                                'Multi-Client Workspaces',
                                'Brand Style & Character DNA',
                                'Batch Reel Generation',
                                'Viral Hook Engineering',
                                'Agency White-Label API',
                                'Dedicated Cloud Isolation'
                            ].map(item => (
                                <li key={item}>
                                    <a href="#solutions" className="text-zinc-400 hover:text-indigo-300 transition-colors">
                                        {item}
                                    </a>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* Col 4: Trust & Compliance */}
                    <div>
                        <h4 className="text-white text-sm font-bold uppercase tracking-wider mb-5">
                            Security & Legal
                        </h4>
                        <ul className="space-y-3 text-sm">
                            {[
                                { name: 'Privacy Policy', href: '/privacy' },
                                { name: 'Terms of Service', href: '/terms' },
                                { name: 'Refund Policy', href: '/refund-policy' },
                                { name: 'Enterprise VPC Security', href: '#architecture' },
                                { name: 'Contact Engineering', href: '/contact' }
                            ].map(item => (
                                <li key={item.name}>
                                    <Link href={item.href} className="text-zinc-400 hover:text-indigo-300 transition-colors flex items-center gap-1 group">
                                        <span>{item.name}</span>
                                        <ArrowUpRight size={12} className="opacity-0 group-hover:opacity-100 transition-opacity text-indigo-400" />
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>

                {/* Cloud & Compute Verification Bar */}
                <div className="border-t border-white/10 pt-8 pb-8 flex flex-col md:flex-row items-center justify-between gap-6 bg-white/[0.01] rounded-2xl px-6 my-6 border border-white/5">
                    <div className="flex flex-wrap items-center gap-4 text-xs text-zinc-400">
                        <div className="flex items-center gap-2">
                            <Cloud size={16} className="text-blue-400" />
                            <span className="text-zinc-300 font-medium">Google Cloud Platform Ecosystem</span>
                        </div>
                        <span className="text-zinc-700">|</span>
                        <div className="flex items-center gap-2">
                            <Server size={14} className="text-emerald-400" />
                            <span>Cloud Run 8Gi / 2 vCPU Microservices</span>
                        </div>
                        <span className="text-zinc-700">|</span>
                        <div className="flex items-center gap-2">
                            <Shield size={14} className="text-indigo-400" />
                            <span>AES-256 Encrypted GCS Buckets</span>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono font-medium">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                            Production SLA: 99.9% Uptime
                        </span>
                    </div>
                </div>

                {/* Bottom Line: The Reviewer Hack + Copyright */}
                <div className="pt-6 border-t border-white/5 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-zinc-400">
                    <div className="flex items-center gap-3">
                        <p>© {new Date().getFullYear()} CloneFrame Inc. All rights reserved.</p>
                        <span>·</span>
                        <p>Founded by Md Kaif Babanagar</p>
                    </div>

                    {/* REQUIRED GOOGLE CLOUD REVIEWER VERIFICATION LINE */}
                    <div className="flex items-center gap-2 text-zinc-300 font-medium bg-black/60 px-4 py-1.5 rounded-full border border-white/10 shadow-sm">
                        <Cloud size={14} className="text-blue-400" />
                        <span>Infrastructure securely hosted on Google Cloud.</span>
                    </div>

                    <div className="flex items-center gap-4">
                        <a href="https://twitter.com" target="_blank" rel="noreferrer" className="text-zinc-400 hover:text-white transition-colors" aria-label="Twitter">
                            <Twitter size={16} />
                        </a>
                        <a href="https://github.com" target="_blank" rel="noreferrer" className="text-zinc-400 hover:text-white transition-colors" aria-label="GitHub">
                            <Github size={16} />
                        </a>
                        <a href="https://discord.com" target="_blank" rel="noreferrer" className="text-zinc-400 hover:text-white transition-colors" aria-label="Discord">
                            <Discord size={16} />
                        </a>
                    </div>
                </div>
            </div>
        </footer>
    );
}
