'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Shield, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get('token');

  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState<string>('Verifying your email address...');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('No verification token provided in URL. Please check your email link.');
      return;
    }

    api.verifyEmail(token)
      .then((res) => {
        setStatus('success');
        setMessage(res.message || 'Email verified successfully! Your account is now active.');
        setTimeout(() => {
          router.push('/');
        }, 3000);
      })
      .catch((err: any) => {
        setStatus('error');
        setMessage(err?.data?.detail || err?.message || 'Verification link is invalid or has expired.');
      });
  }, [token, router]);

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
          SentinelFlow AI Verification
        </h2>

        {status === 'loading' && (
          <div className="space-y-4 py-4">
            <Loader2 className="w-8 h-8 text-[#00ff88] animate-spin mx-auto" />
            <p className="text-sm text-slate-300">{message}</p>
          </div>
        )}

        {status === 'success' && (
          <div className="space-y-4 py-4 animate-fade-in">
            <CheckCircle2 className="w-12 h-12 text-[#00ff88] mx-auto" />
            <p className="text-sm font-semibold text-[#00ff88]">{message}</p>
            <p className="text-xs text-slate-500">Redirecting to sign in...</p>
          </div>
        )}

        {status === 'error' && (
          <div className="space-y-4 py-4 animate-fade-in">
            <XCircle className="w-12 h-12 text-rose-500 mx-auto" />
            <p className="text-sm text-rose-400 font-medium">{message}</p>
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

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-[#00ff88] animate-spin" />
      </div>
    }>
      <VerifyEmailContent />
    </Suspense>
  );
}
