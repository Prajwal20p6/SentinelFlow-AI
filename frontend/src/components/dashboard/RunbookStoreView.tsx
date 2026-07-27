'use client';

import React from 'react';
import { Upload, Edit, Activity, BookOpen } from 'lucide-react';
import { User } from '../../types';

interface RunbookStoreViewProps {
  user: User | null;
  kbSearchQuery: string;
  setKbSearchQuery: (query: string) => void;
  handleKbSearch: () => void;
  fetchKbDocuments: () => void;
  kbUploadTitle: string;
  setKbUploadTitle: (title: string) => void;
  kbUploadCategory: string;
  setKbUploadCategory: (cat: string) => void;
  kbUploadSubcategory: string;
  setKbUploadSubcategory: (subcat: string) => void;
  kbUploadTags: string;
  setKbUploadTags: (tags: string) => void;
  setKbUploadFile: (file: File | null) => void;
  handleKbUpload: (e: React.FormEvent) => void;
  kbUploadLoading: boolean;
  knowledgeDocs: any[];
  selectedDoc: any;
  setSelectedDoc: (doc: any) => void;
  handleKbApprove: (id: number) => void;
  handleKbArchive: (id: number) => void;
  kbIsEditing: boolean;
  setKbIsEditing: (editing: boolean) => void;
  kbEditingContent: string;
  setKbEditingContent: (content: string) => void;
  kbEditingVersion: string;
  setKbEditingVersion: (version: string) => void;
  handleKbEditSubmit: (e: React.FormEvent) => void;
}

