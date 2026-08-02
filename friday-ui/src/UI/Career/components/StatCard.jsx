export default function StatCard({ value, label, icon: Icon, color = '#6366f1', trend = null, suffix = '' }) {
  return (
    <div style={{
      padding: '16px 20px', borderRadius: 10,
      background: 'rgba(255,255,255,0.02)',
      border: '1px solid rgba(255,255,255,0.06)',
      display: 'flex', flexDirection: 'column', gap: 8, flex: 1, minWidth: 0,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 11, color: '#64748b', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {label}
        </span>
        {Icon && <Icon size={14} style={{ color: '#475569' }} />}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
        <span style={{ fontSize: 26, fontWeight: 700, color: '#f1f5f9', letterSpacing: '-0.02em', lineHeight: 1 }}>
          {value}{suffix}
        </span>
        {trend !== null && (
          <span style={{ fontSize: 12, color: trend >= 0 ? '#22c55e' : '#ef4444', fontWeight: 600 }}>
            {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}
          </span>
        )}
      </div>
    </div>
  );
}
