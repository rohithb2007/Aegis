import React from 'react';
import type { AuditRecord } from '../types/aegis';
import { AuditTable } from '../components/AuditTable';
import { FileText } from 'lucide-react';

interface AuditPageProps {
  audits: AuditRecord[];
}

export const AuditPage: React.FC<AuditPageProps> = ({ audits }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
          <FileText size={24} color="#38bdf8" />
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#ffffff' }}>
            Security Audit Explorer
          </h2>
        </div>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          Chronological record of evaluated proposed commands, risk scores, capability tags, policy decisions, and secret redaction.
        </p>
      </div>

      <AuditTable records={audits} />
    </div>
  );
};
