'use client';

import React from 'react';
import { Shield, Lock, AlertTriangle, Loader2 } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';

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
  onVerifyEmail,
  onResetPasswordSubmit,
}) => {
  const {
    email, setEmail,
    password, setPassword,
    authView, setAuthView,
    authError,
    authLoading,
    mfaRequired, mfaToken, setMfaToken,
    resetToken, setResetToken,
    resetSuccessMsg,
    regFullName, setRegFullName,
    regOrgId, setRegOrgId,
    regRole, setRegRole,
  } = useAuthStore();

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
        <p className="text-sm text-center text-slate-400 mb-6">
          Autonomous K8s SecOps & Telemetry Monitor
        </p>

        {resetSuccessMsg && (
          <div className="mb-5 p-3.5 bg-emerald-950/25 border border-emerald-500/20 rounded-xl text-xs text-[#00ff88] leading-relaxed">
            {resetSuccessMsg}
          </div>
        )}

        {/* VIEW: LOGIN */}
        {authView === 'login' && (
          <form onSubmit={onLoginSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Identity (Email)
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full px-4 py-3 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all placeholder:text-slate-600 text-sm"
                placeholder="identity@sentinelflow.ai"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
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
                  <Lock className="w-3.5 h-3.5" /> Google Authenticator Token (MFA)
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
                  Dual-Factor challenge active. Key in the 6-digit verification code.
                </p>
              </div>
            )}

            {authError && (
              <div className="p-3.5 bg-rose-950/25 border border-rose-500/20 rounded-xl text-xs text-rose-400 flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                <span>{authError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={authLoading}
              className="w-full py-3.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-slate-900 font-bold rounded-xl transition-all shadow-lg hover:shadow-emerald-500/10 active:scale-[0.98] flex items-center justify-center gap-2 text-sm"
            >
              {authLoading ? <Loader2 className="w-4 h-4 animate-spin text-slate-900" /> : 'INJECT CREDENTIALS'}
            </button>

            <div className="flex justify-between items-center text-xs text-slate-400 pt-2">
              <button type="button" onClick={() => setAuthView('register')} className="hover:text-emerald-400 transition-colors">
                Create account
              </button>
              <button type="button" onClick={() => setAuthView('forgot')} className="hover:text-emerald-400 transition-colors">
                Forgot password?
              </button>
            </div>
          </form>
        )}

        {/* VIEW: REGISTER */}
        {authView === 'register' && (
          <form onSubmit={onRegisterSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
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
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
                placeholder="identity@sentinelflow.ai"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Organization ID (Optional)
              </label>
              <input
                type="text"
                value={regOrgId}
                onChange={e => setRegOrgId(e.target.value)}
                className="w-full px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
                placeholder="org-123"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Security Role
              </label>
              <select
                value={regRole}
                onChange={e => setRegRole(e.target.value)}
                className="w-full px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-sm"
              >
                <option value="responder">Responder (SecOps Engineer)</option>
                <option value="executive">Executive (Read & Approve)</option>
                <option value="viewer">Viewer (Read-only)</option>
                <option value="admin">Administrator</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
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
              {authLoading ? <Loader2 className="w-4 h-4 animate-spin text-slate-900" /> : 'REGISTER IDENTITY'}
            </button>

            <div className="text-center text-xs text-slate-400 pt-2">
              <button type="button" onClick={() => setAuthView('login')} className="hover:text-emerald-400 transition-colors">
                Already have an account? Sign in
              </button>
            </div>
          </form>
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
                placeholder="identity@sentinelflow.ai"
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
              {authLoading ? <Loader2 className="w-4 h-4 animate-spin text-slate-900" /> : 'REQUEST RESET TOKEN'}
            </button>

            <div className="text-center text-xs text-slate-400 pt-2 flex justify-between">
              <button type="button" onClick={() => setAuthView('login')} className="hover:text-emerald-400 transition-colors">
                Back to login
              </button>
              <button type="button" onClick={() => setAuthView('reset')} className="hover:text-emerald-400 transition-colors">
                Enter verification token
              </button>
            </div>
          </form>
        )}

        {/* VIEW: TOKEN RESET / VERIFICATION PORTAL */}
        {authView === 'reset' && (
          <div className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Verification / Reset Token
              </label>
              <textarea
                rows={3}
                required
                value={resetToken}
                onChange={e => setResetToken(e.target.value)}
                className="w-full px-4 py-3 bg-[#0d111a] border border-white/10 rounded-xl focus:outline-none focus:border-emerald-500 text-slate-200 transition-all text-xs font-mono"
                placeholder="Paste verification or password reset JWT token here"
              />
            </div>

            {authError && (
              <div className="p-3.5 bg-rose-950/25 border border-rose-500/20 rounded-xl text-xs text-rose-400 flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0" />
                <span>{authError}</span>
              </div>
            )}

            <div className="flex gap-3">
              <button
                type="button"
                onClick={onVerifyEmail}
                disabled={authLoading}
                className="flex-1 py-3 bg-emerald-600 hover:bg-emerald-500 text-slate-900 font-bold rounded-xl transition-all text-xs font-bold"
              >
                VERIFY EMAIL
              </button>
              <button
                type="button"
                onClick={() => {
                  setAuthView('reset_password_final');
                }}
                className="flex-1 py-3 bg-white/5 hover:bg-white/10 border border-white/10 text-slate-200 font-bold rounded-xl transition-all text-xs font-bold"
              >
                RESET PASSWORD
              </button>
            </div>

            <div className="text-center text-xs text-slate-400 pt-2">
              <button type="button" onClick={() => setAuthView('login')} className="hover:text-emerald-400 transition-colors">
                Back to login
              </button>
            </div>
          </div>
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

            <button
              type="submit"
              disabled={authLoading}
              className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-slate-900 font-bold rounded-xl transition-all shadow-lg text-sm"
            >
              {authLoading ? <Loader2 className="w-4 h-4 animate-spin text-slate-900" /> : 'CONFIRM RESET'}
            </button>

            <div className="text-center text-xs text-slate-400 pt-2">
              <button type="button" onClick={() => setAuthView('login')} className="hover:text-emerald-400 transition-colors">
                Cancel
              </button>
            </div>
          </form>
        )}

      </div>
    </div>
  );
};
