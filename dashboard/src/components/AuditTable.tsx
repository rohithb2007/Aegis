import React, { useState } from 'react';
import type { AuditRecord } from '../types/aegis';
import { Search, Filter, Lock, Eye } from 'lucide-react';

interface AuditTableProps {
  records: AuditRecord[];
}

export const AuditTable: React.FC<AuditTableProps> = ({ records }) => {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [riskFilter, setRiskFilter] = useState<string>('ALL');
  const [selectedRecord, setSelectedRecord] = useState<AuditRecord | null>(null);

  const filteredRecords = records.filter((rec) => {
    const matchesSearch =
      !search ||
      rec.command.toLowerCase().includes(search.toLowerCase()) ||
      rec.record_id.toLowerCase().includes(search.toLowerCase()) ||
      (rec.session_id && rec.session_id.toLowerCase().includes(search.toLowerCase()));

    const matchesStatus =
      statusFilter === 'ALL' ||
      rec.final_policy_decision.toUpperCase() === statusFilter ||
      (statusFilter === 'ALLOW' && (rec.final_policy_decision === 'PERMITTED' || rec.final_policy_decision === 'PASSTHROUGH'));

    const matchesRisk =
      riskFilter === 'ALL' ||
      (rec.v03_risk && rec.v03_risk.toUpperCase().includes(riskFilter));

    return matchesSearch && matchesStatus && matchesRisk;
  });

  return (
    <div className="glass-card" style={{ padding: '24px' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '16px',
        marginBottom: '20px',
      }}>
        <div style={{ position: 'relative', minWidth: '280px' }}>
          <Search size={14} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '10px' }} />
          <input
            type="text"
            placeholder="Filter by command, ID, session..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: '100%',
              backgroundColor: 'var(--bg-dark)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '8px 12px 8px 34px',
              fontSize: '12px',
              color: 'var(--text-primary)',
              outline: 'none',
              fontFamily: 'var(--font-mono)',
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Filter size={14} color="var(--text-muted)" />
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{
                backgroundColor: 'var(--bg-dark)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-primary)',
                borderRadius: '6px',
                padding: '4px 8px',
                fontSize: '12px',
                outline: 'none',
              }}
            >
              <option value="ALL">ALL</option>
              <option value="ALLOW">ALLOW</option>
              <option value="REVIEW">REVIEW</option>
              <option value="BLOCK">BLOCK</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Risk:</span>
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              style={{
                backgroundColor: 'var(--bg-dark)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-primary)',
                borderRadius: '6px',
                padding: '4px 8px',
                fontSize: '12px',
                outline: 'none',
              }}
            >
              <option value="ALL">ALL</option>
              <option value="SAFE">SAFE</option>
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>
        </div>
      </div>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        fontSize: '12px',
        color: 'var(--text-secondary)',
        marginBottom: '16px',
        padding: '8px 14px',
        backgroundColor: 'var(--input-bg)',
        borderRadius: '8px',
        border: '1px solid var(--border-subtle)',
        fontWeight: 500,
      }}>
        <Lock size={14} color="var(--accent-primary)" />
        <span>Audit Invariant I: All API keys, tokens, and raw secrets are automatically redacted prior to recording.</span>
      </div>

      {filteredRecords.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)', fontSize: '14px' }}>
          No audit records matching current filters.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>
                <th style={{ padding: '12px 14px', fontWeight: 700 }}>TIME</th>
                <th style={{ padding: '12px 14px', fontWeight: 700 }}>DECISION</th>
                <th style={{ padding: '12px 14px', fontWeight: 700 }}>COMMAND</th>
                <th style={{ padding: '12px 14px', fontWeight: 700 }}>RISK LEVEL</th>
                <th style={{ padding: '12px 14px', fontWeight: 700 }}>RECORD ID</th>
                <th style={{ padding: '12px 14px', fontWeight: 700, textAlign: 'right' }}>ACTION</th>
              </tr>
            </thead>
            <tbody>
              {filteredRecords.map((rec) => {
                const dec = rec.final_policy_decision.toUpperCase();
                const badgeClass =
                  dec === 'ALLOW' || dec === 'PERMITTED' || dec === 'PASSTHROUGH'
                    ? 'badge-allow'
                    : dec === 'REVIEW' || dec === 'PAUSED_FOR_APPROVAL'
                    ? 'badge-review'
                    : 'badge-block';

                return (
                  <tr
                    key={rec.record_id}
                    style={{
                      borderBottom: '1px solid var(--border-subtle)',
                      transition: 'background-color 0.15s ease',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-surface-hover)')}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <td style={{ padding: '14px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', fontSize: '12px' }}>
                      {new Date(rec.timestamp).toLocaleTimeString()}
                    </td>
                    <td style={{ padding: '14px' }}>
                      <span className={`badge ${badgeClass}`}>
                        {rec.final_policy_decision}
                      </span>
                    </td>
                    <td style={{ padding: '14px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', maxWidth: '380px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 600 }}>
                      {rec.command}
                    </td>
                    <td style={{ padding: '14px', fontFamily: 'var(--font-mono)', color: 'var(--accent-review)', fontWeight: 600 }}>
                      {rec.v03_risk || 'RISK_EVALUATED'}
                    </td>
                    <td style={{ padding: '14px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', fontSize: '12px' }}>
                      {rec.record_id}
                    </td>
                    <td style={{ padding: '14px', textAlign: 'right' }}>
                      <button
                        onClick={() => setSelectedRecord(rec)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--accent-primary)',
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          fontSize: '13px',
                          fontWeight: 600,
                        }}
                      >
                        <Eye size={15} />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {selectedRecord && (
        <div className="modal-overlay" onClick={() => setSelectedRecord(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)' }}>Audit Record Inspection</h3>
              <button onClick={() => setSelectedRecord(null)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '18px' }}>
                ✕
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '13px', fontFamily: 'var(--font-mono)' }}>
              <div><span style={{ color: 'var(--text-muted)' }}>RECORD ID:</span> <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{selectedRecord.record_id}</span></div>
              <div><span style={{ color: 'var(--text-muted)' }}>TIMESTAMP:</span> <span style={{ color: 'var(--text-primary)' }}>{selectedRecord.timestamp}</span></div>
              <div><span style={{ color: 'var(--text-muted)' }}>COMMAND:</span> <code style={{ color: 'var(--text-primary)', display: 'block', padding: '10px 14px', background: 'var(--input-bg)', borderRadius: '8px', marginTop: '6px', wordBreak: 'break-all' }}>{selectedRecord.command}</code></div>
              <div><span style={{ color: 'var(--text-muted)' }}>DECISION:</span> <span style={{ color: 'var(--accent-allow)', fontWeight: 700 }}>{selectedRecord.final_policy_decision}</span></div>
              <div><span style={{ color: 'var(--text-muted)' }}>REASONS:</span> <span style={{ color: 'var(--text-secondary)' }}>{selectedRecord.policy_reasons?.join(', ') || 'N/A'}</span></div>
              <div><span style={{ color: 'var(--text-muted)' }}>POLICY VERSION:</span> <span style={{ color: 'var(--text-secondary)' }}>{selectedRecord.policy_version}</span></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
