const TYPES = {
  matched: { color: '#22c55e', bg: 'rgba(34,197,94,0.1)',  border: 'rgba(34,197,94,0.2)'  },
  missing: { color: '#ef4444', bg: 'rgba(239,68,68,0.1)',  border: 'rgba(239,68,68,0.2)'  },
  neutral: { color: '#94a3b8', bg: 'rgba(148,163,184,0.08)', border: 'rgba(148,163,184,0.15)' },
};
export default function SkillTag({ label, type = 'neutral' }) {
  const s = TYPES[type] || TYPES.neutral;
  return (
    <span style={{
      display: 'inline-block', padding: '3px 9px', borderRadius: 999,
      fontSize: 11, fontWeight: 500, color: s.color,
      background: s.bg, border: `1px solid ${s.border}`,
    }}>{label}</span>
  );
}
