'use client';

import React, { useState } from 'react';
import { Database, Search, ChevronDown, ChevronUp, Layers, FileText, AlertCircle } from 'lucide-react';
import { useMastraStore } from '../../store/mastraStore';

export const QdrantRetrievalPanel: React.FC = () => {
  const { ragEvents, activeStorageTier } = useMastraStore();
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const latestRetrieval = ragEvents.length > 0 ? ragEvents[ragEvents.length - 1] : null;
  const currentTier = latestRetrieval?.storage_tier || activeStorageTier || 'InMemory fallback';
  const totalDocs = latestRetrieval?.total_documents || 12;

  const getTierBadge = (tier: string) => {
    switch (tier) {
      case 'Qdrant':
        return {
          bg: 'bg-[#00ff88]/10',
          text: 'text-[#00ff88]',
          border: 'border-[#00ff88]/30',
          label: 'Qdrant Primary Vector DB',
        };
      case 'ChromaDB fallback':
        return {
          bg: 'bg-[#00d4ff]/10',
          text: 'text-[#00d4ff]',
          border: 'border-[#00d4ff]/30',
          label: 'Served from ChromaDB fallback',
        };
      case 'FAISS fallback':
        return {
          bg: 'bg-purple-500/10',
          text: 'text-purple-400',
          border: 'border-purple-500/30',
          label: 'Served from FAISS fallback',
        };
      default:
        return {
          bg: 'bg-amber-500/10',
          text: 'text-amber-400',
          border: 'border-amber-500/30',
          label: 'Served from In-Memory fallback',
        };
    }
  };

  const badge = getTierBadge(currentTier);

  return (
    <div className="card p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-widest flex items-center gap-2">
          <Database className="w-4 h-4 text-[#00d4ff]" /> Qdrant & Vector Retrieval Visibility
        </h4>
        <span
          className={`px-2.5 py-1 ${badge.bg} ${badge.text} border ${badge.border} rounded-md text-[10px] font-mono font-bold uppercase flex items-center gap-1.5`}
        >
          <Layers className="w-3 h-3" />
          {badge.label}
        </span>
      </div>

      {/* Index Metrics Bar */}
      <div className="grid grid-cols-2 gap-3 text-xs font-mono">
        <div className="p-3 bg-black/40 border border-white/5 rounded-xl">
          <span className="text-slate-500 text-[10px] block uppercase">Collection</span>
          <span className="text-slate-200 font-bold">runbooks</span>
        </div>
        <div className="p-3 bg-black/40 border border-white/5 rounded-xl">
          <span className="text-slate-500 text-[10px] block uppercase">Total Vectors Indexed</span>
          <span className="text-[#00ff88] font-bold">{totalDocs} documents</span>
        </div>
      </div>

      {/* Fallback Tier Notice */}
      {currentTier !== 'Qdrant' && (
        <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl flex items-center gap-2.5 text-[11px] text-amber-300">
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
          <span>
            Qdrant cluster in fallback mode. Query transparently served from{' '}
            <strong className="font-bold">{currentTier}</strong>.
          </span>
        </div>
      )}

      {/* Live Retrieval Activity */}
      {latestRetrieval ? (
        <div className="space-y-3 pt-1">
          <div className="p-3 bg-white/5 border border-white/5 rounded-xl space-y-1">
            <span className="text-[10px] text-slate-500 font-mono uppercase block flex items-center gap-1.5">
              <Search className="w-3 h-3 text-[#00d4ff]" /> Active Search Query
            </span>
            <p className="text-xs text-slate-200 font-mono italic">"{latestRetrieval.query}"</p>
          </div>

          <div className="space-y-2">
            <span className="text-[10px] text-slate-400 font-mono uppercase block">
              Top Matched Vector Snippets ({latestRetrieval.results?.length || 0})
            </span>
            {(latestRetrieval.results || []).map((hit: any, idx: number) => {
              const isExpanded = expandedIndex === idx;
              const hitTier = hit.storage_tier || currentTier;
              const hitBadge = getTierBadge(hitTier);

              return (
                <div
                  key={idx}
                  className="p-3 bg-black/50 border border-white/10 rounded-xl space-y-2 hover:border-white/20 transition-all"
                >
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileText className="w-3.5 h-3.5 text-[#00d4ff] shrink-0" />
                      <span className="font-bold text-slate-200 truncate">{hit.title || `Document #${hit.id}`}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className={`px-1.5 py-0.5 ${hitBadge.bg} ${hitBadge.text} text-[9px] font-mono rounded`}>
                        {hitTier}
                      </span>
                      <span className="font-mono text-[11px] font-bold text-[#00ff88] bg-[#00ff88]/10 px-2 py-0.5 rounded-md border border-[#00ff88]/20">
                        {hit.score ? (hit.score * 100).toFixed(1) + '%' : 'N/A'} match
                      </span>
                      <button
                        onClick={() => setExpandedIndex(isExpanded ? null : idx)}
                        className="p-1 text-slate-400 hover:text-white"
                      >
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-400 font-mono line-clamp-2 leading-relaxed">
                    {hit.content}
                  </p>

                  {isExpanded && (
                    <div className="pt-2 border-t border-white/5 space-y-1">
                      <span className="text-[9px] font-mono text-slate-500 uppercase">Full Document Content:</span>
                      <pre className="p-2.5 bg-black/80 rounded-lg text-[10px] font-mono text-slate-300 whitespace-pre-wrap max-h-40 overflow-y-auto leading-normal">
                        {hit.content}
                      </pre>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="p-4 text-center space-y-1 bg-black/20 rounded-xl border border-white/5">
          <p className="text-xs text-slate-400 font-mono">No live vector retrieval executed for current context.</p>
          <p className="text-[10px] text-slate-600 font-mono">
            Trigger an incident above to observe real-time similarity search.
          </p>
        </div>
      )}
    </div>
  );
};
