'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '../../store/authStore';
import { useIncidentStore } from '../../store/incidentStore';
import { Navbar } from '../../components/common/Navbar';
import { Sidebar } from '../../components/common/Sidebar';
import { useWebSocket } from '../../hooks/useWebSocket';
import { api } from '../../lib/api';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { isLoggedIn, user, setUser, setIsLoggedIn } = useAuthStore();
  const {
    globalStatus,
    setGlobalStatus,
    activeIncidentCount,
    setActiveIncidentCount,
    serverHealth,
    setIncidents,
  } = useIncidentStore();

  // Redirect unauthenticated users to root login page & hydrate session
  useEffect(() => {
    const token = localStorage.getItem('sf_token');
    if (!isLoggedIn && !token) {
      router.push('/');
    } else if (token && (!isLoggedIn || !user)) {
      setIsLoggedIn(true);
      const stored = localStorage.getItem('sf_user');
      if (stored) {
        try {
          setUser(JSON.parse(stored));
        } catch (e) {}
      }
    }
  }, [isLoggedIn, user, router, setIsLoggedIn, setUser]);

  // Real-time WebSocket Subscriptions for the dashboard shell
  useWebSocket('IncidentUpdate', () => {
    api.getIncidents()
      .then((res) => {
        setIncidents(res.incidents);
        const active = res.incidents.filter((i) =>
          ['DETECTED', 'ANALYZING', 'PENDING_APPROVAL', 'APPROVED', 'EXECUTING'].includes(i.status)
        );
        setActiveIncidentCount(active.length);
        setGlobalStatus(active.length > 0 ? 'THREAT_DETECTED' : 'SECURE');
      })
      .catch(console.error);
  });

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch (e) {}
    localStorage.removeItem('sf_token');
    localStorage.removeItem('sf_refresh_token');
    localStorage.removeItem('sf_user');
    setIsLoggedIn(false);
    setUser(null);
    router.push('/');
  };

  return (
    <div className="min-h-screen bg-[#0a0e17] flex flex-col font-sans text-slate-300">
      <Navbar
        user={user}
        globalStatus={globalStatus}
        onLogout={handleLogout}
      />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          activeIncidentCount={activeIncidentCount}
          serverHealth={serverHealth}
          govMode="MANUAL"
          govMinConfidence={90}
        />

        <main className="flex-1 p-8 overflow-y-auto z-10 relative">
          {children}
        </main>
      </div>
    </div>
  );
}
