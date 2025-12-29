import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle, Coins, Check, X, ShieldCheck } from 'lucide-react';
import { cn } from '@/lib/utils';

interface CreditConfirmationModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => void;
    estimatedCost: number;
    currentBalance: number;
    taskName?: string;
}

export default function CreditConfirmationModal({
    isOpen,
    onClose,
    onConfirm,
    estimatedCost,
    currentBalance,
    taskName = "Generate Video"
}: CreditConfirmationModalProps) {
    if (!isOpen) return null;

    const hasBalance = currentBalance >= estimatedCost;

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
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
                    initial={{ scale: 0.95, opacity: 0, y: 20 }}
                    animate={{ scale: 1, opacity: 1, y: 0 }}
                    exit={{ scale: 0.95, opacity: 0, y: 20 }}
                    onClick={(e) => e.stopPropagation()}
                    className="relative w-full max-w-md bg-zinc-950 border border-zinc-800 rounded-3xl overflow-hidden shadow-2xl"
                >
                    {/* Header */}
                    <div className="p-6 pb-0 flex items-center justify-center mb-6">
                        <div className={cn("w-16 h-16 rounded-full flex items-center justify-center border-4", hasBalance ? "bg-indigo-500/10 border-indigo-500/20 text-indigo-500" : "bg-red-500/10 border-red-500/20 text-red-500")}>
                            {hasBalance ? <ShieldCheck size={32} /> : <AlertCircle size={32} />}
                        </div>
                    </div>

                    <div className="text-center px-8 mb-8 space-y-2">
                        <h3 className="text-2xl font-black text-white">Confirm Credit Usage</h3>
                        <p className="text-zinc-400">
                            You are about to {taskName.toLowerCase()}.
                        </p>
                    </div>

                    {/* Stats */}
                    <div className="mx-6 p-4 rounded-xl bg-zinc-900/50 border border-zinc-800 mb-8 space-y-4">
                        <div className="flex justify-between items-center text-sm">
                            <span className="text-zinc-500">Estimated Cost</span>
                            <span className="font-bold text-white flex items-center gap-1">
                                <Coins size={14} className="text-yellow-500" />
                                {estimatedCost} Credits
                            </span>
                        </div>
                        <div className="h-px bg-zinc-800" />
                        <div className="flex justify-between items-center text-sm">
                            <span className="text-zinc-500">Current Balance</span>
                            <span className={cn("font-bold flex items-center gap-1", hasBalance ? "text-green-400" : "text-red-400")}>
                                <Coins size={14} className={hasBalance ? "text-green-500" : "text-red-500"} />
                                {currentBalance} Credits
                            </span>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="p-6 bg-zinc-900 border-t border-zinc-800 flex gap-3">
                        <button
                            onClick={onClose}
                            className="flex-1 py-3 rounded-xl font-bold bg-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-700 transition-colors"
                        >
                            Cancel
                        </button>

                        {hasBalance ? (
                            <button
                                onClick={onConfirm}
                                className="flex-1 py-3 rounded-xl font-bold bg-white text-black hover:bg-indigo-50 transition-colors flex items-center justify-center gap-2"
                            >
                                Confirm & Generate
                            </button>
                        ) : (
                            <button
                                onClick={() => window.location.href = '/pricing'}
                                className="flex-1 py-3 rounded-xl font-bold bg-indigo-600 text-white hover:bg-indigo-500 transition-colors flex items-center justify-center gap-2"
                            >
                                Get More Credits
                            </button>
                        )}
                    </div>
                </motion.div>
            </div>
        </AnimatePresence>
    );
}
