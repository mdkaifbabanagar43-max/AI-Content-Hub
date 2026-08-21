import { initializeApp, getApps, getApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import { initializeFirestore } from "firebase/firestore";

const firebaseConfig = {
    apiKey: "AIzaSyDL4FHsHBa1XE9aUt1h5VyL4iogNOLvvUg",
    authDomain: "shortcutai-backend.firebaseapp.com",
    projectId: "shortcutai-backend",
    storageBucket: "shortcutai-backend.firebasestorage.app",
    messagingSenderId: "835818829937",
    appId: "1:835818829937:web:ff8f999bbc5cae590c03d0",
    measurementId: "G-7L2N9K3MP9",
};

// Initialize Firebase (Singleton pattern)
if (!firebaseConfig.apiKey) {
    console.error("🚨 CRITICAL: Firebase API Key is missing! Please check your .env.local file.");
    console.error("Values:", firebaseConfig);
}

const app = !getApps().length ? initializeApp(firebaseConfig) : getApp();
const auth = getAuth(app);
// Use long polling to avoid timeout issues in some environments
const db = initializeFirestore(app, {
    experimentalForceLongPolling: true,
});
// const db = getFirestore(app);
const googleProvider = new GoogleAuthProvider();

export { app, auth, db, googleProvider };
