import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "../context/AuthContext";
import { PlanProvider } from "../context/PlanContext";
import { PostHogProvider } from "../lib/analytics";
import { Toaster } from 'sonner';

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CloneFrame - AI Video Creation & Cloning",
  description: "Clone the visual DNA, characters, story structure and style — then create a new story. AI scripts, voiceovers, and auto-edited shorts.",
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
