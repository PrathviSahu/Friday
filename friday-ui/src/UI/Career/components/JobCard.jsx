import StatusBadge from './StatusBadge.jsx';
import MatchScoreRing from './MatchScoreRing.jsx';

export default function JobCard({ job, isSelected, onClick }) {
  const score = Math.round(job.match_score || 0);
  return (
    <div onClick={onClick} style={{
      display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px',
      borderRadius: 8, cursor: 'pointer',
      background: isSelected ? 'rgba(99,102,241,0.08)' : 'transparent',
      border: isSelected ? '1px solid rgba(99,102,241,0.25)' : '1px solid transparent',
      transition: 'all 150ms ease',
    }}
      onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'rgba(255,255,255,0.02)'; }}
      onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
    >
      <MatchScoreRing score={score} size={44} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {job.title}
        </div>
        <div style={{ fontSize: 12, color: '#64748b', marginTop: 2, display: 'flex', gap: 8, alignItems: 'center' }}>
          <span>{job.company}</span>
          {job.location && <><span>·</span><span>{job.location}</span></>}
        </div>
      </div>
      <StatusBadge status={job.status} size="xs" />
    </div>
  );
}
