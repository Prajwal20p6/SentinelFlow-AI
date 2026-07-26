import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Navbar } from '../common/Navbar';

describe('Navbar Component', () => {
  const dummyLogout = jest.fn();

  const mockUser = {
    id: 1,
    email: 'admin@sentinelflow.ai',
    full_name: 'Admin User',
    role: 'admin' as const,
    is_active: true,
    mfa_enabled: false,
    created_at: new Date().toISOString(),
  };

  it('renders user details and status badge', () => {
    render(<Navbar user={mockUser} globalStatus="SECURE" onLogout={dummyLogout} />);

    expect(screen.getByText('SENTINELFLOW AI')).toBeInTheDocument();
    expect(screen.getByText('STATUS:')).toBeInTheDocument();
    expect(screen.getByText('SECURE')).toBeInTheDocument();
    expect(screen.getByText(/admin@sentinelflow.ai/i)).toBeInTheDocument();
  });

  it('triggers onLogout when logout button is clicked', () => {
    render(<Navbar user={mockUser} globalStatus="SECURE" onLogout={dummyLogout} />);

    const logoutBtn = screen.getByTitle('Log Out');
    fireEvent.click(logoutBtn);
    expect(dummyLogout).toHaveBeenCalledTimes(1);
  });
});
