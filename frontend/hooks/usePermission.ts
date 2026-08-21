import { usePlan } from '../context/PlanContext';

export const PLAN_FEATURES = {
    free: {
        allowed_langs: ['es', 'fr', 'hi'],
        hinglish: false,
        repurposer_modes: ['center_crop'],
        voice_cloning: false,
        resolution: '720p',
        all_presets: false
    },
    starter: {
        allowed_langs: ['es', 'fr', 'hi'],
        hinglish: false,
        repurposer_modes: ['center_crop'], // Only basic crop
        voice_cloning: false,
        resolution: '720p',
        all_presets: false
    },
    pro: {
        allowed_langs: ['es', 'fr', 'hi', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh'], // Top 10
        hinglish: false,
        repurposer_modes: ['center_crop', 'smart_face_tracking'],
        voice_cloning: false,
        resolution: '1080p',
        all_presets: false
    },
    creator: {
        allowed_langs: ['all'], // 30+
        hinglish: true,
        repurposer_modes: ['center_crop', 'smart_face_tracking', 'podcast_stack', 'hormozi_captions'],
        voice_cloning: true,
        resolution: '4k',
        all_presets: true
    },
    agency: {
        allowed_langs: ['all'],
        hinglish: true,
        repurposer_modes: ['all'],
        voice_cloning: true,
        resolution: '4k',
        all_presets: true
    }
};

export type FeatureKey = keyof typeof PLAN_FEATURES.starter;

export const usePermission = () => {
    const { userPlan } = usePlan();

    // Helper to normalize plan (fallback to starter)
    const currentPlanFeatures = PLAN_FEATURES[userPlan] || PLAN_FEATURES.starter;

    const canUse = (feature: FeatureKey, value?: string): boolean => {
        const featureSetting = currentPlanFeatures[feature];

        // Boolean check
        if (typeof featureSetting === 'boolean') {
            return featureSetting;
        }

        // Array check (if value is provided)
        if (Array.isArray(featureSetting) && value) {
            if (featureSetting.includes('all')) return true;
            return featureSetting.includes(value);
        }

        // Return true if value not needed (just checking existence/setting)
        return !!featureSetting;
    };

    return { canUse, userPlan };
};

// Backwards compatibility for existing hook calls (canAccess) 
// - mapping old keywords to new logic where possible
export const usePermissionCompatible = () => {
    const { canUse, userPlan } = usePermission();

    // We need to access currentPlanFeatures inside here, let's just re-derive
    const currentPlanFeatures = PLAN_FEATURES[userPlan] || PLAN_FEATURES.starter;

    // Legacy mapper
    const canAccess = (feature: string) => {
        if (feature === 'podcast_stack') return canUse('repurposer_modes', 'podcast_stack');
        if (feature === 'hormozi_captions') return canUse('repurposer_modes', 'hormozi_captions');
        if (feature === 'voice_cloning') return canUse('voice_cloning');
        if (feature === 'smart_face_tracking') return canUse('repurposer_modes', 'smart_face_tracking');
        if (feature === '4k') return currentPlanFeatures.resolution === '4k';
        // For other features like '720p', '1080p', 'center_crop', 'all' (from old PLAN_FEATURES)
        // 'center_crop' is always true for all plans in new logic, so no specific check needed.
        // '720p' and '1080p' are implicitly handled by resolution check if needed, but not directly mapped.
        // 'all' was a special case for agency, which is now handled by the detailed object.
        return false;
    };

    return { canAccess, userPlan };
}
