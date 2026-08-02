const PRIORITY_COLORS = {
  high: { border: 'rgba(239,68,68,0.3)', bg: 'rgba(239,68,68,0.06)', dot: '#ef4444' },
  medium: { border: 'rgba(99,102,241,0.3)', bg: 'rgba(99,102,241,0.06)', dot: '#6366f1' },
  low: { border: 'rgba(71,85,105,0.3)', bg: 'rgba(71,85,105,0.06)', dot: '#475569' },
};
export default function FridayAdvisor({ recommendations = [], onAction }) {
  if (!recommendations.length) return null;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {recommendations.slice(0, 4).map((rec, i) => {
        const colors = PRIORITY_COLORS[rec.priority] || PRIORITY_COLORS.medium;
        return (
          <div key={i} style={{
            padding: '12px 16px', borderRadius: 10,
            border: `1px solid ${colors.border}`, background: colors.bg,
            display: 'flex', alignItems: 'flex-start', gap: 10,
          }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: colors.dot, marginTop: 5, flexShrink: 0 }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0', marginBottom: 3 }}>{rec.title}</div>
              <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>{rec.body}</div>
              {rec.action && rec.action !== 'none' && (
                <button onClick={() => onAction?.(rec.action)} style={{
                  marginTop: 8, fontSize: 11, fontWeight: 600, color: '#6366f1',
                  background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                }}>
                  Take action →
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
