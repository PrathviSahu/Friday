import { useState, useEffect } from 'react';
import { Briefcase, Send, CalendarCheck, Star, Clock } from 'lucide-react';
import { getDashboard } from '../../../api/careerApi.js';
import StatCard from '../components/StatCard.jsx';
import ActivityFeed from '../components/ActivityFeed.jsx';
import FridayAdvisor from '../components/FridayAdvisor.jsx';
import { SkeletonCard } from '../components/Skeleton.jsx';

export default function Dashboard({ onNavigate }) {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboard()
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  const handleRecommendationAction = (action) => {
    const actionMap = {
      open_opportunities: 'opportunities',
      open_resume_manager: 'resumes',
      open_interviews: 'interviews',
      review_job: 'opportunities',
    };
    if (actionMap[action]) onNavigate(actionMap[action]);
  };

  return (
    <div style={{ padding: 32, maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#f1f5f9', letterSpacing: '-0.02em', margin: 0 }}>
          Career Intelligence
        </h1>
        <p style={{ fontSize: 13, color: '#475569', marginTop: 4 }}>
          {new Date().toLocaleDateString('en-GB', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </p>
      </div>

      {/* Daily Briefing */}
      {loading ? (
        <div style={{ marginBottom: 28 }}><SkeletonCard lines={2} /></div>
      ) : data?.briefing && (
        <div style={{
          padding: '16px 20px', marginBottom: 28, borderRadius: 10,
          background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.15)',
          borderLeft: '3px solid #6366f1',
        }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#6366f1', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 8 }}>
            F.R.I.D.A.Y. BRIEFING
          </div>
          <p style={{ fontSize: 14, color: '#cbd5e1', lineHeight: 1.7, margin: 0, fontStyle: 'italic' }}>
            {data.briefing}
          </p>
        </div>
      )}

      {/* Stats Row */}
      {loading ? (
        <div style={{ display: 'flex', gap: 12, marginBottom: 28 }}>
          {[1,2,3,4,5].map(i => <SkeletonCard key={i} lines={2} />)}
        </div>
      ) : (
        <div style={{ display: 'flex', gap: 12, marginBottom: 28, flexWrap: 'wrap' }}>
          <StatCard value={data?.stats?.new_jobs ?? 0}       label="New Jobs"          icon={Briefcase} />
          <StatCard value={data?.stats?.high_priority ?? 0}  label="High Priority"     icon={Star} />
          <StatCard value={data?.stats?.pending_approval ?? 0} label="Pending Approval" icon={Clock} />
          <StatCard value={data?.stats?.submitted ?? 0}      label="Submitted"         icon={Send} />
          <StatCard value={data?.stats?.interviews ?? 0}     label="Interviews"        icon={CalendarCheck} />
        </div>
      )}

      {/* Two-column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20, alignItems: 'start' }}>
        {/* Left column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

          {/* Friday's Recommendations */}
          <Section title="F.R.I.D.A.Y. Recommendations">
            {loading ? <SkeletonCard lines={3} /> : (
              <FridayAdvisor
                recommendations={data?.recommendations || []}
                onAction={handleRecommendationAction}
              />
            )}
          </Section>

          {/* Upcoming Deadlines */}
          {(data?.stats?.upcoming_deadlines?.length > 0) && (
            <Section title="Upcoming Deadlines">
              {data.stats.upcoming_deadlines.map((d, i) => (
                <div key={i} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '10px 0', borderBottom: i < data.stats.upcoming_deadlines.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                }}>
                  <div>
                    <div style={{ fontSize: 13, color: '#cbd5e1', fontWeight: 500 }}>{d.title}</div>
                    <div style={{ fontSize: 12, color: '#64748b' }}>{d.company}</div>
                  </div>
                  <span style={{ fontSize: 12, color: '#ef4444', fontWeight: 600 }}>{d.deadline}</span>
                </div>
              ))}
            </Section>
          )}
        </div>

        {/* Right column — Activity Feed */}
        <Section title="Recent Activity">
          {loading ? <SkeletonCard lines={5} /> : (
            <ActivityFeed items={data?.recent_activity || []} />
          )}
        </Section>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{
      padding: 20, borderRadius: 10,
      background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)',
    }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: '#475569', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 16 }}>
        {title}
      </div>
      {children}
    </div>
  );
}
