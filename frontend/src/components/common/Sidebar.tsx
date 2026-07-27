'use client';

import React from 'react';
import {
  Activity,
  Shield,
  Sliders,
  Server,
  FileSpreadsheet,
  Database,
  Cpu,
  FolderOpen,
  Settings,
  Gauge,
  ListChecks,
  Zap,
  Terminal,
} from 'lucide-react';

import { usePathname, useRouter } from 'next/navigation';

interface SidebarProps {
  activeTab?: string;
  setActiveTab?: (tab: any) => void;
  activeIncidentCount: number;
  serverHealth: any;
  govMode: string;
  govMinConfidence?: number;
}


export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  activeIncidentCount,
  serverHealth,
  govMode,
  govMinConfidence = 85,
}) => {
  const router = useRouter();
  const pathname = usePathname();

  const handleTabClick = (tab: string) => {
    if (setActiveTab) {
      setActiveTab(tab);
    }
    router.push(`/${tab}`);
  };

  const isTabActive = (tab: string) => {
    if (activeTab) return activeTab === tab;
    if (pathname === `/${tab}`) return true;
    if (tab === 'dashboard' && (pathname === '/' || pathname === '/dashboard')) return true;
    return false;
  };


  return (
    <nav className="w-64 bg-[#111827] border-r border-white/5 p-4 space-y-2 flex flex-col justify-between">
      <div className="space-y-1">
        <button
          onClick={() => handleTabClick('dashboard')}
          className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${
            isTabActive('dashboard')
              ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]'
              : 'hover:bg-white/5 text-slate-400'
          }`}
        >
          <Activity className="w-4 h-4" /> Cyber Dashboard
        </button>

        <button
          onClick={() => handleTabClick('executive')}
          className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${
            isTabActive('executive')
              ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]'
              : 'hover:bg-white/5 text-slate-400'
          }`}
        >
          <Shield className="w-4 h-4" /> Executive Dashboard
        </button>

        <button
          onClick={() => handleTabClick('incidents')}
          className={`w-full flex items-center justify-between px-4 py-3 text-sm font-semibold rounded-xl transition-all ${
            isTabActive('incidents')
              ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]'
              : 'hover:bg-white/5 text-slate-400'
          }`}
        >
          <span className="flex items-center gap-3">
            <Sliders className="w-4 h-4" /> Active Incidents
          </span>
          {activeIncidentCount > 0 && (
            <span className="px-2 py-0.5 bg-[#ff3366] text-white rounded-full text-[10px]">
              {activeIncidentCount}
            </span>
          )}
        </button>

        <button
          onClick={() => handleTabClick('topology')}
          className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${
            isTabActive('topology')
              ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]'
              : 'hover:bg-white/5 text-slate-400'
          }`}
        >
          <Server className="w-4 h-4" /> Cluster Topology
        </button>

        <button
          onClick={() => handleTabClick('audit')}
          className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${
            isTabActive('audit')
              ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]'
              : 'hover:bg-white/5 text-slate-400'
          }`}
        >
          <FileSpreadsheet className="w-4 h-4" /> Safety Audit Logs
        </button>

        <button
          onClick={() => handleTabClick('prompts')}
          className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${
            isTabActive('prompts')
              ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]'
              : 'hover:bg-white/5 text-slate-400'
          }`}
        >
          <Database className="w-4 h-4" /> Prompt & RAG Store
        </button>

        <button
          onClick={() => handleTabClick('observability')}
          className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${
            isTabActive('observability')
              ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]'
              : 'hover:bg-white/5 text-slate-400'
          }`}
        >
          <Cpu className="w-4 h-4" /> Observability Traces
        </button>

        <button
          onClick={() => handleTabClick('knowledge')}
          className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${
            isTabActive('knowledge')
              ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]'
              : 'hover:bg-white/5 text-slate-400'
          }`}
        >
          <FolderOpen className="w-4 h-4" /> Runbook & SOP Store
        </button>

        <button
          onClick={() => handleTabClick('settings')}
          className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${
            isTabActive('settings')
              ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]'
              : 'hover:bg-white/5 text-slate-400'
          }`}
        >
          <Settings className="w-4 h-4" /> Security Settings
        </button>

        <button
          onClick={() => handleTabClick('metrics')}
          className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${
            isTabActive('metrics')
              ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]'
              : 'hover:bg-white/5 text-slate-400'
          }`}
        >
          <Gauge className="w-4 h-4" /> Live Metrics
        </button>

        <button
          onClick={() => handleTabClick('playbooks')}
          className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${
            isTabActive('playbooks')
              ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]'
              : 'hover:bg-white/5 text-slate-400'
          }`}
        >
          <ListChecks className="w-4 h-4" /> Playbook Tracker
        </button>

        <button
          onClick={() => handleTabClick('mastra')}
          className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${
            isTabActive('mastra')
              ? 'bg-emerald-500/10 text-[#00ff88] border-l-2 border-[#00ff88]'
              : 'hover:bg-white/5 text-slate-400'
          }`}
        >
          <Zap className="w-4 h-4" /> Mastra Execution
        </button>

      </div>

      {/* Quick Metrics mini card */}
      <div className="p-4 bg-[#1a1f2e] border border-white/5 rounded-2xl">
        <div className="flex items-center gap-2 mb-2">
          <Terminal className="w-3.5 h-3.5 text-[#00d4ff]" />
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            Rate Limiter
          </span>
        </div>
        <div className="flex justify-between text-xs text-slate-500">
          <span>Requests</span>
          <span className="text-slate-300 font-mono">
            {serverHealth?.services?.websocket || '0 clients'}
          </span>
        </div>
        <div className="w-full bg-white/5 h-1.5 rounded-full mt-2 overflow-hidden">
          <div className="bg-[#00d4ff] h-full" style={{ width: '35%' }}></div>
        </div>
      </div>

      {/* Autopilot Mode Dashboard Indicator */}
      <div className="p-4 bg-[#1a1f2e] border border-white/5 rounded-2xl mt-3">
        <div className="flex items-center gap-2 mb-2">
          <Zap className="w-3.5 h-3.5 text-[#00ff88]" />
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest font-mono">
            Autopilot Mode
          </span>
        </div>
        <div className="flex justify-between items-center text-xs">
          <span className="text-slate-500 font-mono text-[10px]">Governance</span>
          <span
            className={`font-mono font-bold text-[9px] px-1.5 py-0.5 rounded ${
              govMode === 'FULLY_AUTONOMOUS'
                ? 'bg-emerald-500/10 text-[#00ff88] border border-emerald-500/20'
                : govMode === 'SEMI_AUTONOMOUS'
                ? 'bg-[#00d4ff]/10 text-[#00d4ff] border border-[#00d4ff]/20'
                : 'bg-slate-800 text-slate-400 border border-slate-700'
            }`}
          >
            {govMode}
          </span>
        </div>
        <div className="flex justify-between text-[10px] text-slate-500 mt-2 font-mono">
          <span>Confidence Gate</span>
          <span className="text-slate-300 font-mono">{govMinConfidence}%</span>
        </div>
      </div>
    </nav>

  );
};
