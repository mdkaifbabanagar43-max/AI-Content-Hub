'use client';

import React from 'react';
import Link from 'next/link';
import { Twitter, Github, Disc as Discord } from 'lucide-react';

export default function Footer() {
    return (
        <footer className="relative z-10 bg-[#050505] border-t border-white/5 pt-20 pb-10">
            <div className="w-full max-w-[1800px] mx-auto px-6 md:px-12">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-16">
                    {/* Col 1: Brand */}
                    <div className="space-y-4">
                        <h3 className="text-3xl md:text-4xl font-bold">
                            Clone<span className="bg-gradient-to-r from-pink-500 to-purple-600 bg-clip-text text-transparent">Frame</span>
                        </h3>
                        <p className="text-zinc-400 text-lg leading-relaxed">
                            The shortcut to viral content. Turn any idea into scroll-stopping videos in minutes.
                        </p>
                    </div>

                    {/* Col 2: Product */}
                    <div>
                        <h4 className="text-white text-xl font-bold mb-6">Product</h4>
                        <ul className="space-y-3">
                            {['Features', 'Roadmap', 'Changelog', 'Pricing'].map(item => (
                                <li key={item}>
                                    <a href="#" className="text-zinc-400 hover:text-blue-400 text-lg transition-colors">{item}</a>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* Col 3: Company */}
                    <div>
                        <h4 className="text-white text-xl font-bold mb-6">Company</h4>
                        <ul className="space-y-3">
                            <li key="about">
                                <Link href="/about" className="text-zinc-400 hover:text-blue-400 text-lg transition-colors">About Us</Link>
                            </li>
                            <li key="blog">
                                <a href="#" className="text-zinc-400 hover:text-blue-400 text-lg transition-colors">Blog</a>
                            </li>
                            <li key="careers">
                                <a href="#" className="text-zinc-400 hover:text-blue-400 text-lg transition-colors">Careers</a>
                            </li>
                        </ul>
                    </div>

                    {/* Col 4: Legal & Support */}
                    <div>
                        <h4 className="text-white text-xl font-bold mb-6">Legal & Support</h4>
                        <ul className="space-y-3">
                            {[
                                { name: 'Refund Policy', href: '/refund-policy' },
                                { name: 'Privacy Policy', href: '/privacy' },
                                { name: 'Terms of Service', href: '/terms' },
                                { name: 'Contact Us', href: '/contact' }
                            ].map(item => (
                                <li key={item.name}>
                                    <Link href={item.href} className="text-zinc-400 hover:text-blue-400 text-lg transition-colors">{item.name}</Link>
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>

                {/* Bottom Bar */}
                <div className="border-t border-white/5 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
                    <p className="text-zinc-500 text-lg">
                        © {new Date().getFullYear()} CloneFrame. All rights reserved.
                    </p>

                    <div className="flex items-center gap-6">
                        <a href="#" className="text-zinc-500 hover:text-blue-500 transition-colors">
                            <Twitter size={20} />
                        </a>
                        <a href="#" className="text-zinc-500 hover:text-white transition-colors">
                            <Github size={20} />
                        </a>
                        <a href="#" className="text-zinc-500 hover:text-indigo-500 transition-colors">
                            <Discord size={20} />
                        </a>
                    </div>
                </div>
            </div>
        </footer>
    );
}
