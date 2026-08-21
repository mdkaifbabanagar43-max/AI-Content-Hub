'use client';

import React, { useState } from 'react';
import { Chrome, ArrowRight, ShieldCheck, Lock, Eye, EyeOff, CheckCircle2, Zap, AlertCircle } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';

interface AuthPageProps {
    mode: 'login' | 'signup';
}

export default function AuthPage({ mode }: AuthPageProps) {
    const { loginWithGoogle, loginWithEmail, signupWithEmail } = useAuth();
    const router = useRouter();
    const [isLoggingIn, setIsLoggingIn] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [authError, setAuthError] = useState<string | null>(null);

    const [currentMode, setCurrentMode] = useState<'login' | 'signup'>(mode);

    // Sync prop with state if it changes (optional, but good practice)
    React.useEffect(() => {
        setCurrentMode(mode);
    }, [mode]);

    const toggleMode = () => {
        setCurrentMode(prev => prev === 'login' ? 'signup' : 'login');
    };

    // Email Login handling
    const handleEmailAuth = async (e: React.FormEvent) => {
        e.preventDefault();
        setAuthError(null);
        if (!email || !password) {
            setAuthError('Please enter your email and password.');
            return;
        }
        if (isLoggingIn) return;
        setIsLoggingIn(true);
        try {
            if (currentMode === 'login') {
                await loginWithEmail(email, password);
            } else {
                await signupWithEmail(email, password);
            }
            router.push('/');
        } catch (error: any) {
            console.error("Auth failed", error);
            // Firebase-friendly error messages
            const msg = error.code === 'auth/wrong-password' ? 'Incorrect password. Please try again.'
                : error.code === 'auth/user-not-found' ? 'No account found with this email.'
                : error.code === 'auth/email-already-in-use' ? 'This email is already registered.'
                : error.code === 'auth/weak-password' ? 'Password must be at least 6 characters.'
                : error.message || 'Authentication failed. Please try again.';
            setAuthError(msg);
        } finally {
            setIsLoggingIn(false);
        }
    };

    const handleGoogleLogin = async () => {
        if (isLoggingIn) return;
        setAuthError(null);
        setIsLoggingIn(true);
        try {
            await loginWithGoogle();
            router.push('/');
        } catch (error: any) {
            console.error("Auth failed", error);
            if (error.code !== 'auth/popup-closed-by-user' && error.code !== 'auth/cancelled-popup-request') {
                setAuthError(error.message || 'Google login failed. Please try again.');
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
                    &copy; 2026 CloneFrame. All rights reserved.
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
                            
                            <form onSubmit={handleEmailAuth} className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-zinc-400 mb-1">Email</label>
                                    <input 
                                        type="email" 
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="w-full bg-zinc-900/50 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                        placeholder="Enter your email"
                                        required
                                    />
                                </div>
                                <div className="relative">
                                    <label className="block text-sm font-medium text-zinc-400 mb-1">Password</label>
                                    <input 
                                        type={showPassword ? "text" : "password"} 
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="w-full bg-zinc-900/50 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                        placeholder="Enter your password"
                                        required
                                    />
                                    <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-4 top-9 text-zinc-400 hover:text-white">
                                        {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                    </button>
                                </div>
                                <button
                                    type="submit"
                                    disabled={isLoggingIn}
                                    className="w-full h-12 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold rounded-xl transition-colors"
                                >
                                    {currentMode === 'login' ? 'Login' : 'Sign Up'}
                                </button>

                                {/* Inline Error Display */}
                                {authError && (
                                    <div className="flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-sm text-red-400">
                                        <AlertCircle size={16} className="mt-0.5 shrink-0" />
                                        <span>{authError}</span>
                                    </div>
                                )}
                            </form>

                            <div className="flex items-center gap-4 my-6">
                                <div className="flex-1 h-px bg-white/10"></div>
                                <span className="text-xs text-zinc-500 uppercase tracking-wider font-bold">Or</span>
                                <div className="flex-1 h-px bg-white/10"></div>
                            </div>

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
                            
                            <div className="text-center text-sm text-zinc-400">
                                {currentMode === 'login' ? "Don't have an account? " : "Already have an account? "}
                                <button onClick={toggleMode} className="text-indigo-400 hover:text-indigo-300 font-bold">
                                    {currentMode === 'login' ? 'Sign Up' : 'Login'}
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

