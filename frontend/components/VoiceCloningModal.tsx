'use client';

import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, UploadCloud, Mic, CheckCircle2, FileAudio } from 'lucide-react';
import { useDropzone } from 'react-dropzone';
import { cn } from '@/lib/utils';

interface VoiceCloningModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: (voiceId: string) => void;
    userId: string;
}

export default function VoiceCloningModal({ isOpen, onClose, onSuccess, userId }: VoiceCloningModalProps) {
    const [step, setStep] = useState<'upload' | 'processing' | 'success'>('upload');
    const [file, setFile] = useState<File | null>(null);

    const onDrop = useCallback((acceptedFiles: File[]) => {
        if (acceptedFiles?.[0]) {
            setFile(acceptedFiles[0]);
        }
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'audio/*': ['.mp3', '.wav', '.m4a'] },
        maxFiles: 1
    });

    const handleClone = async () => {
        if (!file) return;
        setStep('processing');

        // Mock API Call
        try {
            // Simulate upload delay
            await new Promise(resolve => setTimeout(resolve, 3000));

            // In a real app, we'd append FormData here
            // const formData = new FormData();
            // formData.append('file', file);
            // formData.append('user_id', userId);
            // await fetch(`${API_BASE_URL}/clone-voice`, { ... });

            setStep('success');
            // Mock Voice ID
            setTimeout(() => {
                onSuccess('cloned_voice_v1');
                onClose();
            }, 1500);

        } catch (error) {
            console.error("Cloning failed", error);
            setStep('upload'); // Reset on error
        }
    };

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="relative w-full max-w-lg bg-zinc-900 border border-zinc-800 rounded-3xl overflow-hidden shadow-2xl"
                >
                    {/* Close Button */}
                    <button
                        onClick={onClose}
                        className="absolute top-4 right-4 p-2 text-zinc-500 hover:text-white transition-colors z-10"
                    >
                        <X size={20} />
                    </button>

                    <div className="p-8">
                        <div className="text-center mb-8">
                            <h2 className="text-2xl font-bold text-white mb-2">Clone Your Voice</h2>
                            <p className="text-zinc-400 text-sm">
                                Create a lifelike AI replica of your voice for instant text-to-speech.
                            </p>
                        </div>

                        {step === 'upload' && (
                            <div className="space-y-6">
                                <div
                                    {...getRootProps()}
                                    className={cn(
                                        "border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all",
                                        isDragActive ? "border-cyan-500 bg-cyan-500/10" : "border-zinc-700 hover:border-zinc-500 hover:bg-zinc-800/50",
                                        file ? "border-green-500/50 bg-green-500/5" : ""
                                    )}
                                >
                                    <input {...getInputProps()} />
                                    {file ? (
                                        <div className="flex flex-col items-center animate-in zoom-in-50">
                                            <div className="w-16 h-16 bg-green-500/20 text-green-500 rounded-full flex items-center justify-center mb-4">
                                                <FileAudio size={32} />
                                            </div>
                                            <p className="font-bold text-white">{file.name}</p>
                                            <p className="text-xs text-zinc-500 mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                                        </div>
                                    ) : (
                                        <div className="flex flex-col items-center">
                                            <div className="w-16 h-16 bg-zinc-800 text-zinc-400 rounded-full flex items-center justify-center mb-4 group-hover:bg-zinc-700 transition-colors">
                                                <UploadCloud size={32} />
                                            </div>
                                            <p className="font-bold text-zinc-300">Click to upload or drag & drop</p>
                                            <p className="text-xs text-zinc-500 mt-2">MP3, WAV, M4A (Min 1 min of clear audio)</p>
                                        </div>
                                    )}
                                </div>

                                <button
                                    onClick={handleClone}
                                    disabled={!file}
                                    className="w-full py-4 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-bold text-lg rounded-xl shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    Start Cloning Process
                                </button>
                            </div>
                        )}

                        {step === 'processing' && (
                            <div className="text-center py-10 space-y-6">
                                <div className="relative mx-auto w-24 h-24">
                                    <div className="absolute inset-0 border-4 border-cyan-500/30 rounded-full"></div>
                                    <div className="absolute inset-0 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
                                    <div className="absolute inset-0 flex items-center justify-center">
                                        <Mic className="text-white animate-pulse" size={32} />
                                    </div>
                                </div>
                                <div>
                                    <h3 className="text-xl font-bold text-white mb-2">Analyzing Voice Patterns</h3>
                                    <p className="text-zinc-500 text-sm">Extracting tone, pitch, and cadence...</p>
                                </div>
                            </div>
                        )}

                        {step === 'success' && (
                            <div className="text-center py-10 space-y-6">
                                <div className="mx-auto w-24 h-24 bg-green-500/20 text-green-500 rounded-full flex items-center justify-center animate-in zoom-in">
                                    <CheckCircle2 size={48} />
                                </div>
                                <div>
                                    <h3 className="text-xl font-bold text-white mb-2">Voice Cloned Successfully!</h3>
                                    <p className="text-zinc-500 text-sm">Your custom voice model is ready to use.</p>
                                </div>
                            </div>
                        )}
                    </div>
                </motion.div>
            </div>
        </AnimatePresence>
    );
}
