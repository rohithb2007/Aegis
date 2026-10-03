import React from 'react';
import { ShieldCheck, ShieldAlert, Search, RefreshCw, UserCheck, Sun, Moon } from 'lucide-react';
import type { GatewayStatus } from '../types/aegis';

interface TopBarProps {
  title: string;
  subtitle?: string;
  gatewayStatus: GatewayStatus | null;
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
  onRefresh: () => void;
  isRefreshing?: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({
  title,
  subtitle,
  gatewayStatus,
  theme,
  onToggleTheme,
  onRefresh,
  isRefreshing,
}) => {
  const isProtected = gatewayStatus?.protection_enabled && gatewayStatus?.status === 'RUNNING';

  return (
    <header style={{
      height: '76px',
      backgroundColor: 'var(--header-bg)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid var(--border-subtle)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 32px',
      position: 'sticky',
      top: 0,
      zIndex: 90,
      marginLeft: '260px',
      transition: 'all 0.2s ease',
    }}>
      <div>
        <h1 style={{
          fontSize: '22px',
          fontWeight: 800,
          color: 'var(--text-primary)',
          letterSpacing: '-0.01em',
          margin: 0,
          lineHeight: 1.2,
        }}>
          {title}
        </h1>
        {subtitle && (
          <p style={{
            fontSize: '13px',
            color: 'var(--text-secondary)',
            marginTop: '3px',
            fontWeight: 500,
          }}>
            {subtitle}
          </p>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
        }}>
          <Search size={14} color="var(--text-muted)" style={{ position: 'absolute', left: '12px' }} />
          <input
            type="text"
            placeholder="Search commands, IDs..."
            style={{
              backgroundColor: 'var(--input-bg)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '8px 12px 8px 34px',
              fontSize: '13px',
              color: 'var(--text-primary)',
              width: '220px',
              outline: 'none',
              fontFamily: 'var(--font-mono)',
            }}
          />
        </div>

        {/* Protection State Indicator */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 14px',
          borderRadius: '20px',
          backgroundColor: isProtected ? 'var(--accent-allow-bg)' : 'var(--accent-block-bg)',
          border: `1px solid ${isProtected ? 'var(--accent-allow-border)' : 'var(--accent-block-border)'}`,
        }}>
          {isProtected ? (
            <ShieldCheck size={16} color="var(--accent-allow)" />
          ) : (
            <ShieldAlert size={16} color="var(--accent-block)" />
          )}
          <span style={{
            fontSize: '13px',
            fontWeight: 700,
            color: isProtected ? 'var(--accent-allow)' : 'var(--accent-block)',
            letterSpacing: '0.02em',
          }}>
            {isProtected ? 'PROTECTED' : 'UNPROTECTED'}
          </span>
        </div>

        {/* Human Control Badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '6px 12px',
          borderRadius: '8px',
          backgroundColor: 'var(--bg-surface-elevated)',
          border: '1px solid var(--border-subtle)',
          fontSize: '13px',
          color: 'var(--text-secondary)',
          fontWeight: 600,
        }}>
          <UserCheck size={15} color="var(--accent-primary)" />
          <span>Human Control</span>
        </div>

        {/* Theme Toggle Button */}
        <button
          onClick={onToggleTheme}
          title={`Switch to ${theme === 'dark' ? 'Warm Off-White / Brown' : 'Dark Obsidian'} theme`}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 12px',
            borderRadius: '8px',
            backgroundColor: 'var(--bg-surface-elevated)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-primary)',
            fontSize: '13px',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
        >
          {theme === 'dark' ? (
            <>
              <Sun size={15} color="#F59E0B" />
              <span>Light</span>
            </>
          ) : (
            <>
              <Moon size={15} color="#38BDF8" />
              <span>Dark</span>
            </>
          )}
        </button>

        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          title="Refresh Dashboard Data"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            backgroundColor: 'var(--bg-surface-elevated)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
        >
          <RefreshCw
            size={15}
            style={{
              animation: isRefreshing ? 'spin 1s linear infinite' : 'none',
            }}
          />
        </button>
      </div>
    </header>
  );
};

