import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Sidebar } from '../common/Sidebar';

describe('Sidebar Component', () => {
  const dummySetTab = jest.fn();

  const dummyProps = {
    activeTab: 'dashboard',
    setActiveTab: dummySetTab,
    activeIncidentCount: 3,
    serverHealth: { services: { websocket: '2 clients' } },
    govMode: 'SEMI_AUTONOMOUS',
  };

  it('renders all nav buttons and active incident badge', () => {
    render(<Sidebar {...dummyProps} />);

    expect(screen.getByText('Cyber Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Executive Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Active Incidents')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('SEMI_AUTONOMOUS')).toBeInTheDocument();
  });

  it('calls setActiveTab when a navigation button is clicked', () => {
    render(<Sidebar {...dummyProps} />);

    const execBtn = screen.getByText('Executive Dashboard');
    fireEvent.click(execBtn);
    expect(dummySetTab).toHaveBeenCalledWith('executive');
  });
});
