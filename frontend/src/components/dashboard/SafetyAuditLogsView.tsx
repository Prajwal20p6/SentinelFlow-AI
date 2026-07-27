'use client';

import React from 'react';
import { CheckCircle, XCircle } from 'lucide-react';
import { AuditEntry } from '../../types';

interface SafetyAuditLogsViewProps {
  auditEntries: AuditEntry[];
  verifyAuditLedger: () => void;
  ledgerValidating: boolean;
  archiveAuditLedger: () => void;
  ledgerValidationResult: { valid: boolean; message: string } | null;
}

export const SafetyAuditLogsView: React.FC<SafetyAuditLogsViewProps> = ({
  auditEntries,
  verifyAuditLedger,
  ledgerValidating,
  archiveAuditLedger,
  ledgerValidationResult,
}) => {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">Tamper-Evident Audit Ledger</h2>
          <p className="text-xs text-slate-500 mt-1">Cryptographically chained execution trail validating platform action integrity</p>
        </div>
        
        <div className="flex gap-3">
          <button
            onClick={verifyAuditLedger}
            disabled={ledgerValidating}
            className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-900 font-bold text-xs rounded-lg transition-all"
          >
            {ledgerValidating ? 'VERIFYING...' : 'VERIFY LEDGER INTEGRITY'}
          </button>
          
          <button
            onClick={archiveAuditLedger}
            className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 font-semibold text-xs rounded-lg transition-all"
          >
            ARCHIVE TO S3
          </button>
        </div>
      </div>

      {/* Ledger verification panel reports */}
      {ledgerValidationResult && (
        <div className={`p-4 rounded-xl border animate-fade-in text-sm ${ledgerValidationResult.valid ? 'bg-emerald-950/20 border-emerald-500/20 text-[#00ff88]' : 'bg-rose-950/20 border-rose-500/20 text-rose-400'}`}>
          <div className="flex items-center gap-2 font-bold mb-1">
            {ledgerValidationResult.valid ? <CheckCircle className="w-5 h-5 shrink-0" /> : <XCircle className="w-5 h-5 shrink-0" />}
            <span>{ledgerValidationResult.valid ? 'LEDGER VERIFICATION PASSED' : 'LEDGER VERIFICATION FAILED'}</span>
          </div>
          <p className="text-xs text-slate-400 ml-7">{ledgerValidationResult.message}</p>
        </div>
      )}

      {/* Ledger table */}
      <div className="card p-5">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/5 text-slate-500 font-bold">
                <th className="py-2.5">ID</th>
                <th className="py-2.5">Command</th>
                <th className="py-2.5">Status</th>
                <th className="py-2.5">Risk Score</th>
                <th className="py-2.5">Performed By</th>
                <th className="py-2.5">Block Hash</th>
                <th className="py-2.5">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {auditEntries.map(entry => (
                <tr key={entry.id} className="hover:bg-white/5 transition-all font-mono">
                  <td className="py-3 font-semibold text-slate-500">#{entry.id}</td>
                  <td className="py-3 text-slate-200 font-sans max-w-xs truncate" title={entry.command_checked}>{entry.command_checked}</td>
                  <td className="py-3">
                    <span className={`badge ${entry.status === 'ALLOWED' ? 'badge-success' : 'badge-critical'}`}>
                      {entry.status}
                    </span>
                  </td>
                  <td className="py-3 font-bold text-slate-400">{Math.round(entry.risk_score * 100)}%</td>
                  <td className="py-3 font-sans text-slate-400">{entry.performed_by.split('@')[0]}</td>
                  <td className="py-3 text-slate-500 text-[10px]" title={entry.hash || ''}>
                    {entry.hash ? `${entry.hash.substring(0, 8)}...` : 'genesis'}
                  </td>
                  <td className="py-3 text-slate-500 text-[10px] font-sans">
                    {new Date(entry.timestamp).toLocaleString()}
                  </td>
                </tr>
              ))}
              {auditEntries.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 font-mono text-xs">
                    No ledger actions written to memory.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
