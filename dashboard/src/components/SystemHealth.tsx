import React from 'react';
import { Activity, Radio, Shield, CheckSquare, FileText, Cpu } from 'lucide-react';
import type { GatewayStatus, ProtectionStatusDict } from '../types/aegis';

interface SystemHealthProps {
  gatewayStatus: GatewayStatus | null;
  protection: ProtectionStatusDict | null;
}

export const SystemHealth: React.FC<SystemHealthProps> = ({ gatewayStatus, protection }) => {
  const isOnline = gatewayStatus?.status === 'RUNNING';
  const isProtectionOn = protection?.status === 'ON';

  const healthItems = [
    {
      name: 'Gateway Service',
      status: isOnline ? 'Healthy' : 'Offline',
      detail: isOnline ? '127.0.0.1:8765' : 'Disconnected',
      icon: Radio,
      ok: isOnline,
    },
    {
      name: 'Interceptor',
      status: 'Active',
      detail: 'PowerShell Pre-Exec',
      icon: Shield,
      ok: true,
    },
    {
      name: 'Protection Core',
      status: isProtectionOn ? 'Enabled' : 'Disabled',
      detail: isProtectionOn ? 'Human Control' : 'Passthrough',
      icon: Activity,
      ok: isProtectionOn,
    },
    {
      name: 'Approval Engine',
      status: 'Ready',
      detail: 'Exact-Command Binding',
      icon: CheckSquare,
      ok: true,
    },
    {
      name: 'Audit Logger',
      status: 'Recording',
      detail: 'Secret-Redacted',
      icon: FileText,
      ok: true,
    },
    {
      name: 'AI Supervisor',
      status: 'Available',
      detail: 'Deterministic + AI',
      icon: Cpu,
      ok: true,
    },
  ];

  return (
    <div className="glass-card" style={{ padding: '28px' }}>
      <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '18px', display: 'flex', alignItems: 'center', gap: '10px' }}>
        <Activity size={20} color="var(--accent-primary)" />
        <span>System Health & Components</span>
      </h3>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
        {healthItems.map((item) => {
          const Icon = item.icon;
          return (
            <div
              key={item.name}
              style={{
                backgroundColor: 'var(--input-bg)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '10px',
                padding: '14px 16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Icon size={18} color={item.ok ? 'var(--accent-allow)' : 'var(--accent-block)'} />
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {item.name}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 500 }}>
                    {item.detail}
                  </div>
                </div>
              </div>

              <span style={{
                fontSize: '12px',
                fontWeight: 800,
                color: item.ok ? 'var(--accent-allow)' : 'var(--accent-block)',
              }}>
                ● {item.status}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
