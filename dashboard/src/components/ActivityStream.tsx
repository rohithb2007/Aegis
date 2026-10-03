import React, { useState } from 'react';
import type { AuditRecord } from '../types/aegis';
import { CheckCircle2, AlertTriangle, XCircle, Info, ChevronDown, ChevronUp } from 'lucide-react';

interface ActivityStreamProps {
  records: AuditRecord[];
  limit?: number;
}

export const ActivityStream: React.FC<ActivityStreamProps> = ({ records, limit = 10 }) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const displayRecords = records.slice(0, limit);

  if (displayRecords.length === 0) {
    return (
      <div className="glass-card" style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
        <Info size={28} style={{ marginBottom: '8px', opacity: 0.6 }} />
        <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-secondary)' }}>
          No security events evaluated yet.
        </div>
        <div style={{ fontSize: '12px', marginTop: '4px' }}>
          Interception activity evaluated by Aegis will stream here in real time.
        </div>
      </div>
    );
  }

  const getDecisionBadge = (decision: string) => {
    const decUpper = decision.toUpperCase();
    if (decUpper === 'ALLOW' || decUpper === 'PERMITTED' || decUpper === 'PASSTHROUGH') {
      return {
        badgeClass: 'badge-allow',
        icon: CheckCircle2,
        label: 'ALLOW',
      };
    }
    if (decUpper === 'REVIEW' || decUpper === 'PAUSED_FOR_APPROVAL') {
      return {
        badgeClass: 'badge-review',
        icon: AlertTriangle,
        label: 'REVIEW',
      };
    }
    return {
      badgeClass: 'badge-block',
      icon: XCircle,
      label: 'BLOCK',
    };
  };

  const formatTime = (isoStr: string) => {
    try {
      const date = new Date(isoStr);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoStr;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {displayRecords.map((rec) => {
        const decisionInfo = getDecisionBadge(rec.final_policy_decision);
        const Icon = decisionInfo.icon;
        const isExpanded = expandedId === rec.record_id;

        return (
          <div
            key={rec.record_id}
            className="glass-card"
            style={{
              padding: '16px 20px',
              cursor: 'pointer',
            }}
            onClick={() => setExpandedId(isExpanded ? null : rec.record_id)}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flex: 1 }}>
                <span className={`badge ${decisionInfo.badgeClass}`}>
                  <Icon size={14} />
                  {decisionInfo.label}
                </span>

                <code style={{
                  fontSize: '14px',
                  color: 'var(--text-primary)',
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  maxWidth: '520px',
                }}>
                  {rec.command}
                </code>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <span style={{
                  fontSize: '12px',
                  color: 'var(--text-secondary)',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 500,
                }}>
                  {formatTime(rec.timestamp)}
                </span>
                {isExpanded ? (
                  <ChevronUp size={18} color="var(--text-secondary)" />
                ) : (
                  <ChevronDown size={18} color="var(--text-secondary)" />
                )}
              </div>
            </div>

            {isExpanded && (
              <div style={{
                marginTop: '16px',
                paddingTop: '14px',
                borderTop: '1px solid var(--border-subtle)',
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '14px',
                fontSize: '13px',
              }}>
                <div>
                  <div style={{ color: 'var(--text-muted)', marginBottom: '4px', fontWeight: 700, fontSize: '12px' }}>
                    EXPLANATION / REASONS
                  </div>
                  <div style={{ color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    {rec.policy_reasons && rec.policy_reasons.length > 0
                      ? rec.policy_reasons.join(', ')
                      : 'Evaluated by Aegis Security Engine.'}
                  </div>
                </div>

                <div>
                  <div style={{ color: 'var(--text-muted)', marginBottom: '4px', fontWeight: 700, fontSize: '12px' }}>
                    RISK & CAPABILITIES
                  </div>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <span style={{
                      padding: '3px 8px',
                      borderRadius: '6px',
                      backgroundColor: 'var(--bg-surface-elevated)',
                      color: 'var(--accent-review)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '12px',
                      fontWeight: 600,
                    }}>
                      {rec.v03_risk || 'RISK_ANALYZED'}
                    </span>
                    {rec.capabilities && rec.capabilities.map((cap) => (
                      <span key={cap} style={{
                        padding: '3px 8px',
                        borderRadius: '6px',
                        backgroundColor: 'var(--bg-surface-elevated)',
                        color: 'var(--accent-primary)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '12px',
                        fontWeight: 600,
                      }}>
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>

                <div style={{ gridColumn: 'span 2', display: 'flex', gap: '24px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                  <span>Record: <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{rec.record_id}</span></span>
                  {rec.session_id && <span>Session: <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{rec.session_id}</span></span>}
                  {rec.task_id && <span>Task: <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{rec.task_id}</span></span>}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
