'use client';

import React, { useState, useEffect } from 'react';
import { RunbookStoreView } from '../../../components/dashboard/RunbookStoreView';
import { useAuthStore } from '../../../store/authStore';

import { getApiBaseUrl } from '../../../lib/api';

export default function KnowledgePage() {
  const { user } = useAuthStore();

  const [knowledgeDocs, setKnowledgeDocs] = useState<any[]>([]);
  const [kbSearchQuery, setKbSearchQuery] = useState('');
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [kbUploadTitle, setKbUploadTitle] = useState('');
  const [kbUploadCategory, setKbUploadCategory] = useState('runbooks');
  const [kbUploadSubcategory, setKbUploadSubcategory] = useState('kubernetes');
  const [kbUploadTags, setKbUploadTags] = useState('');
  const [kbUploadFile, setKbUploadFile] = useState<File | null>(null);
  const [kbUploadLoading, setKbUploadLoading] = useState(false);
  const [kbEditingContent, setKbEditingContent] = useState('');
  const [kbEditingVersion, setKbEditingVersion] = useState('');
  const [kbIsEditing, setKbIsEditing] = useState(false);

  useEffect(() => {
    fetchKbDocuments();
  }, []);

  const fetchKbDocuments = async () => {
    try {
      const token = localStorage.getItem('sf_token');
      const res = await fetch(`${getApiBaseUrl()}/knowledge/documents`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setKnowledgeDocs(data);
      }
    } catch (err) {
      console.error('Fetch docs error:', err);
    }
  };

  const handleKbUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!kbUploadFile) return;
    setKbUploadLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', kbUploadFile);
      formData.append('title', kbUploadTitle);
      formData.append('category', kbUploadCategory);
      formData.append('subcategory', kbUploadSubcategory);
      formData.append('tags', kbUploadTags);

      const token = localStorage.getItem('sf_token');
      const res = await fetch(`${getApiBaseUrl()}/knowledge/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      if (res.ok) {
        setKbUploadTitle('');
        setKbUploadTags('');
        setKbUploadFile(null);
        fetchKbDocuments();
      }
    } catch (err) {
      console.error('Upload document error:', err);
    } finally {
      setKbUploadLoading(false);
    }
  };

  const handleKbSearch = async () => {
    if (!kbSearchQuery.trim()) {
      fetchKbDocuments();
      return;
    }
    try {
      const token = localStorage.getItem('sf_token');
      const res = await fetch(`${getApiBaseUrl()}/knowledge/search?q=${encodeURIComponent(kbSearchQuery)}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setKnowledgeDocs(data);
      }
    } catch (err) {
      console.error('Search docs error:', err);
    }
  };

  const handleKbApprove = async (docId: number) => {
    try {
      const token = localStorage.getItem('sf_token');
      const res = await fetch(`${getApiBaseUrl()}/knowledge/documents/${docId}/approve`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        fetchKbDocuments();
        if (selectedDoc && selectedDoc.id === docId) {
          setSelectedDoc({ ...selectedDoc, status: 'approved' });
        }
      }
    } catch (err) {
      console.error('Approve doc error:', err);
    }
  };

  const handleKbArchive = async (docId: number) => {
    try {
      const token = localStorage.getItem('sf_token');
      const res = await fetch(`${getApiBaseUrl()}/knowledge/documents/${docId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        fetchKbDocuments();
        setSelectedDoc(null);
      }
    } catch (err) {
      console.error('Archive doc error:', err);
    }
  };

  const handleKbEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDoc) return;
    try {
      const token = localStorage.getItem('sf_token');
      const res = await fetch(`${getApiBaseUrl()}/knowledge/documents/${selectedDoc.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          content: kbEditingContent,
          version: kbEditingVersion
        })
      });
      if (res.ok) {
        const updated = await res.json();
        setSelectedDoc(updated);
        setKbIsEditing(false);
        fetchKbDocuments();
      }
    } catch (err) {
      console.error('Update doc error:', err);
    }
  };

  return (
    <RunbookStoreView
      user={user}
      kbSearchQuery={kbSearchQuery}
      setKbSearchQuery={setKbSearchQuery}
      handleKbSearch={handleKbSearch}
      fetchKbDocuments={fetchKbDocuments}
      kbUploadTitle={kbUploadTitle}
      setKbUploadTitle={setKbUploadTitle}
      kbUploadCategory={kbUploadCategory}
      setKbUploadCategory={setKbUploadCategory}
      kbUploadSubcategory={kbUploadSubcategory}
      setKbUploadSubcategory={setKbUploadSubcategory}
      kbUploadTags={kbUploadTags}
      setKbUploadTags={setKbUploadTags}
      setKbUploadFile={setKbUploadFile}
      handleKbUpload={handleKbUpload}
      kbUploadLoading={kbUploadLoading}
      knowledgeDocs={knowledgeDocs}
      selectedDoc={selectedDoc}
      setSelectedDoc={setSelectedDoc}
      handleKbApprove={handleKbApprove}
      handleKbArchive={handleKbArchive}
      kbIsEditing={kbIsEditing}
      setKbIsEditing={setKbIsEditing}
      kbEditingContent={kbEditingContent}
      setKbEditingContent={setKbEditingContent}
      kbEditingVersion={kbEditingVersion}
      setKbEditingVersion={setKbEditingVersion}
      handleKbEditSubmit={handleKbEditSubmit}
    />
  );
}
