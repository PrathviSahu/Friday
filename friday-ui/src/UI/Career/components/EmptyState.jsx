export default function EmptyState({ icon: Icon, title, body, action, onAction }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', gap: 12, padding: '64px 32px', textAlign: 'center',
    }}>
      {Icon && <Icon size={36} style={{ color: '#334155', strokeWidth: 1.5 }} />}
      <div style={{ fontSize: 15, fontWeight: 600, color: '#64748b' }}>{title}</div>
      {body && <div style={{ fontSize: 13, color: '#475569', maxWidth: 320, lineHeight: 1.6 }}>{body}</div>}
      {action && (
        <button onClick={onAction} style={{
          marginTop: 8, padding: '8px 20px', borderRadius: 8,
          background: '#6366f1', border: 'none', color: '#fff',
          fontSize: 13, fontWeight: 600, cursor: 'pointer',
        }}>{action}</button>
      )}
    </div>
  );
}
