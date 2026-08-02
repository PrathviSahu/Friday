const STATUS_CONFIG = {
  // Application statuses
  saved:     { label: 'Saved',      color: '#6366f1', bg: 'rgba(99,102,241,0.12)' },
  ready:     { label: 'Ready',      color: '#3b82f6', bg: 'rgba(59,130,246,0.12)' },
  submitted: { label: 'Submitted',  color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
  viewed:    { label: 'Viewed',     color: '#8b5cf6', bg: 'rgba(139,92,246,0.12)' },
  interview: { label: 'Interview',  color: '#06b6d4', bg: 'rgba(6,182,212,0.12)'  },
  offer:     { label: 'Offer',      color: '#22c55e', bg: 'rgba(34,197,94,0.12)'  },
  rejected:  { label: 'Rejected',   color: '#ef4444', bg: 'rgba(239,68,68,0.12)'  },
  // Job statuses
  new:        { label: 'New',       color: '#22c55e', bg: 'rgba(34,197,94,0.12)'  },
  bookmarked: { label: 'Bookmarked',color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
  approved:   { label: 'Approved',  color: '#6366f1', bg: 'rgba(99,102,241,0.12)' },
  applied:    { label: 'Applied',   color: '#3b82f6', bg: 'rgba(59,130,246,0.12)' },
  ignored:    { label: 'Ignored',   color: '#475569', bg: 'rgba(71,85,105,0.12)'  },
  // Interview outcomes
  pending:  { label: 'Pending',     color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
  passed:   { label: 'Passed',      color: '#22c55e', bg: 'rgba(34,197,94,0.12)'  },
  failed:   { label: 'Failed',      color: '#ef4444', bg: 'rgba(239,68,68,0.12)'  },
};

export default function StatusBadge({ status, size = 'sm' }) {
  const cfg = STATUS_CONFIG[status] || { label: status, color: '#94a3b8', bg: 'rgba(148,163,184,0.12)' };
  const fontSize = size === 'xs' ? 10 : 11;
  const px = size === 'xs' ? '5px 8px' : '4px 10px';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      background: cfg.bg, color: cfg.color,
      border: `1px solid ${cfg.color}30`,
      borderRadius: 999, fontSize, fontWeight: 600,
      padding: px, letterSpacing: '0.03em', whiteSpace: 'nowrap',
    }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: cfg.color, flexShrink: 0 }} />
      {cfg.label}
    </span>
  );
}
