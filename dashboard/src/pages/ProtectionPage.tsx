import React from 'react';
import type { ProtectionStatusDict, GatewayStatus } from '../types/aegis';
import { ProtectionPanel } from '../components/ProtectionPanel';
import { Shield } from 'lucide-react';

interface ProtectionPageProps {
  protection: ProtectionStatusDict | null;
  gatewayStatus: GatewayStatus | null;
  onToggleProtection: (targetState: 'ON' | 'OFF') => void;
  isProcessing?: boolean;
}

export const ProtectionPage: React.FC<ProtectionPageProps> = ({
  protection,
  gatewayStatus,
  onToggleProtection,
  isProcessing,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
          <Shield size={24} color="var(--accent-allow)" />
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#ffffff' }}>
            Aegis Protection Settings & Invariants
          </h2>
        </div>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          Human-controlled security state, fail-closed policy invariants, and interceptor status.
        </p>
      </div>

      <ProtectionPanel
        protection={protection}
        gatewayStatus={gatewayStatus}
        onToggleProtection={onToggleProtection}
        isProcessing={isProcessing}
      />
    </div>
  );
};
