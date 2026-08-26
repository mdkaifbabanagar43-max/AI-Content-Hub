"use client";

import React from 'react';
import { usePlan } from '../../context/PlanContext';
import { motion, AnimatePresence } from 'framer-motion';
import { Fuel } from 'lucide-react';

export default function LowBalanceModal() {
    const { showLowBalance, setShowLowBalance } = usePlan();

    if (!showLowBalance) return null;

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
                {/* Backdrop */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={() => setShowLowBalance(false)}
                    className="absolute inset-0 bg-black/80 backdrop-blur-sm"
                />

                {/* Modal */}
                <motion.div
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.9, opacity: 0 }}
                    className="relative w-full max-w-lg bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden max-h-[90vh] overflow-y-auto"
                >
                    <div className="p-8 text-center">
                        <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
                            <Fuel size={32} className="text-red-500" />
                        </div>
                        <h2 className="text-2xl font-bold text-white mb-2">Out of Fuel! ⛽</h2>
                        <p className="text-zinc-400 mb-8">
                            You've run out of credits to perform this action. Upgrade your plan to refuel instantly!
                        </p>

                        <div className="bg-zinc-950 rounded-xl p-4 border border-zinc-900 mb-6">
                            <div className="flex items-center justify-between text-sm mb-2">
                                <span className="text-zinc-500">Action Cost</span>
                                <span className="text-red-400 font-bold">- Credits</span>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-zinc-500">Current Balance</span>
                                <span className="text-white font-bold">0 Credits</span>
                            </div>
                        </div>

                        <button
                            onClick={() => {
                                setShowLowBalance(false);
                                window.location.href = '/?tab=pricing';
                            }}
                            className="w-full bg-gradient-to-r from-amber-500 to-orange-500 text-black font-bold py-3 rounded-xl hover:from-amber-400 hover:to-orange-400 transition-all"
                        >
                            Refuel Now
                        </button>
                        <button
                            onClick={() => setShowLowBalance(false)}
                            className="mt-4 text-sm text-zinc-500 hover:text-white transition-colors"
                        >
                            Maybe Later
                        </button>
                    </div>
                </motion.div>
            </div>
        </AnimatePresence>
    );
}
