export interface Voice {
    id: string;
    label: string;
    gender: 'Male' | 'Female';
    provider?: 'rating' | 'elevenlabs'; // Default to 'rating' (which maps to google in backend logic usually) or explicit 'google'
}

export interface Language {
    id: string; // e.g., 'en-US'
    label: string; // e.g., 'English (US)'
    flag: string; // e.g., '🇺🇸'
    voices: Voice[];
}

export const LANGUAGES: Language[] = [
    {
        id: 'en-US',
        label: 'English (US)',
        flag: '🇺🇸',
        voices: [
            // Premium Journey Voices (Ultra HD)
            { id: 'en-US-Journey-D', label: 'Marcus (Deep & Warm) 🌟', gender: 'Male' },
            { id: 'en-US-Journey-F', label: 'Holly (Soft & Calm) 🌟', gender: 'Female' },
            { id: 'en-US-Journey-O', label: 'Liam (Storyteller) 🌟', gender: 'Male' },

            // Studio Voices (Pro)
            { id: 'en-US-Studio-M', label: 'James (Professional) 🎙️', gender: 'Male' },
            { id: 'en-US-Studio-O', label: 'Emma (Narrator) 🎙️', gender: 'Female' },

            // Standard Neural2
            { id: 'en-US-Neural2-A', label: 'David (Professional)', gender: 'Male' },
            { id: 'en-US-Neural2-C', label: 'Sarah (Professional)', gender: 'Female' },
            { id: 'en-US-News-N', label: 'Michael (News Anchor)', gender: 'Male' },
        ]
    },
    {
        id: 'en-GB',
        label: 'English (UK)',
        flag: '🇬🇧',
        voices: [
            // Premium Journey Voices
            { id: 'en-GB-Journey-D', label: 'Arthur (Deep British) 🌟', gender: 'Male' },
            { id: 'en-GB-Journey-F', label: 'Olivia (Warm British) 🌟', gender: 'Female' },

            { id: 'en-GB-Neural2-B', label: 'George (Broadcast)', gender: 'Male' },
            { id: 'en-GB-Neural2-A', label: 'Emily (Formal)', gender: 'Female' },
            { id: 'en-GB-News-J', label: 'Sophia (News Anchor)', gender: 'Female' },
        ]
    },
    {
        id: 'es-ES',
        label: 'Spanish (Spain)',
        flag: '🇪🇸',
        voices: [
            { id: 'es-ES-Neural2-B', label: 'Mateo (Deep)', gender: 'Male' },
            { id: 'es-ES-Neural2-A', label: 'Sofia (Derived)', gender: 'Female' },
        ]
    },
    {
        id: 'es-US',
        label: 'Spanish (Latin Am)',
        flag: '🇲🇽',
        voices: [
            { id: 'es-US-Neural2-B', label: 'Alejandro (Friendly)', gender: 'Male' },
            { id: 'es-US-Neural2-A', label: 'Valentina (Professional)', gender: 'Female' },
            { id: 'es-US-Studio-B', label: 'Diego (Narrator)', gender: 'Male' },
        ]
    },
    {
        id: 'fr-FR',
        label: 'French',
        flag: '🇫🇷',
        voices: [
            { id: 'fr-FR-Neural2-B', label: 'Antoine (Deep)', gender: 'Male' },
            { id: 'fr-FR-Neural2-A', label: 'Marie (Elegant)', gender: 'Female' },
            { id: 'fr-FR-Studio-D', label: 'Louis (Narrator)', gender: 'Male' },
        ]
    },
    {
        id: 'de-DE',
        label: 'German',
        flag: '🇩🇪',
        voices: [
            { id: 'de-DE-Neural2-B', label: 'Hans (Professional)', gender: 'Male' },
            { id: 'de-DE-Neural2-C', label: 'Muller (Warm)', gender: 'Female' },
        ]
    },
    {
        id: 'it-IT',
        label: 'Italian',
        flag: '🇮🇹',
        voices: [
            { id: 'it-IT-Neural2-C', label: 'Marco (Confident)', gender: 'Male' },
            { id: 'it-IT-Neural2-A', label: 'Giulia (Bright)', gender: 'Female' },
        ]
    },
    {
        id: 'hi-IN',
        label: 'Hindi',
        flag: '🇮🇳',
        voices: [
            { id: 'hi-IN-Neural2-B', label: 'Arjun (Formal)', gender: 'Male' },
            { id: 'hi-IN-Neural2-A', label: 'Anjali (Soft)', gender: 'Female' },
        ]
    },
    {
        id: 'ja-JP',
        label: 'Japanese',
        flag: '🇯🇵',
        voices: [
            { id: 'ja-JP-Neural2-C', label: 'Ken (Deep)', gender: 'Male' },
            { id: 'ja-JP-Neural2-B', label: 'Sakura (Cute)', gender: 'Female' },
        ]
    },
    {
        id: 'pt-BR',
        label: 'Portuguese (BR)',
        flag: '🇧🇷',
        voices: [
            { id: 'pt-BR-Neural2-B', label: 'Thiago (Energetic)', gender: 'Male' },
            { id: 'pt-BR-Neural2-A', label: 'Camila (Professional)', gender: 'Female' },
        ]
    },
    // New Languages
    {
        id: 'zh-CN',
        label: 'Chinese (Mandarin)',
        flag: '🇨🇳',
        voices: [
            { id: 'zh-CN-Neural2-C', label: 'Wei (Deep)', gender: 'Male' },
            { id: 'zh-CN-Neural2-B', label: 'Li (Clear)', gender: 'Female' },
        ]
    },
    {
        id: 'ko-KR',
        label: 'Korean',
        flag: '🇰🇷',
        voices: [
            { id: 'ko-KR-Neural2-C', label: 'Min-jun (Deep)', gender: 'Male' },
            { id: 'ko-KR-Neural2-B', label: 'Ji-oo (Soft)', gender: 'Female' },
        ]
    },
    {
        id: 'ar-XA',
        label: 'Arabic',
        flag: '🇸🇦',
        voices: [
            { id: 'ar-XA-Neural2-B', label: 'Omar (Formal)', gender: 'Male' },
            { id: 'ar-XA-Neural2-A', label: 'Fatima (Soft)', gender: 'Female' },
        ]
    },
    {
        id: 'ru-RU',
        label: 'Russian',
        flag: '🇷🇺',
        voices: [
            { id: 'ru-RU-Neural2-D', label: 'Dmitry (Deep)', gender: 'Male' },
            { id: 'ru-RU-Neural2-C', label: 'Natalia (Clear)', gender: 'Female' },
        ]
    }
];
