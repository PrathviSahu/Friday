const EVENT_ICONS = {
  job_found: '🔍', application_created: '📋', status_changed: '🔄',
  interview_scheduled: '📅', company_blacklisted: '🚫', preference_learned: '🧠',
  resume_created: '📄', job_analyzed: '⚡', job_status_changed: '📊',
};
function timeAgo(ts) {
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}
export default function ActivityFeed({ items = [] }) {
  if (!items.length) return (
    <div style={{ color: '#475569', fontSize: 13, textAlign: 'center', padding: '24px 0' }}>
      No recent activity
    </div>
  );
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {items.map((item, i) => (
        <div key={item.id || i} style={{
          display: 'flex', alignItems: 'flex-start', gap: 10, padding: '10px 0',
          borderBottom: i < items.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
        }}>
          <span style={{ fontSize: 14, flexShrink: 0, marginTop: 1 }}>
            {EVENT_ICONS[item.event_type] || '•'}
          </span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, color: '#cbd5e1', fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {item.title}
            </div>
            {item.description && (
              <div style={{ fontSize: 11, color: '#475569', marginTop: 2 }}>{item.description}</div>
            )}
          </div>
          <span style={{ fontSize: 11, color: '#334155', flexShrink: 0 }}>
            {timeAgo(item.created_at)}
          </span>
        </div>
      ))}
    </div>
  );
}
