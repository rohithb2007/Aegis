import React from 'react';
import type { AuditRecord } from '../types/aegis';
import { ShieldCheck, AlertCircle, ShieldOff } from 'lucide-react';

interface ActivityTimelineProps {
  records: AuditRecord[];
}

export const ActivityTimeline: React.FC<ActivityTimelineProps> = ({ records }) => {
  const recentTimeline = records.slice(0, 6);

  if (recentTimeline.length === 0) {
    return (
      <div style={{ color: 'var(--text-muted)', fontSize: '13px', padding: '16px 0' }}>
        No timeline activity recorded yet.
      </div>
    );
  }

  const getTimelineIcon = (decision: string) => {
    const decUpper = decision.toUpperCase();
    if (decUpper === 'ALLOW' || decUpper === 'PERMITTED' || decUpper === 'PASSTHROUGH') {
      return { Icon: ShieldCheck, color: 'var(--accent-allow)' };
    }
    if (decUpper === 'REVIEW' || decUpper === 'PAUSED_FOR_APPROVAL') {
      return { Icon: AlertCircle, color: 'var(--accent-review)' };
    }
    return { Icon: ShieldOff, color: 'var(--accent-block)' };
  };

  const formatTime = (isoStr: string) => {
    try {
      return new Date(isoStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoStr;
    }
  };

  return (
    <div style={{ paddingLeft: '8px', position: 'relative' }}>
      {recentTimeline.map((item, idx) => {
        const { Icon, color } = getTimelineIcon(item.final_policy_decision);
        const isLast = idx === recentTimeline.length - 1;

        return (
          <div key={item.record_id} style={{ display: 'flex', gap: '16px', position: 'relative', marginBottom: isLast ? 0 : '20px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <div style={{
                width: '28px',
                height: '28px',
                borderRadius: '50%',
                backgroundColor: 'var(--bg-surface-elevated)',
                border: `2px solid ${color}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 2,
              }}>
                <Icon size={14} color={color} />
              </div>
              {!isLast && (
                <div style={{
                  width: '2px',
                  flexGrow: 1,
                  backgroundColor: 'var(--border-subtle)',
                  marginTop: '4px',
                  marginBottom: '-4px',
                }} />
              )}
            </div>

            <div style={{ flex: 1, paddingTop: '2px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ fontSize: '13px', fontWeight: 700, color: color }}>
                  {item.final_policy_decision}
                </span>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                  {formatTime(item.timestamp)}
                </span>
              </div>

              <code style={{
                fontSize: '13px',
                color: 'var(--text-primary)',
                fontWeight: 600,
                display: 'block',
                marginBottom: '4px',
                wordBreak: 'break-all',
              }}>
                {item.command}
              </code>

              <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                {item.policy_reasons && item.policy_reasons[0] ? item.policy_reasons[0] : 'Evaluated by policy boundary.'}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
};
