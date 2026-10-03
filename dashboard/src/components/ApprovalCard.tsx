import React from 'react';
import type { ApprovalRequest } from '../types/aegis';
import { ShieldAlert, Check, X, Eye, Clock } from 'lucide-react';

interface ApprovalCardProps {
  request: ApprovalRequest;
  onApprove: (requestId: string) => void;
  onDeny: (requestId: string) => void;
  onViewDetails: (request: ApprovalRequest) => void;
  isProcessing?: boolean;
}

export const ApprovalCard: React.FC<ApprovalCardProps> = ({
  request,
  onApprove,
  onDeny,
  onViewDetails,
  isProcessing,
}) => {
  const isPending = request.status === 'PENDING';

  const formatCreated = (isoStr: string) => {
    try {
      const date = new Date(isoStr);
      return date.toLocaleString();
    } catch {
      return isoStr;
    }
  };

  return (
    <div
      className="glass-card"
      style={{
        padding: '24px',
        border: isPending
          ? '1px solid var(--accent-review-border)'
          : '1px solid var(--border-subtle)',
        boxShadow: isPending ? '0 0 25px rgba(245, 158, 11, 0.08)' : 'none',
        marginBottom: '16px',
        position: 'relative',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldAlert size={18} color="var(--accent-review)" />
          <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--accent-review)', letterSpacing: '0.04em' }}>
            HUMAN APPROVAL REQUIRED
          </span>
        </div>

        <span style={{
          backgroundColor: 'var(--accent-review-bg)',
          color: 'var(--accent-review)',
          border: '1px solid var(--accent-review-border)',
          fontSize: '11px',
          fontWeight: 700,
          padding: '3px 8px',
          borderRadius: '4px',
          fontFamily: 'var(--font-mono)',
        }}>
          {request.risk_level || 'HIGH_RISK'}
        </span>
      </div>

      <div style={{
        backgroundColor: 'var(--input-bg)',
        border: '1px solid var(--border-medium)',
        borderRadius: '10px',
        padding: '16px 20px',
        marginBottom: '16px',
      }}>
        <code style={{
          fontSize: '15px',
          color: 'var(--text-primary)',
          fontWeight: 600,
          wordBreak: 'break-all',
          display: 'block',
        }}>
          {request.command}
        </code>
      </div>

      <p style={{
        fontSize: '14px',
        color: 'var(--text-secondary)',
        marginBottom: '16px',
        lineHeight: 1.6,
      }}>
        {request.explanation || 'Execution paused: command requires explicit human authorization.'}
      </p>

      {request.capabilities && request.capabilities.length > 0 && (
        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px', letterSpacing: '0.04em' }}>
            CAPABILITIES
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {request.capabilities.map((cap) => (
              <span key={cap} style={{
                backgroundColor: 'var(--bg-surface-elevated)',
                color: 'var(--accent-primary)',
                border: '1px solid var(--border-subtle)',
                fontSize: '12px',
                fontFamily: 'var(--font-mono)',
                padding: '4px 10px',
                borderRadius: '6px',
                fontWeight: 600,
              }}>
                {cap}
              </span>
            ))}
          </div>
        </div>
      )}

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: '10px',
        marginBottom: '20px',
        fontSize: '12px',
        fontFamily: 'var(--font-mono)',
        color: 'var(--text-muted)',
      }}>
        <div>REQUEST: <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{request.request_id}</span></div>
        {request.session_id && <div>SESSION: <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{request.session_id}</span></div>}
        {request.task_id && <div>TASK: <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{request.task_id}</span></div>}
      </div>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingTop: '16px',
        borderTop: '1px solid var(--border-subtle)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: 'var(--text-secondary)' }}>
          <Clock size={15} />
          <span>Created {formatCreated(request.created_at)}</span>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            className="btn btn-secondary"
            onClick={() => onViewDetails(request)}
            style={{ padding: '8px 16px', fontSize: '13px' }}
          >
            <Eye size={15} />
            <span>Details</span>
          </button>

          {isPending ? (
            <>
              <button
                className="btn btn-deny"
                disabled={isProcessing}
                onClick={() => onDeny(request.request_id)}
                style={{ opacity: isProcessing ? 0.6 : 1, padding: '8px 18px', fontSize: '13px' }}
              >
                <X size={16} />
                <span>DENY</span>
              </button>

              <button
                className="btn btn-approve"
                disabled={isProcessing}
                onClick={() => onApprove(request.request_id)}
                style={{ opacity: isProcessing ? 0.6 : 1, padding: '8px 18px', fontSize: '13px' }}
              >
                <Check size={16} />
                <span>APPROVE</span>
              </button>
            </>
          ) : (
            <span className={`badge ${request.status === 'APPROVED' ? 'badge-allow' : 'badge-block'}`}>
              {request.status}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
