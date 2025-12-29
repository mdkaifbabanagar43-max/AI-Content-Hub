"use client";

import React, { createContext, useContext, useState, ReactNode, useEffect } from 'react';
import { db } from '../lib/firebase';
import { API_BASE_URL } from '../lib/config';
import { doc, onSnapshot, setDoc } from 'firebase/firestore';
import { useAuth } from './AuthContext';

type PlanType = 'free' | 'starter' | 'pro' | 'creator' | 'agency';

interface PlanContextType {
    userPlan: PlanType;
    setUserPlan: (plan: PlanType) => void;
    credits: number;
    deductCredits: (amount: number) => boolean;
    refundCredits: (amount: number) => void;
    showLowBalance: boolean;
    setShowLowBalance: (show: boolean) => void;
    upgradePlan: (planId: string, creditAmount: number) => Promise<void>;
    capabilities: any;
}

const PlanContext = createContext<PlanContextType | undefined>(undefined);

export const PlanProvider = ({ children }: { children: ReactNode }) => {
    const { user } = useAuth();
    const [userPlan, setUserPlan] = useState<PlanType>('starter');
    const [credits, setCredits] = useState(15);
    const [showLowBalance, setShowLowBalance] = useState(false);
    const [capabilities, setCapabilities] = useState<any>(null); // New Source of Truth

    // Real-time Firestore Sync + API Capabilities Fetch
    useEffect(() => {
        if (!user) {
            setCredits((prev: number) => prev !== 0 ? 0 : prev);
            setCapabilities((prev: any) => prev !== null ? null : prev);
            return;
        }

        // 1. Sync Credits & Plan ID from Firestore
        const unsubscribe = onSnapshot(doc(db, "users", user.uid), (docSnapshot) => {
            if (docSnapshot.exists()) {
                const data = docSnapshot.data();
                setCredits(data.credits ?? 0);
                setUserPlan((data.plan as PlanType) || 'starter');
            } else {
                setCredits(15);
            }
        });

        // 2. Fetch Detailed Capabilities from Backend Source of Truth
        const fetchCapabilities = async () => {
            try {
                // We need the token here too. But user is available.
                const token = await user.getIdToken();
                // Use centralized configuration for API URL
                const res = await fetch(`${API_BASE_URL}/api/me`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.capabilities) {
                        setCapabilities(data.capabilities);
                    }
                }
            } catch (e) {
                console.error("PlanContext Cap fetch failed", e);
            }
        };
        fetchCapabilities();

        return () => unsubscribe();
    }, [user]);

    const upgradePlan = async (planId: string, creditAmount: number) => {
        if (!user) return;

        try {
            await setDoc(doc(db, "users", user.uid), {
                plan: planId,
                credits: creditAmount,
                updatedAt: new Date()
            }, { merge: true });

            // Local update (will be overwritten by snapshot, but good for instant feedback)
            setUserPlan(planId as PlanType);
            setCredits(creditAmount);
        } catch (e) {
            console.error("Failed to upgrade plan:", e);
        }
    };

    const deductCredits = (amount: number): boolean => {
        if (credits >= amount) {
            return true;
        } else {
            setShowLowBalance(true);
            return false;
        }
    };

    const refundCredits = (amount: number) => {
        // Optimistic Refund (Only affects local state until next sync, OR use a pending state)
        // Since we blindly sync from Firestore, a local setCredits might be overwritten.
        // But for the UI "Flash" effect, we can do it. 
        // Ideally, backend handles the refund logic if the transaction failed there. 
        // But if it failed mid-flight *after* deduction but *before* result, we might need a backend endpoint for refund?
        // OR, simply rely on the fact that if the backend transaction FAILED, it wouldn't have deducted?
        // Ah, the Requirement says: "If a generation fails... refundCredits... setCredits(prev + amount)".

        // LIMITATION: 'credits' is set by onSnapshot. Updating it manually might fight with the listener.
        // BUT, if the listener update hasn't come yet (e.g. backend failed TO deduct), then we are fine?
        // Wait, if backend successfully deducted, then we crash, we need to manually ADD back. 
        // To do that securely, we really should call a backend endpoint `/refund-error`.
        // BUT, Step 1 says: "Logic: setCredits(prev => prev + amount)". This implies CLIENT SIDE only for visual.
        // If the backend actually deducted, this client-side refund is fake and will disappear on refresh.
        // However, for the purpose of this task (User Request), I will follow instructions.
        setCredits(prev => prev + amount);
        // Note: Real app would need backend refund endpoint. We should probably implement valid persistent refund later.
    };

    return (
        <PlanContext.Provider value={{ userPlan, setUserPlan, credits, deductCredits, refundCredits, showLowBalance, setShowLowBalance, upgradePlan, capabilities }}>
            {children}
        </PlanContext.Provider>
    );
};

export const usePlan = () => {
    const context = useContext(PlanContext);
    if (!context) {
        throw new Error('usePlan must be used within a PlanProvider');
    }
    return context;
};
