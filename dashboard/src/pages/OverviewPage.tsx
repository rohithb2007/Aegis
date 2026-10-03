import React from 'react';
import type {
  GatewayStatus,
  ApprovalRequest,
  AuditRecord,
  ProtectionStatusDict,
  AgentTaskInfo,
} from '../types/aegis';
import { StatusCard } from '../components/StatusCard';
import { ActivityStream } from '../components/ActivityStream';
import { ActivityTimeline } from '../components/ActivityTimeline';
import { SystemHealth } from '../components/SystemHealth';
import { ApprovalCard } from '../components/ApprovalCard';
import { ShieldCheck, Radio, Shield, Bot, CheckSquare, Activity, BarChart3 } from 'lucide-react';

interface OverviewPageProps {
  gatewayStatus: GatewayStatus | null;
  protection: ProtectionStatusDict | null;
  requests: ApprovalRequest[];
  audits: AuditRecord[];
  tasks: AgentTaskInfo[];
  onApprove: (requestId: string) => void;
  onDeny: (requestId: string) => void;
  onViewDetails: (request: ApprovalRequest) => void;
  isProcessing?: boolean;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  gatewayStatus,
  protection,
  requests,
  audits,
  onApprove,
  onDeny,
  onViewDetails,
  isProcessing,
}) => {
  const pendingRequests = requests.filter((r) => r.status === 'PENDING');

  const totalEvaluated = gatewayStatus?.total_evaluated ?? audits.length;
  const allowCount = audits.filter((a) => {
    const dec = a.final_policy_decision.toUpperCase();
    return dec === 'ALLOW' || dec === 'PERMITTED' || dec === 'PASSTHROUGH';
  }).length;
  const reviewCount = audits.filter((a) => {
    const dec = a.final_policy_decision.toUpperCase();
    return dec === 'REVIEW' || dec === 'PAUSED_FOR_APPROVAL';
  }).length;
  const blockCount = audits.filter((a) => {
    const dec = a.final_policy_decision.toUpperCase();
    return dec === 'BLOCK' || dec === 'REJECTED_POLICY';
  }).length;

  const isProtectionOn = protection?.status === 'ON' || gatewayStatus?.protection_enabled;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
        <StatusCard
          title="PROTECTION STATE"
          value={isProtectionOn ? '● ON' : '● OFF'}
          subtitle={isProtectionOn ? 'Human Controlled Supervision' : 'Passthrough Mode'}
          icon={ShieldCheck}
          status={isProtectionOn ? 'green' : 'red'}
        />

        <StatusCard
          title="GATEWAY SERVICE"
          value={gatewayStatus?.status === 'RUNNING' ? '● ONLINE' : '● OFFLINE'}
          subtitle={`127.0.0.1:${gatewayStatus?.port || 8765}`}
          icon={Radio}
          status={gatewayStatus?.status === 'RUNNING' ? 'green' : 'red'}
        />

        <StatusCard
          title="INTERCEPTOR STATUS"
          value="● ACTIVE"
          subtitle="PowerShell Pre-Execution"
          icon={Shield}
          status="green"
        />

        <StatusCard
          title="AGENT STATUS"
          value="● MONITORED"
          subtitle="Antigravity Trajectory"
          icon={Bot}
          status="blue"
        />
      </div>

      <div className="glass-card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BarChart3 size={18} color="#38bdf8" />
            <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#ffffff' }}>
              SECURITY EVALUATION METRICS
            </h3>
          </div>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Real Backend Telemetry
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', textAlign: 'center' }}>
          <div style={{ backgroundColor: 'var(--bg-dark)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '20px', fontWeight: 700, color: '#ffffff' }}>{totalEvaluated}</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>Total Evaluated</div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-dark)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--accent-allow)' }}>{allowCount}</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>Allowed</div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-dark)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--accent-review)' }}>{reviewCount}</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>Paused for Review</div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-dark)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--accent-block)' }}>{blockCount}</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>Blocked</div>
          </div>
        </div>
      </div>

      {pendingRequests.length > 0 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <CheckSquare size={18} color="var(--accent-review)" />
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--accent-review)' }}>
              Action Required ({pendingRequests.length} Pending Approval)
            </h3>
          </div>

          {pendingRequests.slice(0, 2).map((req) => (
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

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <Activity size={18} color="#38bdf8" />
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#ffffff' }}>
              Security Evaluation Stream
            </h3>
          </div>
          <ActivityStream records={audits} limit={8} />
        </div>

        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <Radio size={18} color="var(--accent-allow)" />
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#ffffff' }}>
              Live Timeline
            </h3>
          </div>
          <div className="glass-card" style={{ padding: '20px' }}>
            <ActivityTimeline records={audits} />
          </div>
        </div>
      </div>

      <SystemHealth gatewayStatus={gatewayStatus} protection={protection} />
    </div>
  );
};
