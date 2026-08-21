'use client';

import React, { useState } from 'react';
import LandingPage from '../components/landing/LandingPage';
import { useAuth } from '../context/AuthContext';
import AuthPage from '../components/AuthPage';
import Layout from '../components/Layout';

export default function Home() {
  const [showAuth, setShowAuth] = useState(false);
  const { user, loading } = useAuth();

  // If loading, show a spinner or skeleton
  if (loading) return <div className="min-h-screen bg-black flex items-center justify-center text-white">Loading...</div>;

  // If not logged in:
  if (!user) {
    if (showAuth) {
      return <AuthPage mode="signup" />;
    }
    return <LandingPage onSignInClick={() => setShowAuth(true)} />;
  }

  // If logged in, render the Dashboard Layout (which handles routing and mobile responsiveness)
  return <Layout />;
}
