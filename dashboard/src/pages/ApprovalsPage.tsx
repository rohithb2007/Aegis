import React from 'react';
import type { ApprovalRequest } from '../types/aegis';
import { ApprovalCard } from '../components/ApprovalCard';
import { CheckSquare, Info } from 'lucide-react';

interface ApprovalsPageProps {
  requests: ApprovalRequest[];
  onApprove: (requestId: string) => void;
  onDeny: (requestId: string) => void;
  onViewDetails: (request: ApprovalRequest) => void;
  isProcessing?: boolean;
}

export const ApprovalsPage: React.FC<ApprovalsPageProps> = ({
  requests,
  onApprove,
  onDeny,
  onViewDetails,
  isProcessing,
}) => {
  const pendingRequests = requests.filter((r) => r.status === 'PENDING');
  const pastRequests = requests.filter((r) => r.status !== 'PENDING');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
          <CheckSquare size={24} color="var(--accent-review)" />
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#ffffff' }}>
            Human Approval Center
          </h2>
        </div>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          Actions waiting for your explicit human decision. Aegis pauses proposed risky agent commands and requires manual authorization before execution is allowed.
        </p>
      </div>

      <div>
        <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--accent-review)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>Pending Approvals ({pendingRequests.length})</span>
        </h3>

        {pendingRequests.length === 0 ? (
          <div className="glass-card" style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Info size={28} style={{ marginBottom: '8px', opacity: 0.6 }} />
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-secondary)' }}>
              No actions currently waiting for human approval.
            </div>
            <div style={{ fontSize: '12px', marginTop: '4px' }}>
              When Antigravity proposes a risky command (e.g. force push, remote state change), it will pause here for authorization.
            </div>
          </div>
        ) : (
          pendingRequests.map((req) => (
            <ApprovalCard
              key={req.request_id}
              request={req}
              onApprove={onApprove}
              onDeny={onDeny}
              onViewDetails={onViewDetails}
              isProcessing={isProcessing}
            />
          ))
        )}
      </div>

      {pastRequests.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '14px' }}>
            Past Approval History ({pastRequests.length})
          </h3>

          {pastRequests.map((req) => (
            <ApprovalCard
              key={req.request_id}
              request={req}
              onApprove={onApprove}
              onDeny={onDeny}
              onViewDetails={onViewDetails}
              isProcessing={isProcessing}
            />
          ))}
        </div>
      )}
    </div>
  );
};
