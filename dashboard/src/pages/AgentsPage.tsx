import React from 'react';
import type { AgentTaskInfo, AuditRecord } from '../types/aegis';
import { AgentPanel } from '../components/AgentPanel';
import { Bot } from 'lucide-react';

interface AgentsPageProps {
  tasks: AgentTaskInfo[];
  audits: AuditRecord[];
}

export const AgentsPage: React.FC<AgentsPageProps> = ({ tasks, audits }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
          <Bot size={24} color="#38bdf8" />
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#ffffff' }}>
            Autonomous Agent Supervision
          </h2>
        </div>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          Real-time monitoring and boundary enforcement for Antigravity AI agent execution paths.
        </p>
      </div>

      <AgentPanel tasks={tasks} recentAudits={audits} />
    </div>
  );
};
