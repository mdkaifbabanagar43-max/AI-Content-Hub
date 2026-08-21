"use client";

import React, { useState } from 'react';
import { X, CreditCard, Loader2, CheckCircle, ShieldCheck } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface MockCheckoutProps {
    isOpen: boolean;
    planName: string;
    price: string;
    onSuccess: (planName: string) => void;
    onClose: () => void;
}

export default function MockCheckout({ isOpen, planName, price, onSuccess, onClose }: MockCheckoutProps) {
    const [isLoading, setIsLoading] = useState(false);
    const [step, setStep] = useState<'form' | 'success'>('form');

    if (!isOpen) return null;

    const handleConfirm = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);

        // Simulate network delay
        setTimeout(() => {
            setIsLoading(false);
            setStep('success');

            // Auto close after success
            setTimeout(() => {
                onSuccess(planName.toLowerCase()); // Normalize plan name ID
            }, 1000);
        }, 2000);
    };

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                {/* Backdrop */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={onClose}
                    className="absolute inset-0 bg-black/80 backdrop-blur-sm"
                />

                {/* Modal */}
                <motion.div
                    initial={{ scale: 0.95, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.95, opacity: 0 }}
                    className="relative w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden"
                >
                    {/* Header */}
                    <div className="flex items-center justify-between p-6 border-b border-zinc-800 bg-zinc-950/50">
                        <div className="flex items-center gap-2">
                            <ShieldCheck className="text-green-500" size={20} />
                            <h2 className="text-lg font-bold text-white">Secure Checkout</h2>
                        </div>
                        <button onClick={onClose} className="text-zinc-500 hover:text-white transition-colors">
                            <X size={20} />
                        </button>
                    </div>

                    <div className="p-6">
                        {step === 'form' ? (
                            <form onSubmit={handleConfirm} className="space-y-6">
                                {/* Plan Summary */}
                                <div className="bg-zinc-800/50 rounded-xl p-4 flex items-center justify-between border border-zinc-700/50">
                                    <div>
                                        <p className="text-xs text-zinc-400 uppercase font-bold tracking-wider">Upgrading to</p>
                                        <h3 className="text-xl font-bold text-white">{planName}</h3>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-2xl font-bold text-white">{price}</p>
                                        <p className="text-xs text-zinc-400">/month</p>
                                    </div>
                                </div>

                                {/* Fake Fields */}
                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-xs font-bold text-zinc-500 mb-1">CARD NUMBER</label>
                                        <div className="relative">
                                            <input
                                                type="text"
                                                placeholder="0000 0000 0000 0000"
                                                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-3 pl-10 text-white outline-none focus:border-green-500 transition-colors font-mono"
                                                required
                                            />
                                            <CreditCard className="absolute left-3 top-3.5 text-zinc-500" size={16} />
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-xs font-bold text-zinc-500 mb-1">EXPIRY</label>
                                            <input
                                                type="text"
                                                placeholder="MM/YY"
                                                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-green-500 transition-colors font-mono"
                                                required
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-bold text-zinc-500 mb-1">CVC</label>
                                            <input
                                                type="text"
                                                placeholder="123"
                                                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-green-500 transition-colors font-mono"
                                                required
                                            />
                                        </div>
                                    </div>
                                </div>

                                {/* Action */}
                                <button
                                    type="submit"
                                    disabled={isLoading}
                                    className="w-full bg-green-600 hover:bg-green-500 text-white font-bold py-4 rounded-xl shadow-lg shadow-green-900/20 transition-all active:scale-[0.98] disabled:opacity-70 disabled:cursor-wait flex items-center justify-center gap-2"
                                >
                                    {isLoading ? (
                                        <>
                                            <Loader2 className="animate-spin" size={20} /> Processing...
                                        </>
                                    ) : (
                                        <>Confirm Payment</>
                                    )}
                                </button>

                                <p className="text-center text-xs text-zinc-500">
                                    <span className="bg-yellow-500/10 text-yellow-500 px-2 py-0.5 rounded">TEST MODE</span> No real money will be charged.
                                </p>
                            </form>
                        ) : (
                            <div className="py-10 text-center space-y-4">
                                <motion.div
                                    initial={{ scale: 0 }}
                                    animate={{ scale: 1 }}
                                    className="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center mx-auto shadow-xl shadow-green-500/30"
                                >
                                    <CheckCircle size={40} className="text-white" />
                                </motion.div>
                                <div>
                                    <h3 className="text-2xl font-bold text-white">Payment Successful!</h3>
                                    <p className="text-zinc-400 mt-2">Welcome to the {planName} plan.</p>
                                </div>
                            </div>
                        )}
                    </div>
                </motion.div>
            </div>
        </AnimatePresence>
    );
}
