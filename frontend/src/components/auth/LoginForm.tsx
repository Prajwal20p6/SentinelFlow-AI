'use client';

import React, { useState, useEffect } from 'react';
import { Shield, Lock, AlertTriangle, Loader2, CheckCircle2, Mail } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { api } from '../../lib/api';

interface LoginFormProps {
  onLoginSubmit: (e: React.FormEvent) => void;
  onRegisterSubmit: (e: React.FormEvent) => void;
  onForgotPasswordSubmit: (e: React.FormEvent) => void;
  onVerifyEmail: () => void;
  onResetPasswordSubmit: (e: React.FormEvent) => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({
  onLoginSubmit,
  onRegisterSubmit,
  onForgotPasswordSubmit,
  onResetPasswordSubmit,
}) => {
  const {
    email, setEmail,
    password, setPassword,
    authView, setAuthView,
    authError, setAuthError,
    authLoading, setAuthLoading,
    mfaRequired, mfaToken, setMfaToken,
    resetSuccessMsg, setResetSuccessMsg,
    regFullName, setRegFullName,
    regOrgId, setRegOrgId,
    regRole, setRegRole,
    setIsLoggedIn, setUser,
  } = useAuthStore();

  const [resendStatus, setResendStatus] = useState<string>('');
  const [resendLoading, setResendLoading] = useState<boolean>(false);

  // Initialize Google Sign-In SDK if available
  useEffect(() => {
    const initGoogle = () => {
      if (typeof window !== 'undefined' && (window as any).google?.accounts?.id) {
        const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
        if (clientId) {
          try {
            (window as any).google.accounts.id.initialize({
              client_id: clientId,
              callback: handleGoogleCallback,
              auto_select: false,
            });
          } catch (e) {
            console.error('Google Auth Init Exception:', e);
          }
        }
      }
    };
    initGoogle();
  }, []);

  const handleGoogleCallback = async (response: any) => {
    if (!response || !response.credential) return;
    setAuthLoading(true);
    setAuthError('');
    try {
      const data = await api.googleLogin(response.credential);
      setUser(data.user);
      setIsLoggedIn(true);
    } catch (err: any) {
      setAuthError(err?.data?.detail || err?.message || 'Google authentication failed. Please try again.');
    } finally {
      setAuthLoading(false);
    }
  };

  const triggerGoogleSignIn = () => {
    setAuthError('');
    const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

    if (typeof window !== 'undefined' && (window as any).google?.accounts?.id && googleClientId) {
      try {
        (window as any).google.accounts.id.initialize({
          client_id: googleClientId,
          callback: handleGoogleCallback,
        });
        (window as any).google.accounts.id.prompt((notification: any) => {
          if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            // Fallback to direct OAuth redirect if One-Tap prompt is skipped/suppressed
            const redirectUri = encodeURIComponent(`${window.location.origin}/auth/google/callback`);
            window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${googleClientId}&redirect_uri=${redirectUri}&response_type=id_token&scope=openid%20email%20profile&nonce=${Date.now()}`;
          }
        });
        return;
      } catch (err) {
        console.error('Google prompt exception:', err);
      }
    }

    if (googleClientId) {
      const redirectUri = encodeURIComponent(`${window.location.origin}/auth/google/callback`);
      window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${googleClientId}&redirect_uri=${redirectUri}&response_type=id_token&scope=openid%20email%20profile&nonce=${Date.now()}`;
      return;
    }

    setAuthError('Google Sign-In is temporarily unavailable. Please try again.');
  };

  const handleResendEmail = async () => {
    if (!email) {
      setAuthError('Please enter your registered email address first.');
      return;
    }
    setResendLoading(true);
    setResendStatus('');
    try {
      const res = await api.resendVerification(email);
      setResendStatus(res.message || `Verification email sent to ${email}. Please check your inbox.`);
    } catch (err: any) {
      setAuthError(err?.data?.detail || err?.message || 'Failed to resend verification email.');
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center relative overflow-hidden font-sans">
      {/* Glow Effects */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full filter blur-[100px] pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full filter blur-[100px] pointer-events-none"></div>

      <div className="w-full max-w-md p-8 glass rounded-2xl border border-white/5 animate-fade-in relative z-10">
        <div className="flex justify-center mb-6">
          <div className="p-3 bg-emerald-500/10 rounded-2xl border border-emerald-500/20">
            <Shield className="w-10 h-10 text-[#00ff88]" />
          </div>
        </div>

        <h2 className="text-2xl font-bold text-center text-slate-100 tracking-wide mb-1">
          SENTINELFLOW AI
        </h2>
        <p className="text-xs text-center text-slate-400 mb-6 uppercase tracking-wider">
          Autonomous SecOps & Infrastructure Resilience
        </p>

        {resetSuccessMsg && (
          <div className="mb-5 p-3.5 bg-emerald-950/25 border border-emerald-500/20 rounded-xl text-xs text-[#00ff88] leading-relaxed flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-[#00ff88] shrink-0" />
            <span>{resetSuccessMsg}</span>
          </div>
        )}

        {resendStatus && (
          <div className="mb-5 p-3.5 bg-teal-950/30 border border-teal-500/30 rounded-xl text-xs text-teal-300 leading-relaxed flex items-center gap-2 font-mono">
            <Mail className="w-4 h-4 text-teal-400 shrink-0" />
            <span>{resendStatus}</span>
          </div>
        )}

        {/* VIEW: LOGIN */}
        {authView === 'login' && (
          <div className="space-y-5">
            {/* Google Sign-In Button */}
            <button
              type="button"
              onClick={triggerGoogleSignIn}
              disabled={authLoading}
              className="w-full py-3 bg-white hover:bg-slate-100 disabled:opacity-50 text-slate-900 font-semibold rounded-xl transition-all shadow-md flex items-center justify-center gap-3 text-sm"
            >
              <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
              </svg>
              <span>Continue with Google</span>
            </button>

            <div className="flex items-center gap-3">
              <div className="h-px bg-white/10 flex-1"></div>
              <span className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold">Or sign in with email</span>
              <div className="h-px bg-white/10 flex-1"></div>
            </div>

            <form onSubmit={onLoginSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="w-full px-4 py-3 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all placeholder:text-slate-600 text-sm"
                  placeholder="name@example.com"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  Password
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full px-4 py-3 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all placeholder:text-slate-600 text-sm"
                  placeholder="••••••••"
                />
              </div>

              {mfaRequired && (
                <div className="p-4 bg-emerald-950/20 border border-emerald-500/30 rounded-xl animate-fade-in">
                  <label className="block text-xs font-semibold text-[#00ff88] uppercase tracking-wider mb-2 flex items-center gap-2">
                    <Lock className="w-3.5 h-3.5" /> Authenticator Code (MFA)
                  </label>
                  <input
                    type="text"
                    maxLength={6}
                    required
                    value={mfaToken}
                    onChange={e => setMfaToken(e.target.value)}
                    className="w-full px-4 py-3 bg-[#0d111a] border border-[#00ff88]/30 rounded-xl focus:outline-none focus:border-emerald-400 text-center tracking-widest text-[#00ff88] font-mono text-lg"
                    placeholder="000000"
                  />
                  <p className="text-[10px] text-slate-400 mt-2">
                    Enter the 6-digit TOTP code from your authenticator app.
                  </p>
                </div>
              )}

              {authError && (
                <div className="p-3.5 bg-rose-950/25 border border-rose-500/20 rounded-xl text-xs text-rose-400 flex flex-col gap-2">
                  <div className="flex items-start gap-2.5">
                    <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                    <span>{authError}</span>
                  </div>
                  {authError.toLowerCase().includes('verify') && (
                    <button
                      type="button"
                      onClick={handleResendEmail}
                      disabled={resendLoading}
                      className="self-end text-[11px] font-bold text-emerald-400 hover:text-emerald-300 underline"
                    >
                      {resendLoading ? 'Sending...' : 'Resend Verification Email'}
                    </button>
                  )}
                </div>
              )}

              <button
                type="submit"
                disabled={authLoading}
                className="w-full py-3.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-slate-900 font-bold rounded-xl transition-all shadow-lg hover:shadow-emerald-500/10 active:scale-[0.98] flex items-center justify-center gap-2 text-sm"
              >
                {authLoading ? <Loader2 className="w-4 h-4 animate-spin text-slate-900" /> : 'SIGN IN'}
              </button>

              <div className="flex justify-between items-center text-xs text-slate-400 pt-2">
                <button type="button" onClick={() => { setAuthError(''); setAuthView('register'); }} className="hover:text-emerald-400 transition-colors">
                  Create account
                </button>
                <button type="button" onClick={() => { setAuthError(''); setAuthView('forgot'); }} className="hover:text-emerald-400 transition-colors">
                  Forgot password?
                </button>
              </div>
            </form>
          </div>
        )}

        {/* VIEW: REGISTER */}
        {authView === 'register' && (
          <form onSubmit={onRegisterSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                Full Name
              </label>
              <input
                type="text"
                required
                value={regFullName}
                onChange={e => setRegFullName(e.target.value)}
                className="w-full px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
                placeholder="Jane Doe"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
                placeholder="name@example.com"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                Organization ID (Optional)
              </label>
              <input
                type="text"
                value={regOrgId}
                onChange={e => setRegOrgId(e.target.value)}
                className="w-full px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
                placeholder="org-prod-01"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                Security Role
              </label>
              <select
                value={regRole}
                onChange={e => setRegRole(e.target.value)}
                className="w-full px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
              >
                <option value="engineer">Responder (SecOps Engineer)</option>
                <option value="executive">Executive (Read & Approve)</option>
                <option value="viewer">Viewer (Read-only)</option>
                <option value="admin">Administrator</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
                placeholder="••••••••"
              />
            </div>

            {authError && (
              <div className="p-3.5 bg-rose-950/25 border border-rose-500/20 rounded-xl text-xs text-rose-400 flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0" />
                <span>{authError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={authLoading}
              className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-slate-900 font-bold rounded-xl transition-all shadow-lg text-sm"
            >
              {authLoading ? <Loader2 className="w-4 h-4 animate-spin text-slate-900" /> : 'CREATE ACCOUNT'}
            </button>

            <div className="text-center text-xs text-slate-400 pt-2">
              <button type="button" onClick={() => { setAuthError(''); setAuthView('login'); }} className="hover:text-emerald-400 transition-colors">
                Already have an account? Sign in
              </button>
            </div>
          </form>
        )}

        {/* VIEW: VERIFY NOTICE (After Registration) */}
        {authView === 'verify_notice' && (
          <div className="space-y-6 text-center animate-fade-in">
            <div className="w-16 h-16 bg-emerald-500/10 border border-emerald-500/30 rounded-2xl flex items-center justify-center mx-auto text-[#00ff88]">
              <Mail className="w-8 h-8" />
            </div>

            <div>
              <h3 className="text-lg font-bold text-slate-100">Verify Your Email Address</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                We&apos;ve sent a secure verification email to: <br />
                <span className="font-mono text-slate-200 font-semibold">{email}</span>
              </p>
              <p className="text-xs text-slate-500 mt-3">
                Please click the link in your email inbox to activate your account before logging in.
              </p>
            </div>

            <div className="space-y-3 pt-2">
              <button
                type="button"
                onClick={handleResendEmail}
                disabled={resendLoading}
                className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-slate-900 font-bold rounded-xl transition-all text-xs uppercase tracking-wider flex items-center justify-center gap-2"
              >
                {resendLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Resend Verification Email'}
              </button>

              <button
                type="button"
                onClick={() => { setAuthError(''); setAuthView('login'); }}
                className="w-full py-2.5 bg-white/5 hover:bg-white/10 text-slate-300 font-semibold rounded-xl transition-all text-xs"
              >
                Back to Sign In
              </button>
            </div>
          </div>
        )}

        {/* VIEW: FORGOT PASSWORD */}
        {authView === 'forgot' && (
          <form onSubmit={onForgotPasswordSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Registered Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full px-4 py-3 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
                placeholder="name@example.com"
              />
            </div>

            {authError && (
              <div className="p-3.5 bg-rose-950/25 border border-rose-500/20 rounded-xl text-xs text-rose-400 flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0" />
                <span>{authError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={authLoading}
              className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-slate-900 font-bold rounded-xl transition-all shadow-lg text-sm"
            >
              {authLoading ? <Loader2 className="w-4 h-4 animate-spin text-slate-900" /> : 'SEND PASSWORD RESET LINK'}
            </button>

            <div className="text-center text-xs text-slate-400 pt-2">
              <button type="button" onClick={() => { setAuthError(''); setAuthView('login'); }} className="hover:text-emerald-400 transition-colors">
                Back to Sign In
              </button>
            </div>
          </form>
        )}

        {/* VIEW: RESET PASSWORD FINAL STEP */}
        {authView === 'reset_password_final' && (
          <form onSubmit={onResetPasswordSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                New Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
                placeholder="••••••••"
              />
            </div>

            {authError && (
              <div className="p-3.5 bg-rose-950/25 border border-rose-500/20 rounded-xl text-xs text-rose-400 flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0" />
                <span>{authError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={authLoading}
              className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-slate-900 font-bold rounded-xl transition-all shadow-lg text-sm"
            >
              {authLoading ? <Loader2 className="w-4 h-4 animate-spin text-slate-900" /> : 'UPDATE PASSWORD'}
            </button>

            <div className="text-center text-xs text-slate-400 pt-2">
              <button type="button" onClick={() => { setAuthError(''); setAuthView('login'); }} className="hover:text-emerald-400 transition-colors">
                Cancel
              </button>
            </div>
          </form>
        )}

      </div>
    </div>
  );
};
