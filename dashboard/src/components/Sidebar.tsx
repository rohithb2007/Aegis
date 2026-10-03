import React from 'react';
import {
  ShieldAlert,
  LayoutDashboard,
  Activity,
  CheckSquare,
  Bot,
  FileText,
  Shield,
  Settings,
  Radio,
} from 'lucide-react';
import type { GatewayStatus } from '../types/aegis';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  gatewayStatus: GatewayStatus | null;
  pendingCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  gatewayStatus,
  pendingCount,
}) => {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'activity', label: 'Activity', icon: Activity },
    {
      id: 'approvals',
      label: 'Approvals',
      icon: CheckSquare,
      badge: pendingCount > 0 ? pendingCount : undefined,
    },
    { id: 'agents', label: 'Agents', icon: Bot },
    { id: 'audit', label: 'Audit Log', icon: FileText },
    { id: 'protection', label: 'Protection', icon: Shield },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  const isOnline = gatewayStatus?.status === 'RUNNING';

  return (
    <aside style={{
      width: '260px',
      backgroundColor: 'var(--sidebar-bg)',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      height: '100vh',
      position: 'fixed',
      left: 0,
      top: 0,
      zIndex: 100,
      transition: 'all 0.2s ease',
    }}>
      <div>
        {/* Brand Header */}
        <div style={{
          padding: '24px 20px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
        }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-primary-hover) 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 15px rgba(0, 0, 0, 0.2)',
          }}>
            <ShieldAlert size={24} color="#ffffff" />
          </div>
          <div>
            <div style={{
              fontSize: '18px',
              fontWeight: 800,
              letterSpacing: '0.05em',
              color: 'var(--text-primary)',
              lineHeight: 1.2,
            }}>
              AEGIS
            </div>
            <div style={{
              fontSize: '12px',
              color: 'var(--text-secondary)',
              fontWeight: 600,
            }}>
              Security Operations Center
            </div>
          </div>
        </div>

        {/* Navigation Items */}
        <nav style={{ padding: '16px 12px' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '11px 16px',
                  borderRadius: '10px',
                  border: 'none',
                  backgroundColor: isActive ? 'var(--bg-surface-hover)' : 'transparent',
                  color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                  fontWeight: isActive ? 700 : 500,
                  fontSize: '14px',
                  cursor: 'pointer',
                  marginBottom: '6px',
                  transition: 'all 0.15s ease',
                  textAlign: 'left',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Icon size={19} color={isActive ? 'var(--accent-primary)' : 'var(--text-muted)'} />
                  <span>{item.label}</span>
                </div>
                {item.badge !== undefined && (
                  <span style={{
                    backgroundColor: 'var(--accent-review)',
                    color: '#000000',
                    fontSize: '12px',
                    fontWeight: 800,
                    padding: '2px 8px',
                    borderRadius: '12px',
                    lineHeight: 1.2,
                  }}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Gateway Footer Info */}
      <div style={{
        padding: '18px 20px',
        borderTop: '1px solid var(--border-subtle)',
        backgroundColor: 'var(--bg-surface-elevated)',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '8px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Radio size={14} color={isOnline ? 'var(--accent-allow)' : 'var(--accent-block)'} />
            <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)' }}>
              Gateway
            </span>
          </div>
          <span style={{
            fontSize: '11px',
            fontWeight: 800,
            color: isOnline ? 'var(--accent-allow)' : 'var(--accent-block)',
            letterSpacing: '0.05em',
          }}>
            {isOnline ? 'ONLINE' : 'OFFLINE'}
          </span>
        </div>

        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
          127.0.0.1:{gatewayStatus?.port || 8765}
        </div>

        <div style={{
          marginTop: '10px',
          paddingTop: '8px',
          borderTop: '1px dashed var(--border-subtle)',
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: '12px',
          color: 'var(--text-secondary)',
        }}>
          <span>Version</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-primary)' }}>
            {gatewayStatus?.version || 'V1.1.0'}
          </span>
        </div>
      </div>
    </aside>
  );
};

