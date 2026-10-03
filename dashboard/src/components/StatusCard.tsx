import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface StatusCardProps {
  title: string;
  value: string;
  subtitle: string;
  icon: LucideIcon;
  status: 'green' | 'amber' | 'red' | 'blue';
}

export const StatusCard: React.FC<StatusCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  status,
}) => {
  const getStatusColor = () => {
    switch (status) {
      case 'green':
        return {
          badge: 'var(--accent-allow-bg)',
          text: 'var(--accent-allow)',
          border: 'var(--accent-allow-border)',
        };
      case 'amber':
        return {
          badge: 'var(--accent-review-bg)',
          text: 'var(--accent-review)',
          border: 'var(--accent-review-border)',
        };
      case 'red':
        return {
          badge: 'var(--accent-block-bg)',
          text: 'var(--accent-block)',
          border: 'var(--accent-block-border)',
        };
      default:
        return {
          badge: 'var(--accent-system-bg)',
          text: 'var(--accent-system)',
          border: 'var(--accent-system-border)',
        };
    }
  };

  const colors = getStatusColor();

  return (
    <div className="glass-card" style={{ padding: '22px', position: 'relative', overflow: 'hidden' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '12px',
      }}>
        <span style={{
          fontSize: '12px',
          fontWeight: 700,
          color: 'var(--text-muted)',
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}>
          {title}
        </span>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '10px',
          backgroundColor: colors.badge,
          border: `1px solid ${colors.border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <Icon size={18} color={colors.text} />
        </div>
      </div>

      <div style={{
        fontSize: '24px',
        fontWeight: 800,
        color: 'var(--text-primary)',
        marginBottom: '6px',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        lineHeight: 1.2,
      }}>
        <span>{value}</span>
      </div>

      <div style={{
        fontSize: '13px',
        color: 'var(--text-secondary)',
        fontWeight: 500,
      }}>
        {subtitle}
      </div>
    </div>
  );
};
