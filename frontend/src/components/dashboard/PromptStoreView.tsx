'use client';

import React from 'react';
import { Eye, Loader2 } from 'lucide-react';
import { PromptTemplate } from '../../types';

interface PromptStoreViewProps {
  ragQuery: string;
  setRagQuery: (query: string) => void;
  runRAGSearch: () => void;
  ragLoading: boolean;
  ragResults: any[];
  prompts: PromptTemplate[];
}

export const PromptStoreView: React.FC<PromptStoreViewProps> = ({
  ragQuery,
  setRagQuery,
  runRAGSearch,
  ragLoading,
  ragResults,
  prompts,
}) => {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">CRISPE Prompts & Vector RAG Store</h2>
          <p className="text-xs text-slate-500 mt-1">Structured agent directives linked to Qdrant vector database similarity match runbooks</p>
        </div>
      </div>

      {/* RAG interactive query console */}
      <div className="card p-5 space-y-4">
        <h4 className="text-xs font-bold text-slate-200 uppercase tracking-widest">Similarity Search Console</h4>
        <div className="flex gap-3">
          <input
            type="text"
            value={ragQuery}
            onChange={e => setRagQuery(e.target.value)}
            placeholder="Search for OOM or CPU resolution runbooks..."
            className="flex-1 px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-lg focus:outline-none focus:border-emerald-500 text-xs text-slate-300"
          />
          <button
            onClick={runRAGSearch}
            disabled={ragLoading}
            className="px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-900 font-bold text-xs rounded-lg transition-all flex items-center gap-2"
          >
            {ragLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Eye className="w-3.5 h-3.5" />}
            QUERY
          </button>
        </div>

        {/* Similarity query results */}
        {ragResults.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 animate-fade-in">
            {ragResults.map((res, i) => (
              <div key={i} className="p-4 bg-white/5 border border-white/5 rounded-xl space-y-2">
                <div className="flex justify-between items-start gap-2">
                  <h5 className="text-xs font-bold text-slate-200 line-clamp-1">{res.title}</h5>
                  <span className="font-mono text-[9px] text-[#00ff88] bg-emerald-950/20 border border-emerald-500/20 px-1.5 py-0.5 rounded shrink-0">
                    Score: {Math.round(res.score * 100)}%
                  </span>
                </div>
                <p className="text-xs text-slate-500 line-clamp-4">{res.content}</p>
                <div className="flex gap-1 flex-wrap pt-1">
                  {res.tags.map((tag: string) => (
                    <span key={tag} className="text-[9px] font-mono text-slate-400 bg-white/5 px-2 py-0.5 rounded">
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Prompt template list */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {prompts.map(pr => (
          <div key={pr.id} className="p-5 card space-y-4">
            <div className="flex justify-between items-start border-b border-white/5 pb-3">
              <div>
                <h4 className="text-sm font-bold text-slate-200">{pr.name}</h4>
                <span className="text-[10px] text-[#00d4ff] font-mono">{pr.id}</span>
              </div>
              <span className="badge badge-info uppercase text-[9px]">{pr.category}</span>
            </div>

            <div className="space-y-2.5 text-xs text-slate-400">
              <p><span className="text-slate-500 font-bold">CAPACITY:</span> {pr.capacity}</p>
              <p><span className="text-slate-500 font-bold">ROLE:</span> {pr.role}</p>
              <p><span className="text-slate-500 font-bold">INTENT:</span> {pr.intent}</p>
              <p><span className="text-slate-500 font-bold">SUBJECT:</span> {pr.subject}</p>
              <p><span className="text-slate-500 font-bold">EVALUATION:</span> {pr.evaluation}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
