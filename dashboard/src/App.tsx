import { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { GatewayDisconnected } from './components/GatewayDisconnected';
import { ApprovalDrawer } from './components/ApprovalDrawer';
import { ToastContainer } from './components/Toast';
import type { ToastMessage } from './components/Toast';

import { OverviewPage } from './pages/OverviewPage';
import { ApprovalsPage } from './pages/ApprovalsPage';
import { AgentsPage } from './pages/AgentsPage';
import { AuditPage } from './pages/AuditPage';
import { ProtectionPage } from './pages/ProtectionPage';
import { SettingsPage } from './pages/SettingsPage';

import { AegisApi } from './api/aegis';
import type {
  GatewayStatus,
  ApprovalRequest,
  AuditRecord,
  AgentTaskInfo,
  ProtectionStatusDict,
} from './types/aegis';

export function App() {
  const [activeTab, setActiveTab] = useState<string>('overview');

  // Theme state
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const saved = localStorage.getItem('aegis_theme');
    if (saved === 'dark' || saved === 'light') return saved;
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light';
    }
    return 'dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('aegis_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  // Backend state
  const [gatewayStatus, setGatewayStatus] = useState<GatewayStatus | null>(null);
  const [protection, setProtection] = useState<ProtectionStatusDict | null>(null);
  const [requests, setRequests] = useState<ApprovalRequest[]>([]);
  const [audits, setAudits] = useState<AuditRecord[]>([]);
  const [tasks, setTasks] = useState<AgentTaskInfo[]>([]);

  // UI state
  const [isDisconnected, setIsDisconnected] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isProcessingAction, setIsProcessingAction] = useState<boolean>(false);
  const [selectedRequest, setSelectedRequest] = useState<ApprovalRequest | null>(null);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = (type: 'success' | 'warning' | 'error', title: string, message: string) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
    setToasts((prev) => [...prev, { id, type, title, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Main data fetch
  const fetchAllData = useCallback(async (showIndicator = false) => {
    if (showIndicator) setIsRefreshing(true);
    try {
      const [gwStat, reqs, recentAudits, tks, protDict] = await Promise.all([
        AegisApi.getStatus(),
        AegisApi.getRequests(),
        AegisApi.getRecentAudit(50),
        AegisApi.getTasks(),
        AegisApi.getProtection(),
      ]);

      setGatewayStatus(gwStat);
      setRequests(reqs);
      setAudits(recentAudits);
      setTasks(tks);
      setProtection(protDict);
      setIsDisconnected(false);
    } catch (err) {
      console.warn('[Aegis Dashboard] Gateway fetch failed:', err);
      setIsDisconnected(true);
    } finally {
      if (showIndicator) setIsRefreshing(false);
    }
  }, []);

  // Polling loop (every 2 seconds)
  useEffect(() => {
    fetchAllData();
    const interval = setInterval(() => {
      fetchAllData();
    }, 2000);
    return () => clearInterval(interval);
  }, [fetchAllData]);

  // Action handlers
  const handleApprove = async (requestId: string) => {
    setIsProcessingAction(true);
    try {
      await AegisApi.approveRequest(requestId);
      addToast('success', 'Request Approved', `Request '${requestId}' set to APPROVED via Aegis Gateway.`);
      await fetchAllData();
    } catch (err: any) {
      addToast('error', 'Approval Error', err.message || 'Failed to approve request');
    } finally {
      setIsProcessingAction(false);
    }
  };

  const handleDeny = async (requestId: string) => {
    setIsProcessingAction(true);
    try {
      await AegisApi.denyRequest(requestId);
      addToast('warning', 'Request Denied', `Request '${requestId}' set to DENIED via Aegis Gateway.`);
      await fetchAllData();
    } catch (err: any) {
      addToast('error', 'Denial Error', err.message || 'Failed to deny request');
    } finally {
      setIsProcessingAction(false);
    }
  };

  const handleToggleProtection = async (targetState: 'ON' | 'OFF') => {
    setIsProcessingAction(true);
    try {
      await AegisApi.setProtection(targetState);
      addToast(
        targetState === 'ON' ? 'success' : 'warning',
        `Protection ${targetState}`,
        `Aegis Protection state updated to ${targetState} via Human Control.`
      );
      await fetchAllData();
    } catch (err: any) {
      addToast('error', 'Protection Error', err.message || 'Failed to update protection state');
    } finally {
      setIsProcessingAction(false);
    }
  };

  const pendingCount = requests.filter((r) => r.status === 'PENDING').length;

  const getPageTitle = () => {
    switch (activeTab) {
      case 'overview':
        return { title: 'Security Overview', subtitle: 'Mission control for autonomous AI agent supervision' };
      case 'activity':
        return { title: 'Security Activity Stream', subtitle: 'Real-time evaluation stream and observability timeline' };
      case 'approvals':
        return { title: 'Human Approval Center', subtitle: 'Actions waiting for human authorization' };
      case 'agents':
        return { title: 'Agent Supervision', subtitle: 'Antigravity execution trajectory & task monitoring' };
      case 'audit':
        return { title: 'Security Audit Explorer', subtitle: 'Secret-redacted chronological evaluation audit log' };
      case 'protection':
        return { title: 'Protection & Invariants', subtitle: 'Human-controlled protection state and fail-closed policies' };
      case 'settings':
        return { title: 'Settings & Config', subtitle: 'Localhost security boundaries and configuration parameters' };
      default:
        return { title: 'Aegis Security Operations Center', subtitle: 'V1.1 Premium Command Center' };
    }
  };

  const currentHeader = getPageTitle();

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'var(--bg-dark)' }}>
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        gatewayStatus={gatewayStatus}
        pendingCount={pendingCount}
      />

      {/* Main Content Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <TopBar
          title={currentHeader.title}
          subtitle={currentHeader.subtitle}
          gatewayStatus={gatewayStatus}
          theme={theme}
          onToggleTheme={toggleTheme}
          onRefresh={() => fetchAllData(true)}
          isRefreshing={isRefreshing}
        />

        <main style={{
          marginLeft: '260px',
          padding: '32px',
          flex: 1,
          maxWidth: '1400px',
        }}>
          {isDisconnected ? (
            <GatewayDisconnected onRetry={() => fetchAllData(true)} isRetrying={isRefreshing} />
          ) : (
            <>
              {activeTab === 'overview' && (
                <OverviewPage
                  gatewayStatus={gatewayStatus}
                  protection={protection}
                  requests={requests}
                  audits={audits}
                  tasks={tasks}
                  onApprove={handleApprove}
                  onDeny={handleDeny}
                  onViewDetails={setSelectedRequest}
                  isProcessing={isProcessingAction}
                />
              )}

              {activeTab === 'activity' && (
                <OverviewPage
                  gatewayStatus={gatewayStatus}
                  protection={protection}
                  requests={requests}
                  audits={audits}
                  tasks={tasks}
                  onApprove={handleApprove}
                  onDeny={handleDeny}
                  onViewDetails={setSelectedRequest}
                  isProcessing={isProcessingAction}
                />
              )}

              {activeTab === 'approvals' && (
                <ApprovalsPage
                  requests={requests}
                  onApprove={handleApprove}
                  onDeny={handleDeny}
                  onViewDetails={setSelectedRequest}
                  isProcessing={isProcessingAction}
                />
              )}

              {activeTab === 'agents' && (
                <AgentsPage tasks={tasks} audits={audits} />
              )}

              {activeTab === 'audit' && (
                <AuditPage audits={audits} />
              )}

              {activeTab === 'protection' && (
                <ProtectionPage
                  protection={protection}
                  gatewayStatus={gatewayStatus}
                  onToggleProtection={handleToggleProtection}
                  isProcessing={isProcessingAction}
                />
              )}

              {activeTab === 'settings' && (
                <SettingsPage
                  gatewayStatus={gatewayStatus}
                  theme={theme}
                  onSetTheme={setTheme}
                />
              )}
            </>
          )}
        </main>
      </div>

      {/* Approval Details Drawer/Modal */}
      <ApprovalDrawer
        request={selectedRequest}
        onClose={() => setSelectedRequest(null)}
        onApprove={handleApprove}
        onDeny={handleDeny}
        isProcessing={isProcessingAction}
      />

      {/* Notification Toast Container */}
      <ToastContainer toasts={toasts} onClose={removeToast} />
    </div>
  );
}

export default App;

