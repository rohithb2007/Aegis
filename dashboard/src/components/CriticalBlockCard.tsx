import React from 'react';
import { OctagonAlert, ShieldOff } from 'lucide-react';

interface CriticalBlockCardProps {
  command: string;
  reason?: string;
}

export const CriticalBlockCard: React.FC<CriticalBlockCardProps> = ({
  command,
  reason,
}) => {
  return (
    <div
      className="glass-card"
      style={{
        padding: '24px',
        border: '1px solid var(--accent-block-border)',
        backgroundColor: 'var(--accent-block-bg)',
        marginBottom: '16px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '10px',
          backgroundColor: 'var(--accent-block-bg)',
          border: '1px solid var(--accent-block-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <OctagonAlert size={20} color="var(--accent-block)" />
        </div>
        <div>
          <div style={{ fontSize: '15px', fontWeight: 800, color: 'var(--accent-block)', letterSpacing: '0.04em' }}>
            ⛔ ACTION BLOCKED BY CRITICAL POLICY
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 600 }}>
            System Boundary Protection Invariant D
          </div>
        </div>
      </div>

      {/* Blocked Command */}
      <div style={{
        backgroundColor: 'var(--input-bg)',
        border: '1px solid var(--accent-block-border)',
        borderRadius: '10px',
        padding: '16px 20px',
        marginBottom: '16px',
      }}>
        <code style={{ fontSize: '15px', color: 'var(--text-primary)', fontWeight: 600, wordBreak: 'break-all', display: 'block' }}>
          {command}
        </code>
      </div>

      <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '16px', lineHeight: 1.6 }}>
        {reason || 'This action targets a critical system directory or destructive operation outside authorized workspace boundaries.'}
      </p>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        fontSize: '13px',
        fontWeight: 700,
        color: 'var(--accent-block)',
        padding: '10px 14px',
        backgroundColor: 'var(--accent-block-bg)',
        borderRadius: '8px',
        border: '1px solid var(--accent-block-border)',
      }}>
        <ShieldOff size={16} />
        <span>Human approval cannot override this decision. Policy decision is non-negotiable.</span>
      </div>
    </div>
  );
};

