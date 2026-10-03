export interface GatewayStatus {
  status: 'RUNNING' | 'OFFLINE';
  version: string;
  port: number;
  protection_status: 'ON' | 'OFF';
  protection_enabled: boolean;
  workspace_root: string;
  total_evaluated: number;
  pending_approvals: number;
}

export interface ApprovalRequest {
  request_id: string;
  command: string;
  status: 'PENDING' | 'APPROVED' | 'DENIED' | 'EXPIRED' | 'CANCELLED';
  risk_level: string;
  capabilities: string[];
  created_at: string;
  session_id?: string | null;
  task_id?: string | null;
  explanation?: string;
  reasons?: string[];
  verdict?: string | null;
}

export interface AuditRecord {
  record_id: string;
  timestamp: string;
  command: string;
  v03_risk: string;
  risk_score: number;
  capabilities: string[];
  final_policy_decision: 'ALLOW' | 'REVIEW' | 'BLOCK' | 'PASSTHROUGH' | string;
  policy_reasons: string[];
  event_id?: string | null;
  session_id?: string | null;
  task_id?: string | null;
  v04_verdict?: string | null;
  v04_confidence?: string | null;
  v05_route?: string | null;
  approval_status?: string | null;
  policy_version: string;
}

export interface AgentTaskInfo {
  task_id: string;
  status: 'WAITING_FOR_APPROVAL' | 'RUNNING' | 'BLOCKED';
  last_command: string;
  request_id?: string;
}

export interface ProtectionStatusDict {
  enabled: boolean;
  status: 'ON' | 'OFF';
  updated_at?: string;
  updated_by?: string;
}

export interface SystemHealthInfo {
  gateway: 'healthy' | 'offline';
  interceptor: 'active' | 'inactive';
  protection: 'enabled' | 'disabled';
  approvalEngine: 'ready' | 'degraded';
  auditLogger: 'recording' | 'offline';
  aiSupervisor: 'available' | 'offline';
}
