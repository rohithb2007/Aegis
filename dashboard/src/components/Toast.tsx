import React from 'react';
import { CheckCircle2, AlertCircle, XCircle, X } from 'lucide-react';

export interface ToastMessage {
  id: string;
  type: 'success' | 'warning' | 'error';
  title: string;
  message: string;
}

interface ToastProps {
  toasts: ToastMessage[];
  onClose: (id: string) => void;
}

export const ToastContainer: React.FC<ToastProps> = ({ toasts, onClose }) => {
  if (toasts.length === 0) return null;

  return (
    <div style={{
      position: 'fixed',
      bottom: '24px',
      right: '24px',
      zIndex: 2000,
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
      maxWidth: '380px',
    }}>
      {toasts.map((toast) => {
        const isSuccess = toast.type === 'success';
        const isWarning = toast.type === 'warning';
        const Icon = isSuccess ? CheckCircle2 : isWarning ? AlertCircle : XCircle;
        const color = isSuccess ? 'var(--accent-allow)' : isWarning ? 'var(--accent-review)' : 'var(--accent-block)';

        return (
          <div
            key={toast.id}
            style={{
              backgroundColor: 'var(--bg-surface)',
              border: `1px solid ${color}`,
              borderRadius: '10px',
              padding: '14px 16px',
              boxShadow: '0 10px 25px rgba(0, 0, 0, 0.5)',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
              animation: 'fadeIn 0.2s ease',
            }}
          >
            <Icon size={18} color={color} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#ffffff', marginBottom: '2px' }}>
                {toast.title}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                {toast.message}
              </div>
            </div>
            <button
              onClick={() => onClose(toast.id)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                padding: '2px',
              }}
            >
              <X size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
};
