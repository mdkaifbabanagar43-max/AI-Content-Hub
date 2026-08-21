'use client';

import posthog from 'posthog-js';
import { PostHogProvider as PHProvider } from 'posthog-js/react';
import { useEffect } from 'react';

// PostHog Configuration
// Sign up at https://posthog.com for free tier
const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY || '';
const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://app.posthog.com';

export function PostHogProvider({ children }: { children: React.ReactNode }) {
    useEffect(() => {
        if (POSTHOG_KEY && typeof window !== 'undefined') {
            posthog.init(POSTHOG_KEY, {
                api_host: POSTHOG_HOST,
                capture_pageview: true,
                capture_pageleave: true,
                persistence: 'localStorage',
            });
        }
    }, []);

    // If no key configured, just render children without tracking
    if (!POSTHOG_KEY) {
        return <>{children}</>;
    }

    return <PHProvider client={posthog}>{children}</PHProvider>;
}

// Analytics helper functions
export const analytics = {
    // Track user signup
    trackSignup: (userId: string, email: string) => {
        if (typeof window !== 'undefined' && POSTHOG_KEY) {
            posthog.identify(userId, { email });
            posthog.capture('user_signed_up', { email });
        }
    },

    // Track video export
    trackVideoExport: (feature: string, plan: string, credits_used: number) => {
        if (typeof window !== 'undefined' && POSTHOG_KEY) {
            posthog.capture('video_exported', { feature, plan, credits_used });
        }
    },

    // Track feature usage
    trackFeatureUsed: (feature: string) => {
        if (typeof window !== 'undefined' && POSTHOG_KEY) {
            posthog.capture('feature_used', { feature });
        }
    },

    // Track credit depletion
    trackCreditsDepleted: (plan: string) => {
        if (typeof window !== 'undefined' && POSTHOG_KEY) {
            posthog.capture('credits_depleted', { plan });
        }
    },

    // Track plan upgrade
    trackPlanUpgrade: (from_plan: string, to_plan: string) => {
        if (typeof window !== 'undefined' && POSTHOG_KEY) {
            posthog.capture('plan_upgraded', { from_plan, to_plan });
        }
    },
};
