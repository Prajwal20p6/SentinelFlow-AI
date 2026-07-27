'use client';

import React, { useState, useEffect } from 'react';
import { PromptStoreView } from '../../../components/dashboard/PromptStoreView';
import { useIncidentStore } from '../../../store/incidentStore';
import { api } from '../../../lib/api';

export default function PromptsPage() {
  const { prompts, setPrompts } = useIncidentStore();

  const [ragQuery, setRagQuery] = useState('');
  const [ragResults, setRagResults] = useState<any[]>([]);
  const [ragLoading, setRagLoading] = useState(false);

  useEffect(() => {
    api.getPrompts()
      .then((res) => setPrompts(res.templates))
      .catch(console.error);
  }, [setPrompts]);

  const runRAGSearch = async () => {
    if (!ragQuery.trim()) return;
    setRagLoading(true);
    try {
      const res = await api.ragSearch({ query: ragQuery, limit: 3 });
      setRagResults(res.results);
    } catch (e) {
      console.error(e);
    } finally {
      setRagLoading(false);
    }
  };

  return (
    <PromptStoreView
      ragQuery={ragQuery}
      setRagQuery={setRagQuery}
      runRAGSearch={runRAGSearch}
      ragLoading={ragLoading}
      ragResults={ragResults}
      prompts={prompts}
    />
  );
}