export const RunbookStoreView: React.FC<RunbookStoreViewProps> = ({
  user,
  kbSearchQuery,
  setKbSearchQuery,
  handleKbSearch,
  fetchKbDocuments,
  kbUploadTitle,
  setKbUploadTitle,
  kbUploadCategory,
  setKbUploadCategory,
  kbUploadSubcategory,
  setKbUploadSubcategory,
  kbUploadTags,
  setKbUploadTags,
  setKbUploadFile,
  handleKbUpload,
  kbUploadLoading,
  knowledgeDocs,
  selectedDoc,
  setSelectedDoc,
  handleKbApprove,
  handleKbArchive,
  kbIsEditing,
  setKbIsEditing,
  kbEditingContent,
  setKbEditingContent,
  kbEditingVersion,
  setKbEditingVersion,
  handleKbEditSubmit,
}) => {
  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold text-slate-100">SecOps Knowledge Base & Playbook Manager</h2>
        <p className="text-xs text-slate-500 mt-1">
          Upload runbooks, PDF SOPs, and recovery guides. Content is automatically parsed, split into 500-token chunks, and indexed into Qdrant for semantic RAG lookups.
        </p>
      </div>

      {/* Search & Filter Bar */}
      <div className="flex gap-3 bg-white/5 p-4 rounded-2xl border border-white/5 font-mono text-xs">
        <input
          type="text"
          placeholder="Query semantic playbook index (e.g. memory leak, oom troubleshooting)..."
          value={kbSearchQuery}
          onChange={e => setKbSearchQuery(e.target.value)}
          className="flex-1 px-4 py-2.5 bg-[#0d111a] border border-white/10 rounded-xl text-slate-200 text-xs focus:outline-none"
        />
        <button
          onClick={handleKbSearch}
          className="px-5 py-2.5 bg-[#00ff88]/10 text-[#00ff88] border border-[#00ff88]/20 font-bold rounded-xl hover:bg-[#00ff88]/20 transition-all uppercase"
        >
          Search Index
        </button>
        <button
          onClick={() => {
            setKbSearchQuery('');
            fetchKbDocuments();
          }}
          className="px-4 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 rounded-xl transition-all uppercase"
        >
          Reset
        </button>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Column 1: Document Upload & List */}
        <div className="lg:col-span-1 space-y-6">
          {/* Upload Widget */}
          <div className="card p-5 space-y-4">
            <h3 className="text-xs font-bold text-[#00ff88] uppercase tracking-widest flex items-center gap-1.5">
              <Upload className="w-4 h-4 text-[#00ff88]" /> Index Recovery Document
            </h3>
            
            <form onSubmit={handleKbUpload} className="space-y-3.5 text-xs">
              <div className="space-y-1">
                <label className="block text-slate-400 font-bold uppercase text-[9px] tracking-wider">Document Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Memory Leak mitigation playbook"
                  value={kbUploadTitle}
                  onChange={e => setKbUploadTitle(e.target.value)}
                  className="w-full px-3.5 py-2 bg-[#0d111a] border border-white/10 rounded-lg text-slate-200 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="block text-slate-400 font-bold uppercase text-[9px] tracking-wider">Category</label>
                  <select
                    value={kbUploadCategory}
                    onChange={e => setKbUploadCategory(e.target.value)}
                    className="w-full px-3.5 py-2 bg-[#0d111a] border border-white/10 rounded-lg text-slate-200 focus:outline-none"
                  >
                    <option value="runbooks">Runbook</option>
                    <option value="sops">SOP</option>
                    <option value="playbooks">Playbook</option>
                    <option value="guides">Guide</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="block text-slate-400 font-bold uppercase text-[9px] tracking-wider">Subcategory</label>
                  <select
                    value={kbUploadSubcategory}
                    onChange={e => setKbUploadSubcategory(e.target.value)}
                    className="w-full px-3.5 py-2 bg-[#0d111a] border border-white/10 rounded-lg text-slate-200 focus:outline-none"
                  >
                    <option value="kubernetes">Kubernetes</option>
                    <option value="aws">AWS Cloud</option>
                    <option value="security">Security Sec</option>
                    <option value="performance">Performance</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="block text-slate-400 font-bold uppercase text-[9px] tracking-wider">Search Keywords / Tags</label>
                <input
                  type="text"
                  placeholder="e.g. oom, restart, leak"
                  value={kbUploadTags}
                  onChange={e => setKbUploadTags(e.target.value)}
                  className="w-full px-3.5 py-2 bg-[#0d111a] border border-white/10 rounded-lg text-slate-200 focus:outline-none"
                />
              </div>

              {/* File selector input */}
              <div className="space-y-1">
                <label className="block text-slate-400 font-bold uppercase text-[9px] tracking-wider">Source Document (PDF, DOCX, MD, TXT)</label>
                <input
                  type="file"
                  required
                  onChange={e => {
                    if (e.target.files && e.target.files.length > 0) {
                      setKbUploadFile(e.target.files[0]);
                    }
                  }}
                  className="w-full p-2 bg-[#0d111a]/50 border border-white/5 border-dashed rounded-lg text-slate-400 cursor-pointer"
                />
              </div>

              <button
                type="submit"
                disabled={kbUploadLoading}
                className="w-full py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-900 font-bold rounded-lg transition-all uppercase tracking-wider text-[10px]"
              >
                {kbUploadLoading ? 'Parsing & Embedding...' : 'Embed playbook'}
              </button>
            </form>
          </div>

          {/* Document List */}
          <div className="space-y-3">
            <div className="flex justify-between items-center mb-1">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Available Knowledge Files</h3>
              <span className="text-[10px] bg-white/5 px-2 py-0.5 rounded text-slate-500 font-mono">
                Count: {knowledgeDocs.length}
              </span>
            </div>

            <div className="space-y-2.5 overflow-y-auto max-h-[calc(100vh-500px)] pr-2">
              {knowledgeDocs.map(doc => (
                <div
                  key={doc.id}
                  onClick={() => {
                    setSelectedDoc(doc);
                    setKbEditingContent(doc.content);
                    setKbEditingVersion(doc.version);
                    setKbIsEditing(false);
                  }}
                  className={`p-3.5 card cursor-pointer transition-all border ${
                    selectedDoc?.id === doc.id ? 'border-[#00ff88] bg-emerald-500/5' : 'border-white/5'
                  }`}
                >
                  <div className="flex justify-between items-start mb-1 text-[10px] font-mono">
                    <span className="text-[#00d4ff] uppercase tracking-wider">{doc.category}</span>
                    <span className={`px-1.5 py-0.5 rounded uppercase ${
                      doc.status === 'approved' ? 'bg-emerald-500/10 text-[#00ff88]' : 'bg-amber-500/10 text-amber-400'
                    }`}>
                      {doc.status}
                    </span>
                  </div>
                  <h4 className="text-xs font-bold text-slate-200 line-clamp-1">{doc.title}</h4>
                  <div className="flex justify-between items-center mt-2.5 pt-2 border-t border-white/5 text-[9px] text-slate-500 font-mono">
                    <span>Author: {doc.author}</span>
                    <span>v{doc.version}</span>
                  </div>
                </div>
              ))}
              {knowledgeDocs.length === 0 && (
                <div className="text-center py-8 font-mono text-xs text-slate-500">No documents indexed in storage.</div>
              )}
            </div>
          </div>
        </div>

        {/* Column 2: Selected Document Detail Inspector */}
        <div className="lg:col-span-2">
          {selectedDoc ? (
            <div className="card p-6 space-y-6 animate-fade-in text-xs">
              {/* Document Details Header */}
              <div className="flex justify-between items-start border-b border-white/5 pb-4">
                <div>
                  <h3 className="text-base font-bold text-slate-100">{selectedDoc.title}</h3>
                  <p className="text-[10px] text-slate-500 font-mono mt-1">File: {selectedDoc.filename} (Author: {selectedDoc.author})</p>
                </div>

                <div className="flex items-center gap-2">
                  {selectedDoc.status === 'draft' && user?.role === 'admin' && (
                    <button
                      onClick={() => handleKbApprove(selectedDoc.id)}
                      className="px-3 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-900 font-bold text-[10px] rounded-lg transition-all uppercase tracking-wider"
                    >
                      Approve Playbook
                    </button>
                  )}
                  {user?.role === 'admin' && (
                    <button
                      onClick={() => handleKbArchive(selectedDoc.id)}
                      className="px-3 py-1.5 bg-white/5 hover:bg-rose-500/15 border border-white/10 hover:border-rose-500/20 text-rose-400 font-bold text-[10px] rounded-lg transition-all uppercase tracking-wider"
                    >
                      Archive
                    </button>
                  )}
                </div>
              </div>

              {/* Content Preview & Editing */}
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Document Content Payload</h4>
                  {!kbIsEditing ? (
                    <button
                      onClick={() => setKbIsEditing(true)}
                      className="text-[#00ff88] hover:underline flex items-center gap-1 font-mono text-[10px]"
                    >
                      <Edit className="w-3 h-3" /> Edit content
                    </button>
                  ) : (
                    <button
                      onClick={() => setKbIsEditing(false)}
                      className="text-slate-500 hover:underline font-mono text-[10px]"
                    >
                      Cancel
                    </button>
                  )}
                </div>

                {kbIsEditing ? (
                  <form onSubmit={handleKbEditSubmit} className="space-y-3">
                    <textarea
                      rows={12}
                      value={kbEditingContent}
                      onChange={e => setKbEditingContent(e.target.value)}
                      className="w-full p-4 bg-[#0d111a] border border-white/10 rounded-xl text-slate-300 font-mono text-xs focus:outline-none focus:border-[#00ff88]/30"
                    />
                    
                    <div className="flex justify-between items-center gap-3">
                      <div className="flex items-center gap-2">
                        <label className="text-slate-500 font-mono uppercase text-[9px] tracking-wider shrink-0">Version</label>
                        <input
                          type="text"
                          value={kbEditingVersion}
                          onChange={e => setKbEditingVersion(e.target.value)}
                          className="w-20 px-2 py-1 bg-[#0d111a] border border-white/10 rounded text-center text-slate-200 focus:outline-none focus:border-[#00ff88]/30"
                        />
                      </div>

                      <button
                        type="submit"
                        className="px-4 py-2 bg-emerald-600 text-slate-900 font-bold text-[10px] rounded-lg uppercase tracking-wider transition-all"
                      >
                        Save Changes
                      </button>
                    </div>
                  </form>
                ) : (
                  <div className="p-4 bg-black/30 border border-white/5 rounded-xl text-slate-300 leading-relaxed font-mono whitespace-pre-wrap select-text max-h-[350px] overflow-y-auto">
                    {selectedDoc.content}
                  </div>
                )}
              </div>

              {/* Analytics Dashboard Panel */}
              <div className="p-4 bg-[#1a1f2e] border border-white/5 rounded-xl space-y-3">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                  <Activity className="w-4 h-4 text-[#00d4ff]" /> Playbook Analytics
                </h4>
                
                <div className="grid grid-cols-3 gap-3 text-center font-mono">
                  <div className="p-2.5 bg-white/5 rounded border border-white/5">
                    <span className="text-slate-500 block uppercase text-[9px]">Matched Matches</span>
                    <span className="text-slate-200 font-bold text-base mt-1">{selectedDoc.usage_count}</span>
                  </div>
                  <div className="p-2.5 bg-white/5 rounded border border-white/5">
                    <span className="text-slate-500 block uppercase text-[9px]">Applied Actions</span>
                    <span className="text-[#00ff88] font-bold text-base mt-1">{selectedDoc.success_count}</span>
                  </div>
                  <div className="p-2.5 bg-white/5 rounded border border-white/5">
                    <span className="text-slate-500 block uppercase text-[9px]">Success Rate</span>
                    <span className="text-amber-400 font-bold text-base mt-1">
                      {selectedDoc.usage_count > 0 ? `${Math.round((selectedDoc.success_count / selectedDoc.usage_count) * 100)}%` : '100%'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="card p-12 flex flex-col items-center justify-center text-center">
              <BookOpen className="w-12 h-12 text-slate-600 mb-4 animate-pulse-glow" />
              <h4 className="text-sm font-bold text-slate-400">Select a knowledge file from the list to view extraction chunks & edit playbooks</h4>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
