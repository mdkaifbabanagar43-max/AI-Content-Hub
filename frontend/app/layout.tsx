import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "../context/AuthContext";
import { PlanProvider } from "../context/PlanContext";
import { PostHogProvider } from "../lib/analytics";
import { Toaster } from 'sonner';

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CloneFrame - Automated AI Video Pipeline for B2B Agencies",
  description: "Turn concepts into ready-to-publish short-form videos in seconds. Orchestrating Gemini 2.0, Veo, and ElevenLabs into one unified API.",
  keywords: [
    "AI Video Pipeline",
    "B2B Video Automation",
    "Gemini 2.0 Video",
    "Google Veo",
    "ElevenLabs API",
    "Social Media Marketing Agencies",
    "Google Cloud AI"
  ],
  authors: [{ name: "Md Kaif Babanagar" }],
  openGraph: {
    title: "CloneFrame - Automated AI Video Pipeline for B2B Agencies",
    description: "Turn concepts into ready-to-publish short-form videos in seconds. Orchestrating Gemini 2.0, Veo, and ElevenLabs into one unified API.",
    type: "website",
    siteName: "CloneFrame"
  }
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${inter.className} antialiased`}
        suppressHydrationWarning
      >
        <PostHogProvider>
          <AuthProvider>
            <PlanProvider>
              {children}
              <Toaster position="top-center" richColors theme="dark" />
            </PlanProvider>
          </AuthProvider>
        </PostHogProvider>
      </body>
    </html>
  );
}
