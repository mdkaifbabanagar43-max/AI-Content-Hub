'use client';

import React, { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { usePathname, useRouter } from 'next/navigation';

interface NavbarProps {
    onSignInClick: () => void;
}

export default function Navbar({ onSignInClick }: NavbarProps) {
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const pathname = usePathname();
    const router = useRouter();

    const links = [
        { name: 'Features', id: 'features' },
        { name: 'Showcase', id: 'showcase' }, // Added Showcase logic
        { name: 'Pricing', id: 'pricing' }
    ];

    const scrollToSection = (id: string) => {
        if (pathname === '/') {
            const element = document.getElementById(id);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth' });
            }
        } else {
            router.push(`/#${id}`);
        }
        setMobileMenuOpen(false);
    };

    return (
        <nav className="fixed top-0 left-0 right-0 z-50 bg-black/40 backdrop-blur-md border-b border-white/5 transition-all w-full">
            <div className="w-full max-w-[1800px] mx-auto px-6 md:px-12 h-16 flex items-center justify-between">
                {/* 1. Logo */}
                <div
                    className="flex items-center gap-2 cursor-pointer"
                    onClick={() => router.push('/')}
                >
                    <div className="text-2xl md:text-3xl font-bold tracking-tight text-white">
                        Clone<span className="text-transparent bg-clip-text bg-gradient-to-r from-pink-500 to-purple-500">Frame</span>
                    </div>
                </div>

                {/* 2. Desktop Links */}
                <div className="hidden md:flex items-center gap-8">
                    {links.map((link) => (
                        <button
                            key={link.name}
                            onClick={() => scrollToSection(link.id)}
                            className="text-[15px] font-[500] text-zinc-300 hover:text-white uppercase tracking-wide transition-colors"
                        >
                            {link.name}
                        </button>
                    ))}
                </div>

                {/* 3. Actions */}
                <div className="flex items-center gap-4">
                    <button
                        onClick={onSignInClick}
                        className="hidden md:block px-6 py-2.5 rounded-full text-[15px] font-[600] bg-white text-black hover:bg-zinc-200 transition-colors"
                    >
                        Get Started
                    </button>

                    {/* Mobile Menu Toggle */}
                    <button
                        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                        className="md:hidden text-zinc-400 hover:text-white"
                    >
                        {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
                    </button>
                </div>
            </div>

            {/* Mobile Menu */}
            <AnimatePresence>
                {mobileMenuOpen && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="md:hidden bg-black/90 border-b border-white/10 overflow-hidden backdrop-blur-xl"
                    >
                        <div className="px-6 py-8 flex flex-col gap-6">
                            {links.map((link) => (
                                <button
                                    key={link.name}
                                    onClick={() => scrollToSection(link.id)}
                                    className="text-lg font-medium text-zinc-400 hover:text-white text-left"
                                >
                                    {link.name}
                                </button>
                            ))}
                            <button
                                onClick={() => {
                                    onSignInClick();
                                    setMobileMenuOpen(false);
                                }}
                                className="w-full py-3 rounded-full font-bold bg-white text-black"
                            >
                                Get Started
                            </button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </nav>
    );
}
