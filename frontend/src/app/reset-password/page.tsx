'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Shield, CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';

function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get('token');

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (!token) {
      setError('No password reset token provided in URL. Please check your email link.');
    }
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      setError('Invalid reset token.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const res = await api.resetPassword({ token, new_password: password });
      setSuccess(res.message || 'Password updated successfully! Redirecting to sign in...');
      setTimeout(() => {
        router.push('/');
      }, 3000);
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || 'Failed to reset password. Link may be expired.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center p-6 relative overflow-hidden font-sans">
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full filter blur-[100px] pointer-events-none"></div>
      <div className="w-full max-w-md p-8 glass rounded-2xl border border-white/5 space-y-6 relative z-10">
        <div className="flex justify-center">
          <div className="p-3 bg-emerald-500/10 rounded-2xl border border-emerald-500/20">
            <Shield className="w-10 h-10 text-[#00ff88]" />
          </div>
        </div>

        <h2 className="text-xl font-bold text-center text-slate-100 uppercase tracking-wide">
          Reset Your Password
        </h2>

        {success ? (
          <div className="space-y-4 py-4 text-center animate-fade-in">
            <CheckCircle2 className="w-12 h-12 text-[#00ff88] mx-auto" />
            <p className="text-sm font-semibold text-[#00ff88]">{success}</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                New Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
                placeholder="••••••••"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                Confirm New Password
              </label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-4 py-3 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="p-3.5 bg-rose-950/25 border border-rose-500/20 rounded-xl text-xs text-rose-400 flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !token}
              className="w-full py-3.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-slate-900 font-bold rounded-xl transition-all shadow-lg text-sm uppercase tracking-wider flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'UPDATE PASSWORD'}
            </button>

            <div className="text-center text-xs text-slate-400 pt-2">
              <button
                type="button"
                onClick={() => router.push('/')}
                className="hover:text-emerald-400 transition-colors"
              >
                Back to Sign In
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-[#00ff88] animate-spin" />
        </div>
      }
    >
      <ResetPasswordContent />
    </Suspense>
  );
}
