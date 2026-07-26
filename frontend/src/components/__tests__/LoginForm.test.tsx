import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { LoginForm } from '../auth/LoginForm';
import { useAuthStore } from '../../store/authStore';

describe('LoginForm Component', () => {
  const dummyProps = {
    onLoginSubmit: jest.fn(e => e.preventDefault()),
    onRegisterSubmit: jest.fn(e => e.preventDefault()),
    onForgotPasswordSubmit: jest.fn(e => e.preventDefault()),
    onVerifyEmail: jest.fn(),
    onResetPasswordSubmit: jest.fn(e => e.preventDefault()),
  };

  beforeEach(() => {
    useAuthStore.setState({
      authView: 'login',
      email: 'test@sentinelflow.ai',
      password: 'password123',
      authError: '',

      authLoading: false,
      mfaRequired: false,
    });
  });

  it('renders login form with title and input fields', () => {
    render(<LoginForm {...dummyProps} />);
    expect(screen.getByText(/SENTINELFLOW AI/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/identity@sentinelflow.ai/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /INJECT CREDENTIALS/i })).toBeInTheDocument();
  });

  it('renders MFA field when mfaRequired is true', () => {
    useAuthStore.setState({ mfaRequired: true });
    render(<LoginForm {...dummyProps} />);
    expect(screen.getByPlaceholderText('000000')).toBeInTheDocument();
  });

  it('renders auth error message when provided', () => {
    useAuthStore.setState({ authError: 'Invalid credentials' });
    render(<LoginForm {...dummyProps} />);
    expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
  });
});
