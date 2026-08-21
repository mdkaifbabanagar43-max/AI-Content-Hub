import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
    steps: string[];
    layout?: React.ReactNode; // The Ghost Layout
}

export function LoadingState({ steps, layout }: LoadingStateProps) {
    const [currentStepIndex, setCurrentStepIndex] = useState(0);

    useEffect(() => {
        const interval = setInterval(() => {
            setCurrentStepIndex((prev) => (prev + 1) % steps.length);
        }, 3000); // Rotate every 3 seconds

        return () => clearInterval(interval);
    }, [steps.length]);

    return (
        <div className="relative w-full min-h-[400px]">
            {/* 1. THE GHOST UI (Background) */}
            <div className="opacity-50 pointer-events-none blur-[1px] transition-all duration-500">
                {layout}
            </div>

            {/* 2. THE FLOATING STATUS INDICATOR (Foreground) */}
            <div className="absolute inset-0 flex items-center justify-center z-20">
                <motion.div
                    initial={{ opacity: 0, scale: 0.9, y: 10 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    className="bg-zinc-950/80 backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-2xl flex flex-col items-center gap-4 max-w-sm text-center"
                >
                    <div className="relative">
                        <div className="absolute inset-0 bg-blue-500/20 blur-xl rounded-full"></div>
                        <Loader2 className="animate-spin text-blue-400 relative z-10" size={32} />
                    </div>

                    <div className="h-12 flex items-center justify-center overflow-hidden">
                        <AnimatePresence mode='wait'>
                            <motion.p
                                key={currentStepIndex}
                                initial={{ y: 20, opacity: 0 }}
                                animate={{ y: 0, opacity: 1 }}
                                exit={{ y: -20, opacity: 0 }}
                                transition={{ duration: 0.3 }}
                                className="text-lg font-bold text-white"
                            >
                                {steps[currentStepIndex]}
                            </motion.p>
                        </AnimatePresence>
                    </div>

                    <p className="text-xs text-zinc-500 font-mono uppercase tracking-widest">
                        Credits deducted on approval
                    </p>
                </motion.div>
            </div>
        </div>
    );
}
