import React from 'react';
import { Bot, Terminal, Activity, Cpu, ArrowRight } from 'lucide-react';
import type { AgentTaskInfo, AuditRecord } from '../types/aegis';

interface AgentPanelProps {
  tasks: AgentTaskInfo[];
  recentAudits: AuditRecord[];
}

export const AgentPanel: React.FC<AgentPanelProps> = ({ tasks, recentAudits }) => {
  const agentInfo = {
    name: 'Antigravity',
    type: 'Autonomous AI Agent',
    supervisor: 'Aegis Security Engine V1.1.0',
    executionBoundary: 'Experimentally verified Antigravity PowerShell execution path',
    status: 'RUNNING',
  };

  const agentEvents = recentAudits.slice(0, 5);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Monitored Agent Card */}
      <div className="glass-card" style={{ padding: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{
              width: '52px',
              height: '52px',
              borderRadius: '14px',
              background: 'linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-primary-hover) 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)',
            }}>
              <Bot size={30} color="#ffffff" />
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <h3 style={{ fontSize: '22px', fontWeight: 800, color: 'var(--text-primary)' }}>
                  {agentInfo.name}
                </h3>
                <span className="badge badge-allow">
                  <div className="pulse-dot pulse-dot-green" />
                  MONITORED
                </span>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px', fontWeight: 500 }}>
                {agentInfo.type} • {agentInfo.executionBoundary}
              </p>
            </div>
          </div>

          <div style={{
            padding: '10px 16px',
            borderRadius: '10px',
            backgroundColor: 'var(--bg-surface-elevated)',
            border: '1px solid var(--border-subtle)',
            textAlign: 'right',
          }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>Supervision Engine</div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--accent-primary)' }}>Aegis Policy Core</div>
          </div>
        </div>

        {/* Execution Boundary Diagram */}
        <div style={{
          backgroundColor: 'var(--input-bg)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '12px',
          padding: '20px',
          marginBottom: '24px',
        }}>
          <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '14px', letterSpacing: '0.04em' }}>
            SUPERVISION EXECUTION PATH
          </div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '8px',
            flexWrap: 'wrap',
            fontFamily: 'var(--font-mono)',
            fontSize: '13px',
          }}>
            <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-subtle)', fontWeight: 700, color: 'var(--text-primary)' }}>
              Antigravity
            </div>
            <ArrowRight size={16} color="var(--text-muted)" />
            <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-subtle)', fontWeight: 600, color: 'var(--text-secondary)' }}>
              PowerShell
            </div>
            <ArrowRight size={16} color="var(--text-muted)" />
            <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-subtle)', fontWeight: 600, color: 'var(--accent-primary)' }}>
              Aegis Interceptor
            </div>
            <ArrowRight size={16} color="var(--text-muted)" />
            <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-subtle)', fontWeight: 600, color: 'var(--accent-primary)' }}>
              Aegis Gateway
            </div>
            <ArrowRight size={16} color="var(--text-muted)" />
            <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-subtle)', fontWeight: 600, color: 'var(--accent-system)' }}>
              Security Engine
            </div>
            <ArrowRight size={16} color="var(--text-muted)" />
            <div style={{ backgroundColor: 'var(--accent-allow-bg)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--accent-allow-border)', fontWeight: 800, color: 'var(--accent-allow)' }}>
              VERDICT
            </div>
          </div>
        </div>

        {/* Active Command Context */}
        <div style={{
          backgroundColor: 'var(--bg-surface-elevated)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '10px',
          padding: '18px',
          marginBottom: '20px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '10px' }}>
            <Terminal size={16} color="var(--accent-primary)" />
            <span>ACTIVE COMMAND TASK CONTEXT</span>
          </div>

          {tasks.length > 0 ? (
            tasks.map((task) => (
              <div key={task.task_id} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)', fontWeight: 600 }}>
                    Task ID: {task.task_id}
                  </span>
                  <span className={`badge ${task.status === 'RUNNING' ? 'badge-allow' : 'badge-review'}`}>
                    {task.status}
                  </span>
                </div>
                <code style={{ fontSize: '14px', color: 'var(--text-secondary)', display: 'block', wordBreak: 'break-all' }}>
                  {task.last_command}
                </code>
              </div>
            ))
          ) : (
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Aegis is actively intercepting and evaluating proposed Antigravity execution boundary calls.
            </div>
          )}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', fontSize: '13px' }}>
          <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: '14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '4px', fontWeight: 600 }}>INTERCEPTION BOUNDARY</div>
            <div style={{ color: 'var(--text-primary)', fontWeight: 700 }}>PowerShell Pre-Exec</div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: '14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '4px', fontWeight: 600 }}>APPROVAL POLICY</div>
            <div style={{ color: 'var(--accent-review)', fontWeight: 700 }}>Human-In-The-Loop</div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-surface-elevated)', padding: '14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '4px', fontWeight: 600 }}>CRITICAL BOUNDARY</div>
            <div style={{ color: 'var(--accent-block)', fontWeight: 700 }}>Non-Overridable</div>
          </div>
        </div>
      </div>

      {/* Action History Card */}
      <div className="glass-card" style={{ padding: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          <Activity size={20} color="var(--accent-primary)" />
          <h4 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)' }}>
            Agent Action History
          </h4>
        </div>

        {agentEvents.length === 0 ? (
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>No agent execution steps recorded yet.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {agentEvents.map((ev) => (
              <div key={ev.record_id} style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 18px',
                backgroundColor: 'var(--input-bg)',
                borderRadius: '10px',
                border: '1px solid var(--border-subtle)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <Cpu size={18} color="var(--text-muted)" />
                  <code style={{ fontSize: '13px', color: 'var(--text-primary)', fontWeight: 600 }}>{ev.command}</code>
                </div>

                <span className={`badge ${
                  ev.final_policy_decision === 'ALLOW' || ev.final_policy_decision === 'PASSTHROUGH'
                    ? 'badge-allow'
                    : ev.final_policy_decision === 'REVIEW' || ev.final_policy_decision === 'PAUSED_FOR_APPROVAL'
                    ? 'badge-review'
                    : 'badge-block'
                }`}>
                  {ev.final_policy_decision}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

