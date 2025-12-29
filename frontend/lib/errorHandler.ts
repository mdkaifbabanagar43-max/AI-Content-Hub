import { toast } from 'sonner';

export const handleAppError = (error: any, refundCallback?: () => void) => {
    // 1. Log for developer
    console.error("🔥 App Error:", error);

    // 2. Determine Friendly Message
    let message = "Something unexpected happened. We are looking into it.";
    let description = "";

    // Parse Error Message
    const errorString = error?.message || error?.toString() || "";
    const errorCode = error?.status || error?.code;

    if (errorString.includes('Network Error') || errorString.includes('Failed to fetch')) {
        message = "Connection lost.";
        description = "Please check your internet connection.";
    } else if (errorCode === 401 || errorCode === 403 || errorString.includes('401') || errorString.includes('403')) {
        message = "Session expired.";
        description = "Please log in again.";
    } else if (errorCode === 429 || errorString.includes('429')) {
        message = "You are going too fast!";
        description = "Please wait a moment before trying again.";
    } else if (errorCode === 500 || errorString.includes('500')) {
        message = "Server Traffic High";
        description = "Our AI servers are experiencing heavy traffic. We are fixing it!";
    }

    // 3. Trigger Refund
    if (refundCallback) {
        try {
            refundCallback();
            description += " (Credits have been refunded)";
        } catch (e) {
            console.error("Refund failed during error handling:", e);
        }
    }

    // 4. Show Toast
    // Using sonner: toast.error(message, { description })
    // Or if standard hot-toast: toast.error(message)
    // Assuming UI library pattern. If sonner isn't installed, we might need a fallback.
    // Given the "Stealth AI" design request, we'll try to style it or rely on global styles.
    toast.error(message, {
        description: description,
        style: {
            background: '#0a0a0a',
            border: '1px solid #7f1d1d', // Red border
            color: '#fff',
        },
        className: 'my-toast-class'
    });
};
