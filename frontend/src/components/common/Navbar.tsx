'use client';

import React from 'react';
import { Shield, Power } from 'lucide-react';
import { User } from '../../types';

interface NavbarProps {
  user: User | null;
  globalStatus: string;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  globalStatus,
  onLogout,
}) => {
  return (
    <header className="border-b border-white/5 bg-[#111827] px-6 py-4 flex items-center justify-between z-20">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-emerald-500/10 rounded-xl border border-emerald-500/20">
          <Shield className="w-6 h-6 text-[#00ff88]" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-slate-200 tracking-wider">SENTINELFLOW AI</h1>
          <p className="text-xs text-slate-500">Autonomous Cyber-Defense & Autopilot K8s Node Exporter</p>
        </div>
      </div>

      {/* Global Status Banner */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2.5">
          <div className="relative flex h-2 w-2">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                globalStatus === 'SECURE' ? 'bg-[#00ff88]' : 'bg-[#ff3366]'
              }`}
            ></span>
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                globalStatus === 'SECURE' ? 'bg-[#00ff88]' : 'bg-[#ff3366]'
              }`}
            ></span>
          </div>
          <span className="text-xs uppercase font-bold tracking-widest">
            STATUS:{' '}
            <span className={globalStatus === 'SECURE' ? 'text-[#00ff88]' : 'text-[#ff3366]'}>
              {globalStatus.replace('_', ' ')}
            </span>
          </span>
        </div>

        <div className="h-6 w-[1px] bg-white/10"></div>

        <div className="flex items-center gap-2.5">
          <span className="text-xs text-slate-500">USER:</span>
          <span className="text-xs font-mono bg-white/5 px-2.5 py-1 rounded text-slate-300">
            {user?.email} ({user?.role})
          </span>
        </div>

        <button
          onClick={onLogout}
          className="p-2 text-slate-400 hover:text-rose-400 bg-white/5 hover:bg-rose-500/10 border border-white/5 rounded-lg transition-all"
          title="Log Out"
        >
          <Power className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
