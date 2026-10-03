import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert, Power, AlertTriangle, CheckCircle2, Lock, Radio } from 'lucide-react';
import type { ProtectionStatusDict, GatewayStatus } from '../types/aegis';

interface ProtectionPanelProps {
  protection: ProtectionStatusDict | null;
  gatewayStatus: GatewayStatus | null;
  onToggleProtection: (targetState: 'ON' | 'OFF') => void;
  isProcessing?: boolean;
}

export const ProtectionPanel: React.FC<ProtectionPanelProps> = ({
  protection,
  gatewayStatus,
  onToggleProtection,
  isProcessing,
}) => {
  const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);

  const isProtectionOn = protection?.status === 'ON';
  const isGatewayOnline = gatewayStatus?.status === 'RUNNING';

  const handleToggleClick = (target: 'ON' | 'OFF') => {
    if (target === 'OFF') {
      setShowConfirmModal(true);
    } else {
      onToggleProtection('ON');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Protection State Control Card */}
      <div className="glass-card" style={{ padding: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{
              width: '56px',
              height: '56px',
              borderRadius: '16px',
              backgroundColor: isProtectionOn ? 'var(--accent-allow-bg)' : 'var(--accent-block-bg)',
              border: `1px solid ${isProtectionOn ? 'var(--accent-allow-border)' : 'var(--accent-block-border)'}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              {isProtectionOn ? (
                <ShieldCheck size={32} color="var(--accent-allow)" />
              ) : (
                <ShieldAlert size={32} color="var(--accent-block)" />
              )}
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <h2 style={{ fontSize: '22px', fontWeight: 800, color: 'var(--text-primary)' }}>
                  AEGIS PROTECTION CONTROL
                </h2>
                <span className={`badge ${isProtectionOn ? 'badge-allow' : 'badge-block'}`}>
                  {isProtectionOn ? '● ACTIVE / PROTECTED' : '● DISABLED BY HUMAN'}
                </span>
              </div>
              <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: 1.5 }}>
                {isProtectionOn
                  ? 'Your AI agent (Antigravity) is operating under active Aegis security supervision.'
                  : 'Aegis protection is intentionally disabled by human choice. Agent commands will pass through without Gateway enforcement.'}
              </p>
            </div>
          </div>

          {isProtectionOn ? (
            <button
              className="btn btn-deny"
              disabled={isProcessing}
              onClick={() => handleToggleClick('OFF')}
              style={{ padding: '12px 20px', fontSize: '14px' }}
            >
              <Power size={18} />
              <span>TURN PROTECTION OFF</span>
            </button>
          ) : (
            <button
              className="btn btn-approve"
              disabled={isProcessing}
              onClick={() => handleToggleClick('ON')}
              style={{ padding: '12px 20px', fontSize: '14px' }}
            >
              <Power size={18} />
              <span>TURN PROTECTION ON</span>
            </button>
          )}
        </div>

        {/* State vs Connectivity Distinction Section */}
        <div style={{
          backgroundColor: 'var(--input-bg)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '12px',
          padding: '18px 20px',
          marginBottom: '20px',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '20px',
        }}>
          <div>
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px', letterSpacing: '0.04em' }}>
              PROTECTION STATE (POLICY)
            </div>
            <div style={{ fontSize: '16px', fontWeight: 800, color: isProtectionOn ? 'var(--accent-allow)' : 'var(--accent-block)' }}>
              {isProtectionOn ? 'PROTECTION ON (SUPERVISED)' : 'PROTECTION OFF (PASSTHROUGH)'}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Explicit human-controlled toggle setting stored in protection_state.json.
            </div>
          </div>

          <div>
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px', letterSpacing: '0.04em' }}>
              GATEWAY CONNECTIVITY (SERVICE)
            </div>
            <div style={{ fontSize: '16px', fontWeight: 800, color: isGatewayOnline ? 'var(--accent-allow)' : 'var(--accent-block)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Radio size={16} />
              <span>{isGatewayOnline ? 'GATEWAY ONLINE (127.0.0.1:8765)' : 'GATEWAY DISCONNECTED (FAIL-CLOSED)'}</span>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              {isGatewayOnline
                ? 'Gateway active & responding to evaluation requests.'
                : 'Gateway offline + Protection ON enforces Fail-Closed security (Exit Code 3).'}
            </div>
          </div>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '16px',
          paddingTop: '20px',
          borderTop: '1px solid var(--border-subtle)',
        }}>
          <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>INTERCEPTOR STATUS</div>
            <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>Active (PowerShell Profile)</div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>Idempotent Boundary</div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>GATEWAY DAEMON</div>
            <div style={{ fontSize: '15px', fontWeight: 700, color: isGatewayOnline ? 'var(--accent-allow)' : 'var(--accent-block)', marginTop: '4px' }}>
              {isGatewayOnline ? '127.0.0.1:8765' : 'Offline'}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>Localhost HTTP Gateway</div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>FAIL-CLOSED INVARIANT</div>
            <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--accent-allow)', marginTop: '4px' }}>Active (Exit 3)</div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>Gateway offline = Blocks command</div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>LAST STATE CHANGE</div>
            <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
              {protection?.updated_by || 'HUMAN_CLI'}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              {protection?.updated_at ? new Date(protection.updated_at).toLocaleTimeString() : 'N/A'}
            </div>
          </div>
        </div>
      </div>

      {/* Security Invariants List */}
      <div className="glass-card" style={{ padding: '28px' }}>
        <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Lock size={20} color="var(--accent-primary)" />
          <span>Security Boundary Invariants (V0.9.4 & V1.1.0)</span>
        </h3>

        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '14px', color: 'var(--text-secondary)' }}>
          <li style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <CheckCircle2 size={18} color="var(--accent-allow)" style={{ marginTop: '2px', flexShrink: 0 }} />
            <span><strong>Invariant A (Fail Closed):</strong> When Protection is ON and the Aegis Gateway service is unreachable, all proposed commands fail closed (exit code 3).</span>
          </li>
          <li style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <CheckCircle2 size={18} color="var(--accent-allow)" style={{ marginTop: '2px', flexShrink: 0 }} />
            <span><strong>Invariant B (Human Control Only):</strong> Protection OFF is an intentional human-controlled choice. Antigravity AI agent is strictly prohibited from altering Aegis protection state.</span>
          </li>
          <li style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <CheckCircle2 size={18} color="var(--accent-allow)" style={{ marginTop: '2px', flexShrink: 0 }} />
            <span><strong>Invariant D (Critical Boundary):</strong> Actions targeting critical system directories (e.g., <code>rm -rf /</code>) are blocked by policy and cannot be overridden by human approval.</span>
          </li>
          <li style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <CheckCircle2 size={18} color="var(--accent-allow)" style={{ marginTop: '2px', flexShrink: 0 }} />
            <span><strong>Invariant F (Exact Identity Binding):</strong> Approval for a command is strictly bound to the exact string and context. Modifying the command string requires a new human approval request.</span>
          </li>
          <li style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <CheckCircle2 size={18} color="var(--accent-allow)" style={{ marginTop: '2px', flexShrink: 0 }} />
            <span><strong>Invariant M (Strict CORS Local Origins):</strong> Gateway restricts CORS access strictly to local dashboard origins (`http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:4173`, `http://127.0.0.1:4173`). Wildcards are prohibited.</span>
          </li>
        </ul>
      </div>

      {showConfirmModal && (
        <div className="modal-overlay" onClick={() => setShowConfirmModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '18px' }}>
              <div style={{
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                backgroundColor: 'var(--accent-block-bg)',
                border: '1px solid var(--accent-block-border)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <AlertTriangle size={24} color="var(--accent-block)" />
              </div>
              <div>
                <h3 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)' }}>
                  Turn Off Aegis Protection?
                </h3>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                  Human Authorization Confirmation Required
                </p>
              </div>
            </div>

            <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: 1.6 }}>
              While disabled, proposed agent commands will bypass Aegis security policy enforcement.
              This action is strictly logged and reserved for human operators.
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button className="btn btn-secondary" onClick={() => setShowConfirmModal(false)} style={{ padding: '10px 18px', fontSize: '14px' }}>
                CANCEL
              </button>

              <button
                className="btn btn-deny"
                onClick={() => {
                  setShowConfirmModal(false);
                  onToggleProtection('OFF');
                }}
                style={{ padding: '10px 18px', fontSize: '14px' }}
              >
                TURN OFF PROTECTION
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

