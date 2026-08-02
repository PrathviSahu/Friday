import { useState, useEffect } from 'react';
import { getAnalytics } from '../../../api/careerApi.js';
import { SkeletonCard } from '../components/Skeleton.jsx';

// ── Pure SVG Charts ────────────────────────────────────────────────────────────
function BarChart({ data = [], color = '#6366f1', height = 120, label = '' }) {
  if (!data.length) return <EmptyChart />;
  const max = Math.max(...data.map(d => d.count || d.value || 0), 1);
  return (
    <div>
      {label && <div style={{ fontSize: 12, color: '#64748b', marginBottom: 12 }}>{label}</div>}
      <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end', height }}>
        {data.map((d, i) => {
          const val = d.count || d.value || 0;
          const pct = (val / max) * 100;
          return (
            <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 11, color: '#94a3b8', fontWeight: 600 }}>{val}</span>
              <div style={{
                width: '100%', height: `${Math.max(4, pct)}%`, minHeight: 4,
                background: `${color}cc`, borderRadius: '4px 4px 0 0',
                transition: 'height 0.5s ease',
              }} />
              <span style={{ fontSize: 10, color: '#475569', textAlign: 'center', lineHeight: 1.2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '100%' }}>
                {(d.month || d.label || d.company || d.title || '').replace(/^\d{4}-/, '').slice(-5)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DonutChart({ segments = [], size = 120, label = '' }) {
  if (!segments.length) return <EmptyChart />;
  const total = segments.reduce((s, d) => s + (d.value || 0), 0);
  if (total === 0) return <EmptyChart />;
  const cx = size / 2, cy = size / 2, r = size * 0.35, strokeWidth = size * 0.18;
  const circ = 2 * Math.PI * r;
  let cumPct = 0;
  const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4', '#8b5cf6'];

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
      <svg width={size} height={size}>
        {segments.map((seg, i) => {
          const pct = (seg.value / total);
          const offset = circ - pct * circ;
          const rotation = cumPct * 360 - 90;
          cumPct += pct;
          return (
            <circle key={i} cx={cx} cy={cy} r={r}
              fill="none" stroke={COLORS[i % COLORS.length]} strokeWidth={strokeWidth}
              strokeDasharray={circ} strokeDashoffset={offset}
              style={{ transform: `rotate(${rotation}deg)`, transformOrigin: `${cx}px ${cy}px`, transition: '0.5s ease' }} />
          );
        })}
        <text x={cx} y={cy + 4} textAnchor="middle" fill="#94a3b8" fontSize={12} fontWeight="700">{total}</text>
      </svg>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {segments.map((seg, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: ['#6366f1','#22c55e','#f59e0b','#ef4444','#06b6d4','#8b5cf6'][i % 6], flexShrink: 0 }} />
            <span style={{ color: '#94a3b8', textTransform: 'capitalize' }}>{seg.label}</span>
            <span style={{ color: '#64748b', marginLeft: 4 }}>{seg.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function EmptyChart() {
  return <div style={{ height: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: 13 }}>No data yet</div>;
}

function ChartCard({ title, children }) {
  return (
    <div style={{ padding: '20px 24px', borderRadius: 10, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 20 }}>{title}</div>
      {children}
    </div>
  );
}

export default function Analytics() {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAnalytics().then(d => setData(d.analytics)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: 32 }}><SkeletonCard lines={4} /></div>;

  const funnel = data?.status_funnel || {};
  const funnelSegments = Object.entries(funnel).map(([label, value]) => ({ label, value })).filter(s => s.value > 0);

  const resumePerf = (data?.resume_performance || []).map(r => ({ label: r.title, value: r.applications || 0, count: r.applications || 0 }));

  const monthly = [...(data?.monthly_applications || [])].reverse();

  return (
    <div style={{ padding: 32, maxWidth: 1100 }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, color: '#f1f5f9', margin: '0 0 8px', letterSpacing: '-0.02em' }}>Analytics</h2>
      <p style={{ fontSize: 13, color: '#475569', margin: '0 0 28px' }}>
        Avg match score: <strong style={{ color: '#6366f1' }}>{data?.avg_match_score || 0}%</strong>
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        <ChartCard title="Applications Per Month">
          <BarChart data={monthly} color="#6366f1" height={140} />
        </ChartCard>

        <ChartCard title="Application Pipeline">
          <DonutChart segments={funnelSegments} size={110} />
        </ChartCard>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <ChartCard title="Resume Performance">
          <BarChart data={resumePerf} color="#22c55e" height={120} />
        </ChartCard>

        <ChartCard title="Top Companies Applied">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {(data?.top_companies || []).length === 0 ? <EmptyChart /> : (data?.top_companies || []).map((c, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 11, color: '#475569', width: 18, textAlign: 'right' }}>{i + 1}</span>
                <span style={{ flex: 1, fontSize: 13, color: '#cbd5e1' }}>{c.company}</span>
                <div style={{ width: 80, height: 4, borderRadius: 99, background: 'rgba(255,255,255,0.06)' }}>
                  <div style={{ width: `${Math.min(100, (c.apps / Math.max(...(data?.top_companies || []).map(x => x.apps), 1)) * 100)}%`, height: '100%', borderRadius: 99, background: '#6366f1' }} />
                </div>
                <span style={{ fontSize: 12, color: '#64748b', width: 20, textAlign: 'right' }}>{c.apps}</span>
              </div>
            ))}
          </div>
        </ChartCard>
      </div>
    </div>
  );
}
