import type {
  GatewayStatus,
  ApprovalRequest,
  AuditRecord,
  AgentTaskInfo,
  ProtectionStatusDict,
} from '../types/aegis';

const GATEWAY_BASE_URL = 'http://127.0.0.1:8765';

export class AegisApi {
  static async getStatus(): Promise<GatewayStatus> {
    const res = await fetch(`${GATEWAY_BASE_URL}/status`, { cache: 'no-store' });
    if (!res.ok) {
      throw new Error(`Gateway returned HTTP ${res.status}`);
    }
    return await res.json();
  }

  static async getRequests(): Promise<ApprovalRequest[]> {
    const res = await fetch(`${GATEWAY_BASE_URL}/requests`, { cache: 'no-store' });
    if (!res.ok) {
      throw new Error(`Gateway returned HTTP ${res.status}`);
    }
    const data = await res.json();
    return data.requests || [];
  }

  static async getRecentAudit(limit = 50): Promise<AuditRecord[]> {
    const res = await fetch(`${GATEWAY_BASE_URL}/audit/recent?limit=${limit}`, { cache: 'no-store' });
    if (!res.ok) {
      throw new Error(`Gateway returned HTTP ${res.status}`);
    }
    const data = await res.json();
    return data.recent_logs || [];
  }

  static async getTasks(): Promise<AgentTaskInfo[]> {
    const res = await fetch(`${GATEWAY_BASE_URL}/tasks`, { cache: 'no-store' });
    if (!res.ok) {
      throw new Error(`Gateway returned HTTP ${res.status}`);
    }
    const data = await res.json();
    return data.tasks || [];
  }

  static async getProtection(): Promise<ProtectionStatusDict> {
    const res = await fetch(`${GATEWAY_BASE_URL}/protection`, { cache: 'no-store' });
    if (!res.ok) {
      throw new Error(`Gateway returned HTTP ${res.status}`);
    }
    return await res.json();
  }

  static async approveRequest(requestId: string): Promise<{ status: string; request_id: string }> {
    const res = await fetch(`${GATEWAY_BASE_URL}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request_id: requestId }),
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.error || `Failed to approve request ${requestId}`);
    }
    return await res.json();
  }

  static async denyRequest(requestId: string): Promise<{ status: string; request_id: string }> {
    const res = await fetch(`${GATEWAY_BASE_URL}/deny`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request_id: requestId }),
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.error || `Failed to deny request ${requestId}`);
    }
    return await res.json();
  }

  static async setProtection(state: 'ON' | 'OFF'): Promise<{ status: string; details: ProtectionStatusDict }> {
    const res = await fetch(`${GATEWAY_BASE_URL}/protection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ state }),
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.error || `Failed to set protection to ${state}`);
    }
    return await res.json();
  }
}
