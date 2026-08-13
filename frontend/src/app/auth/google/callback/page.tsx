'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Shield, Loader2, AlertTriangle } from 'lucide-react';
import { api } from '../../../../lib/api';
import { useAuthStore } from '../../../../store/authStore';

function GoogleCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setUser, setIsLoggedIn, setAuthError } = useAuthStore();

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const handleAuth = async () => {
      let idToken = searchParams.get('id_token') || searchParams.get('credential');

      // Check URL hash if id_token was returned in location.hash
      if (!idToken && typeof window !== 'undefined' && window.location.hash) {
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        idToken = hashParams.get('id_token') || hashParams.get('credential');
      }

      if (!idToken) {
        setError('No Google authentication credential received. Please try signing in again.');
        setLoading(false);
        return;
      }

      try {
        const data = await api.googleLogin(idToken);
        setUser(data.user);
        setIsLoggedIn(true);
        router.push('/dashboard');
      } catch (err: any) {
        setError(err?.data?.detail || err?.message || 'Google authentication failed. Please try again.');
        setAuthError(err?.data?.detail || err?.message || 'Google authentication failed.');
        setLoading(false);
      }
    };

    handleAuth();
  }, [searchParams, router, setUser, setIsLoggedIn, setAuthError]);

  return (
    <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center p-6 relative overflow-hidden font-sans">
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full filter blur-[100px] pointer-events-none"></div>
      <div className="w-full max-w-md p-8 glass rounded-2xl border border-white/5 text-center space-y-6 relative z-10">
        <div className="flex justify-center">
          <div className="p-3 bg-emerald-500/10 rounded-2xl border border-emerald-500/20">
            <Shield className="w-10 h-10 text-[#00ff88]" />
          </div>
        </div>

        <h2 className="text-xl font-bold text-slate-100 uppercase tracking-wide">
          Authenticating with Google
        </h2>

        {loading && (
          <div className="space-y-4 py-4">
            <Loader2 className="w-8 h-8 text-[#00ff88] animate-spin mx-auto" />
            <p className="text-sm text-slate-300">Validating Google identity & establishing secure session...</p>
          </div>
        )}

        {error && (
          <div className="space-y-4 py-4 animate-fade-in">
            <div className="p-3.5 bg-rose-950/25 border border-rose-500/20 rounded-xl text-xs text-rose-400 flex items-start gap-2.5 text-left">
              <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => router.push('/')}
              className="mt-4 px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-slate-900 font-bold text-xs rounded-xl uppercase tracking-wider transition-all"
            >
              Back to Sign In
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function GoogleCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-[#00ff88] animate-spin" />
        </div>
      }
    >
      <GoogleCallbackContent />
    </Suspense>
  );
}
