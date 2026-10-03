import React from 'react';
import { WifiOff, RefreshCw, ShieldAlert } from 'lucide-react';

interface GatewayDisconnectedProps {
  onRetry: () => void;
  isRetrying?: boolean;
}

export const GatewayDisconnected: React.FC<GatewayDisconnectedProps> = ({
  onRetry,
  isRetrying,
}) => {
  return (
    <div style={{
      padding: '40px 24px',
      margin: '32px auto',
      maxWidth: '680px',
      backgroundColor: 'var(--accent-block-bg)',
      border: '1px solid var(--accent-block-border)',
      borderRadius: '16px',
      textAlign: 'center',
      boxShadow: 'var(--card-shadow)',
    }}>
      <div style={{
        width: '56px',
        height: '56px',
        borderRadius: '16px',
        backgroundColor: 'var(--card-bg)',
        border: '1px solid var(--accent-block-border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        margin: '0 auto 20px auto',
      }}>
        <WifiOff size={30} color="var(--accent-block)" />
      </div>

      <h2 style={{ fontSize: '22px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>
        GATEWAY CONNECTION LOST
      </h2>

      <div style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        fontSize: '13px',
        fontWeight: 700,
        color: 'var(--accent-block)',
        backgroundColor: 'var(--accent-block-bg)',
        border: '1px solid var(--accent-block-border)',
        padding: '6px 14px',
        borderRadius: '20px',
        marginBottom: '16px',
      }}>
        ● Dashboard Disconnected (127.0.0.1:8765)
      </div>

      <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '16px', lineHeight: 1.6 }}>
        Protection state cannot be confirmed from the dashboard interface.
      </p>

      {/* Critical Fail-Closed Notice */}
      <div style={{
        backgroundColor: 'var(--card-bg)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '10px',
        padding: '16px',
        fontSize: '13px',
        color: 'var(--text-secondary)',
        textAlign: 'left',
        marginBottom: '24px',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px',
      }}>
        <ShieldAlert size={20} color="var(--accent-review)" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div>
          <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: '4px' }}>
            Fail-Closed Security Protection Invariant
          </strong>
          The Aegis PowerShell interceptor continues to enforce its own fail-closed security behavior when Protection is ON. Proposed commands are automatically blocked (Exit code 3) until Gateway communication is re-established.
        </div>
      </div>

      <button
        className="btn btn-primary"
        onClick={onRetry}
        disabled={isRetrying}
        style={{ padding: '10px 24px', fontSize: '14px' }}
      >
        <RefreshCw size={16} className={isRetrying ? 'spin' : ''} />
        <span>RETRY CONNECTION</span>
      </button>
    </div>
  );
};
