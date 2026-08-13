'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '../store/authStore';
import { LoginForm } from '../components/auth/LoginForm';
import { api } from '../lib/api';

export default function Home() {
  const router = useRouter();
  const {
    isLoggedIn,
    setIsLoggedIn,
    setUser,
    email,
    password,
    mfaToken,
    setMfaRequired,
    setMfaToken,
    setAuthError,
    setAuthLoading,
    setAuthView,
    regFullName,
    regOrgId,
    regRole,
    resetToken,
    setResetToken,
    setResetSuccessMsg,
  } = useAuthStore();

  useEffect(() => {
    const token = localStorage.getItem('sf_token');
    if (isLoggedIn || token) {
      if (token && !isLoggedIn) {
        setIsLoggedIn(true);
        const stored = localStorage.getItem('sf_user');
        if (stored) setUser(JSON.parse(stored));
      }
      router.push('/dashboard');
    }
  }, [isLoggedIn, router, setIsLoggedIn, setUser]);

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    setAuthLoading(true);

    try {
      const res = await api.login(email, password, mfaToken || undefined);
      if (res.mfaRequired) {
        setMfaRequired(true);
        setAuthLoading(false);
      } else {
        setIsLoggedIn(true);
        const stored = localStorage.getItem('sf_user');
        if (stored) setUser(JSON.parse(stored));
        setMfaRequired(false);
        setMfaToken('');
        setAuthLoading(false);
        router.push('/dashboard');
      }
    } catch (err: any) {
      setAuthLoading(false);
      setAuthError(err.data?.detail || 'Authentication failed. Please verify credentials.');
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    setResetSuccessMsg('');
    setAuthLoading(true);
    try {
      const res = await api.register({
        email,
        password,
        full_name: regFullName,
        role: regRole,
        organization_id: regOrgId || undefined,
      });
      setResetSuccessMsg(res.message || `Account created successfully. We've sent a verification link to ${email}.`);
      setAuthView('verify_notice');
      setAuthLoading(false);
    } catch (err: any) {
      setAuthLoading(false);
      setAuthError(err.data?.detail || 'Registration failed.');
    }
  };

  const handleVerifyEmail = async () => {
    setAuthError('');
    setResetSuccessMsg('');
    setAuthLoading(true);
    try {
      await api.verifyEmail(resetToken);
      setResetSuccessMsg('Email verified successfully! You can now login.');
      setAuthView('login');
      setAuthLoading(false);
    } catch (err: any) {
      setAuthLoading(false);
      setAuthError(err.data?.detail || 'Verification failed.');
    }
  };

  const handleForgotPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    setResetSuccessMsg('');
    setAuthLoading(true);
    try {
      const res = await api.forgotPassword(email);
      setResetSuccessMsg(res.message || `A password reset link has been sent to ${email}. Please check your inbox.`);
      setAuthLoading(false);
    } catch (err: any) {
      setAuthLoading(false);
      setAuthError(err.data?.detail || 'Password reset request failed.');
    }
  };

  const handleResetPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    setResetSuccessMsg('');
    setAuthLoading(true);
    try {
      await api.resetPassword({
        token: resetToken,
        new_password: password,
      });
      setResetSuccessMsg('Password reset successfully! Please login with your new password.');
      setAuthView('login');
      setAuthLoading(false);
    } catch (err: any) {
      setAuthLoading(false);
      setAuthError(err.data?.detail || 'Password reset failed.');
    }
  };

  return (
    <LoginForm
      onLoginSubmit={handleLoginSubmit}
      onRegisterSubmit={handleRegisterSubmit}
      onForgotPasswordSubmit={handleForgotPasswordSubmit}
      onVerifyEmail={handleVerifyEmail}
      onResetPasswordSubmit={handleResetPasswordSubmit}
    />
  );
}
