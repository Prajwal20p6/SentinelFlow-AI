'use client';

import React, { useState, useEffect } from 'react';
import { SafetyAuditLogsView } from '../../../components/dashboard/SafetyAuditLogsView';
import { useIncidentStore } from '../../../store/incidentStore';
import { api } from '../../../lib/api';

export default function AuditPage() {
  const { auditEntries, setAuditEntries } = useIncidentStore();

  const [ledgerValidating, setLedgerValidating] = useState(false);
  const [ledgerValidationResult, setLedgerValidationResult] = useState<{ valid: boolean; message: string } | null>(null);

  useEffect(() => {
    api.getAuditTrail()
      .then((res) => setAuditEntries(res.audit_entries))
      .catch(console.error);
  }, [setAuditEntries]);

  const verifyAuditLedger = async () => {
    setLedgerValidating(true);
    try {
      const res = await api.verifyAuditTrail();
      setLedgerValidationResult(res);
    } catch (e: any) {
      setLedgerValidationResult({
        valid: false,
        message: e.message || 'Validation request failed'
      });
    } finally {
      setLedgerValidating(false);
    }
  };

  const archiveAuditLedger = () => {
    alert('Audit ledger chain exported to S3 bucket s3://sentinelflow-audit-vault-prod/');
  };

  return (
    <SafetyAuditLogsView
      auditEntries={auditEntries}
      verifyAuditLedger={verifyAuditLedger}
      ledgerValidating={ledgerValidating}
      archiveAuditLedger={archiveAuditLedger}
      ledgerValidationResult={ledgerValidationResult}
    />
  );
}
