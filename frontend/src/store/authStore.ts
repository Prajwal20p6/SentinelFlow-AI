import { create } from 'zustand';
import { User } from '../types';

export type AuthView = 'login' | 'register' | 'forgot' | 'reset' | 'reset_password_final';

interface AuthState {
  isLoggedIn: boolean;
  user: User | null;
  email: string;
  password: string;
  mfaRequired: boolean;
  mfaToken: string;
  authError: string;
  authLoading: boolean;
  authView: AuthView;
  regFullName: string;
  regOrgId: string;
  regRole: string;
  resetToken: string;
  resetSuccessMsg: string;
  sessions: any[];

  setIsLoggedIn: (val: boolean) => void;
  setUser: (user: User | null) => void;
  setEmail: (email: string) => void;
  setPassword: (password: string) => void;
  setMfaRequired: (val: boolean) => void;
  setMfaToken: (token: string) => void;
  setAuthError: (error: string) => void;
  setAuthLoading: (loading: boolean) => void;
  setAuthView: (view: AuthView) => void;
  setRegFullName: (name: string) => void;
  setRegOrgId: (orgId: string) => void;
  setRegRole: (role: string) => void;
  setResetToken: (token: string) => void;
  setResetSuccessMsg: (msg: string) => void;
  setSessions: (sessions: any[]) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isLoggedIn: false,
  user: null,
  email: 'admin@sentinelflow.ai',
  password: 'admin123',
  mfaRequired: false,
  mfaToken: '',
  authError: '',
  authLoading: false,
  authView: 'login',
  regFullName: '',
  regOrgId: '',
  regRole: 'responder',
  resetToken: '',
  resetSuccessMsg: '',
  sessions: [],

  setIsLoggedIn: (isLoggedIn) => set({ isLoggedIn }),
  setUser: (user) => set({ user }),
  setEmail: (email) => set({ email }),
  setPassword: (password) => set({ password }),
  setMfaRequired: (mfaRequired) => set({ mfaRequired }),
  setMfaToken: (mfaToken) => set({ mfaToken }),
  setAuthError: (authError) => set({ authError }),
  setAuthLoading: (authLoading) => set({ authLoading }),
  setAuthView: (authView) => set({ authView }),
  setRegFullName: (regFullName) => set({ regFullName }),
  setRegOrgId: (regOrgId) => set({ regOrgId }),
  setRegRole: (regRole) => set({ regRole }),
  setResetToken: (resetToken) => set({ resetToken }),
  setResetSuccessMsg: (resetSuccessMsg) => set({ resetSuccessMsg }),
  setSessions: (sessions) => set({ sessions }),

  logout: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('sf_token');
    }
    set({
      isLoggedIn: false,
      user: null,
      mfaRequired: false,
      mfaToken: '',
      authError: '',
    });
  },
}));
