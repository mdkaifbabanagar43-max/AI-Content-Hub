'use client';

import React, { useState } from 'react';
import { Chrome, ArrowRight, ShieldCheck, Lock, Eye, EyeOff, CheckCircle2, Zap } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';

interface AuthPageProps {
    mode: 'login' | 'signup';
}

export default function AuthPage({ mode }: AuthPageProps) {
    const { loginWithGoogle } = useAuth();
    const router = useRouter();
    const [isLoggingIn, setIsLoggingIn] = useState(false);
    const [showPassword, setShowPassword] = useState(false);

    const [currentMode, setCurrentMode] = useState<'login' | 'signup'>(mode);

    // Sync prop with state if it changes (optional, but good practice)
    React.useEffect(() => {
        setCurrentMode(mode);
    }, [mode]);

    const toggleMode = () => {
        setCurrentMode(prev => prev === 'login' ? 'signup' : 'login');
    };

    // Mock Email Login handling for UI demo
    const handleEmailAuth = (e: React.FormEvent) => {
        e.preventDefault();
        // In a real app, this would call loginWithEmail(email, password)
        alert("Email auth is currently a placeholder. Please use Google Login for this demo.");
    };

    const handleGoogleLogin = async () => {
        if (isLoggingIn) return;
        setIsLoggingIn(true);
        try {
            await loginWithGoogle();
            router.push('/');
        } catch (error: any) {
            console.error("Auth failed", error);
            if (error.code !== 'auth/popup-closed-by-user' && error.code !== 'auth/cancelled-popup-request') {
                alert("Login Failed: " + error.message);
            }
        } finally {
            setIsLoggingIn(false);
        }
    };

    return (
        <div className="min-h-screen flex flex-col md:flex-row bg-[#030303] text-white font-sans selection:bg-indigo-500/30">

            {/* --- LEFT SIDE: VALUE (Desktop Only / Top on Mobile optimized) --- */}
            <div className="w-full md:w-5/12 lg:w-1/2 relative overflow-hidden bg-[#050505] flex flex-col justify-between p-8 md:p-16 border-b md:border-b-0 md:border-r border-white/5">
                {/* Atmosphere */}
                <div className="absolute inset-0 z-0 pointer-events-none">
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-600/10 blur-[120px] rounded-full"></div>
                    <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff_1px,transparent_1px),linear-gradient(to_bottom,#ffffff_1px,transparent_1px)] bg-[size:40px_40px] opacity-[0.02]"></div>
                </div>

                <div className="relative z-10 hidden md:block">
                    <div className="bg-white/5 border border-white/10 rounded-xl p-3 inline-flex mb-8 backdrop-blur-md">
                        <Zap size={24} className="text-indigo-400" />
                    </div>
                </div>

                <div className="relative z-10 max-w-lg mb-8 md:mb-0">
                    <h1 className="text-3xl md:text-5xl font-[800] tracking-tight leading-tight mb-6">
                        Create content faster. <br />
                        <span className="text-zinc-500">Let AI handle the hard part.</span>
                    </h1>
                    <ul className="hidden md:block space-y-4 text-zinc-400 font-medium">
                        <li className="flex items-center gap-3">
                            <CheckCircle2 size={20} className="text-indigo-500" />
                            <span>Viral scripts in seconds</span>
                        </li>
                        <li className="flex items-center gap-3">
                            <CheckCircle2 size={20} className="text-indigo-500" />
                            <span>Ultra-realistic voice cloning</span>
                        </li>
                        <li className="flex items-center gap-3">
                            <CheckCircle2 size={20} className="text-indigo-500" />
                            <span>Bank-level security</span>
                        </li>
                    </ul>
                </div>

                <div className="hidden md:block relative z-10 text-zinc-600 text-sm font-mono">
                    &copy; 2024 AI Video SaaS. All rights reserved.
                </div>
            </div>

            {/* --- RIGHT SIDE: FORM --- */}
            <div className="flex-1 flex flex-col justify-center px-6 py-12 md:p-16 bg-[#030303] relative">
                <div className="w-full max-w-md mx-auto">

                    {/* Header for Mobile/Form Context */}
                    <div className="mb-10 text-center md:text-left">
                        <h2 className="text-3xl font-bold text-white mb-2">{currentMode === 'login' ? 'Welcome Back' : 'Get Started Free'}</h2>
                        <p className="text-zinc-400">Enter your details to access the studio.</p>
                    </div>

                    {/* Main Form Content or Loading Spinner */}
                    {isLoggingIn ? (
                        <div className="flex flex-col items-center justify-center py-20 bg-zinc-900/20 rounded-3xl border border-white/5 animate-in fade-in duration-500">
                            <div className="relative">
                                <div className="w-16 h-16 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mb-6"></div>
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <Zap size={20} className="text-white animate-pulse" />
                                </div>
                            </div>
                            <p className="text-zinc-300 font-medium animate-pulse text-lg">Initialising Mission Control...</p>
                            <p className="text-zinc-500 text-sm mt-2">Securing connection</p>
                        </div>
                    ) : (
                        <div className="space-y-6">

                            {/* Social Login (Primary) */}
                            <button
                                onClick={handleGoogleLogin}
                                className="w-full h-14 bg-white text-black font-bold text-lg rounded-2xl flex items-center justify-center gap-3 hover:bg-zinc-200 transition-all transform active:scale-[0.98] shadow-lg shadow-indigo-500/5 group"
                            >
                                <Chrome size={22} className="group-hover:text-indigo-600 transition-colors" />
                                <span>Continue with Google</span>
                            </button>

                            <div className="flex items-center gap-2 justify-center text-xs text-zinc-500 font-medium">
                                <ShieldCheck size={14} />
                                <span>We never post without your permission.</span>
                            </div>

                            {/* Divider */}
                            <div className="relative py-4">
                                <div className="absolute inset-0 flex items-center">
                                    <span className="w-full border-t border-white/10"></span>
                                </div>
                                <div className="relative flex justify-center text-xs uppercase">
                                    <span className="bg-[#030303] px-3 text-zinc-500 font-mono tracking-widest">Or via email</span>
                                </div>
                            </div>

                            {/* Email Form */}
                            <form onSubmit={handleEmailAuth} className="space-y-5">
                                <div className="space-y-1.5">
                                    <label className="text-sm font-bold text-zinc-400 ml-1">Email Address</label>
                                    <input
                                        type="email"
                                        placeholder="name@work.com"
                                        className="w-full h-14 bg-zinc-900/50 border border-white/10 rounded-2xl px-5 text-white placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all text-base"
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <div className="flex justify-between items-center ml-1">
                                        <label className="text-sm font-bold text-zinc-400">Password</label>
                                        {currentMode === 'login' && <a href="#" className="text-xs text-indigo-400 hover:text-indigo-300">Forgot Password?</a>}
                                    </div>
                                    <div className="relative">
                                        <input
                                            type={showPassword ? "text" : "password"}
                                            placeholder="••••••••"
                                            className="w-full h-14 bg-zinc-900/50 border border-white/10 rounded-2xl px-5 text-white placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all text-base pr-12"
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowPassword(!showPassword)}
                                            className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors p-1"
                                        >
                                            {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                                        </button>
                                    </div>
                                </div>

                                <button
                                    type="submit"
                                    className="w-full h-14 bg-zinc-800 text-zinc-200 font-bold text-lg rounded-2xl flex items-center justify-center gap-2 hover:bg-zinc-700 transition-colors border border-white/5"
                                >
                                    {currentMode === 'login' ? 'Sign In with Email' : 'Create Account'} <ArrowRight size={18} />
                                </button>
                            </form>

                            {/* Login/Signup Toggle */}
                            <div className="text-center pt-2">
                                <button
                                    onClick={toggleMode}
                                    className="text-sm text-zinc-400 hover:text-white transition-colors"
                                >
                                    {currentMode === 'signup' ? "Already have an account? " : "Don't have an account? "}
                                    <span className="font-bold underline Decoration-indigo-500/50 hover:decoration-indigo-400">
                                        {currentMode === 'signup' ? "Log in" : "Sign up"}
                                    </span>
                                </button>
                            </div>

                            {/* Trust Footer */}
                            <div className="pt-6 border-t border-white/5 flex flex-col items-center justify-center gap-4 text-zinc-600 text-xs font-medium">
                                <div className="flex items-center gap-6">
                                    <div className="flex items-center gap-1.5">
                                        <Lock size={12} />
                                        <span>Secure Login</span>
                                    </div>
                                    <div className="w-1 h-1 bg-zinc-800 rounded-full"></div>
                                    <div>No spam. Ever.</div>
                                </div>
                                <p className="text-zinc-700">
                                    By clicking continue, you agree to our <a href="#" className="hover:text-zinc-500 underline">Terms</a> and <a href="#" className="hover:text-zinc-500 underline">Privacy Policy</a>.
                                </p>
                            </div>

                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

