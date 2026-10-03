import React from 'react';
import type { GatewayStatus } from '../types/aegis';
import { Settings, Server, Lock, Cpu, Database, Palette, Check } from 'lucide-react';

interface SettingsPageProps {
  gatewayStatus: GatewayStatus | null;
  theme?: 'dark' | 'light';
  onSetTheme?: (theme: 'dark' | 'light') => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({
  gatewayStatus,
  theme = 'dark',
  onSetTheme,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="glass-card" style={{ padding: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '8px' }}>
          <Settings size={28} color="var(--accent-primary)" />
          <h2 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--text-primary)' }}>
            System Settings & Local Configuration
          </h2>
        </div>
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          Localhost security parameters, Gateway socket configuration, policy engine rulesets, visual themes, and workspace root settings.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px' }}>
        {/* Theme Selection Card */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Palette size={20} color="var(--accent-primary)" />
            <span>Dashboard Appearance & Theme</span>
          </h3>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '16px', lineHeight: 1.5 }}>
            Choose your preferred aesthetic. Selections persist automatically across browser sessions.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <button
              onClick={() => onSetTheme?.('dark')}
              style={{
                padding: '16px',
                borderRadius: '12px',
                backgroundColor: '#11141A',
                border: `2px solid ${theme === 'dark' ? '#38BDF8' : '#262C36'}`,
                color: '#F8FAFC',
                cursor: 'pointer',
                textAlign: 'left',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                transition: 'all 0.15s ease',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '14px', fontWeight: 700 }}>Dark Obsidian</span>
                {theme === 'dark' && <Check size={16} color="#38BDF8" />}
              </div>
              <span style={{ fontSize: '12px', color: '#94A3B8' }}>SOC Cyber Command aesthetic</span>
            </button>

            <button
              onClick={() => onSetTheme?.('light')}
              style={{
                padding: '16px',
                borderRadius: '12px',
                backgroundColor: '#FFFDFC',
                border: `2px solid ${theme === 'light' ? '#B95F38' : '#E4D8CC'}`,
                color: '#33261F',
                cursor: 'pointer',
                textAlign: 'left',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                transition: 'all 0.15s ease',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '14px', fontWeight: 700 }}>Warm Off-White</span>
                {theme === 'light' && <Check size={16} color="#B95F38" />}
              </div>
              <span style={{ fontSize: '12px', color: '#76675D' }}>Warm Sepia & Terracotta theme</span>
            </button>
          </div>
        </div>

        {/* Localhost Security Bound */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Lock size={20} color="var(--accent-allow)" />
            <span>Localhost-Only Security Bound</span>
          </h3>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '14px', lineHeight: 1.5 }}>
            Aegis operates strictly on localhost (`127.0.0.1:8765`). It does NOT listen on `0.0.0.0`, connect to external cloud servers, send remote telemetry, or support remote approval.
          </p>
          <div style={{
            fontSize: '13px',
            fontFamily: 'var(--font-mono)',
            backgroundColor: 'var(--bg-surface-elevated)',
            padding: '12px 16px',
            borderRadius: '8px',
            color: 'var(--accent-primary)',
            border: '1px solid var(--border-subtle)',
            fontWeight: 600,
          }}>
            HTTP_LISTEN: 127.0.0.1:{gatewayStatus?.port || 8765}
          </div>
        </div>

        {/* Workspace Boundary */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Server size={20} color="var(--accent-system)" />
            <span>Workspace Boundary</span>
          </h3>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '14px', lineHeight: 1.5 }}>
            Workspace root directory enforced by Aegis boundary validation:
          </p>
          <div style={{
            fontSize: '13px',
            fontFamily: 'var(--font-mono)',
            backgroundColor: 'var(--bg-surface-elevated)',
            padding: '12px 16px',
            borderRadius: '8px',
            color: 'var(--text-primary)',
            wordBreak: 'break-all',
            border: '1px solid var(--border-subtle)',
          }}>
            {gatewayStatus?.workspace_root || 'd:\\Projects\\Real Projects\\Aegis'}
          </div>
        </div>

        {/* Policy Engine Ruleset */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Cpu size={20} color="var(--accent-review)" />
            <span>Policy Engine Ruleset</span>
          </h3>
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', color: 'var(--text-secondary)' }}>
            <li>• Safe Read / Test Commands: <strong style={{ color: 'var(--accent-allow)' }}>ALLOW</strong></li>
            <li>• Remote State / Destructive Actions: <strong style={{ color: 'var(--accent-review)' }}>REVIEW</strong></li>
            <li>• System Boundary Violations: <strong style={{ color: 'var(--accent-block)' }}>BLOCK</strong></li>
            <li>• Secret Redaction: <strong>ALWAYS ACTIVE</strong></li>
          </ul>
        </div>

        {/* Interceptor Installation */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Database size={20} color="var(--accent-primary)" />
            <span>Interceptor Installation</span>
          </h3>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
            PowerShell Pre-Execution Interceptor registered in WindowsPowerShell profile.
          </p>
          <div style={{ fontSize: '13px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', fontWeight: 600 }}>
            Idempotent: YES • Preserves Profile: YES
          </div>
        </div>
      </div>
    </div>
  );
};

