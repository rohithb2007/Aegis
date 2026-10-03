import React from 'react';
import type { ApprovalRequest } from '../types/aegis';
import { X, ShieldAlert, Check, AlertTriangle, FileCode, Layers, Cpu } from 'lucide-react';

interface ApprovalDrawerProps {
  request: ApprovalRequest | null;
  onClose: () => void;
  onApprove: (requestId: string) => void;
  onDeny: (requestId: string) => void;
  isProcessing?: boolean;
}

export const ApprovalDrawer: React.FC<ApprovalDrawerProps> = ({
  request,
  onClose,
  onApprove,
  onDeny,
  isProcessing,
}) => {
  if (!request) return null;

  const isPending = request.status === 'PENDING';

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content"
        style={{ maxWidth: '640px', width: '90%' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '20px',
          paddingBottom: '16px',
          borderBottom: '1px solid var(--border-subtle)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ShieldAlert size={20} color="var(--accent-review)" />
            <h2 style={{ fontSize: '18px', fontWeight: 700, color: '#ffffff' }}>
              Approval Details & Explainability
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '4px',
            }}
          >
            <X size={20} />
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px' }}>
              <FileCode size={14} />
              <span>COMMAND</span>
            </div>
            <div style={{
              backgroundColor: 'var(--bg-dark)',
              border: '1px solid var(--border-medium)',
              borderRadius: '8px',
              padding: '12px 16px',
            }}>
              <code style={{ fontSize: '14px', color: '#ffffff', fontWeight: 600, wordBreak: 'break-all' }}>
                {request.command}
              </code>
            </div>
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px' }}>
              <AlertTriangle size={14} color="var(--accent-review)" />
              <span>WHY AEGIS PAUSED IT</span>
            </div>
            <div style={{
              backgroundColor: 'var(--accent-review-bg)',
              border: '1px solid var(--accent-review-border)',
              borderRadius: '8px',
              padding: '12px 16px',
              color: 'var(--text-primary)',
              fontSize: '13px',
              lineHeight: 1.5,
            }}>
              {request.explanation || 'Execution paused by Aegis Policy Engine: action modifies environment state or sensitive boundaries.'}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <div>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px' }}>
                TECHNICAL RISK
              </div>
              <span style={{
                display: 'inline-block',
                backgroundColor: 'var(--bg-surface-elevated)',
                color: 'var(--accent-review)',
                border: '1px solid var(--accent-review-border)',
                fontSize: '12px',
                fontWeight: 700,
                padding: '4px 10px',
                borderRadius: '6px',
                fontFamily: 'var(--font-mono)',
              }}>
                {request.risk_level || 'HIGH_RISK'}
              </span>
            </div>

            <div>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px' }}>
                POLICY DECISION
              </div>
              <span className="badge badge-review">
                PAUSED_FOR_APPROVAL
              </span>
            </div>
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px' }}>
              <Layers size={14} />
              <span>CAPABILITIES DETECTED</span>
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {request.capabilities && request.capabilities.length > 0 ? (
                request.capabilities.map((cap) => (
                  <span key={cap} style={{
                    backgroundColor: 'var(--bg-surface-elevated)',
                    color: '#38bdf8',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono)',
                    padding: '4px 10px',
                    borderRadius: '6px',
                  }}>
                    {cap}
                  </span>
                ))
              ) : (
                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>General execution capability</span>
              )}
            </div>
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px' }}>
              <Cpu size={14} color="#6366f1" />
              <span>AI SUPERVISOR VERDICT</span>
            </div>
            <div style={{
              backgroundColor: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '12px 16px',
              fontSize: '12px',
              color: 'var(--text-secondary)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <span>Verdict: <strong style={{ color: '#ffffff' }}>{request.verdict || 'QUESTIONABLE'}</strong></span>
              <span>Policy: <strong style={{ color: 'var(--accent-review)' }}>REVIEW</strong></span>
            </div>
          </div>
        </div>

        <div style={{
          marginTop: '24px',
          paddingTop: '16px',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>

          {isPending && (
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                className="btn btn-deny"
                disabled={isProcessing}
                onClick={() => {
                  onDeny(request.request_id);
                  onClose();
                }}
              >
                <X size={15} />
                <span>DENY</span>
              </button>

              <button
                className="btn btn-approve"
                disabled={isProcessing}
                onClick={() => {
                  onApprove(request.request_id);
                  onClose();
                }}
              >
                <Check size={15} />
                <span>APPROVE</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
