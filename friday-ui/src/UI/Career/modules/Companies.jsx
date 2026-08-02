import { useState, useEffect } from 'react';
import { Shield, ShieldOff } from 'lucide-react';
import { getCompanies, blacklistCompany } from '../../../api/careerApi.js';
import DataTable from '../components/DataTable.jsx';
import Skeleton from '../components/Skeleton.jsx';

export default function Companies() {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [filter, setFilter]       = useState('all');

  const load = () => {
    getCompanies().then(d => setCompanies(d.companies || [])).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const filtered = filter === 'blacklisted' ? companies.filter(c => c.is_blacklisted) : companies;

  const handleBlacklist = async (company) => {
    const reason = prompt(`Reason for blocking "${company.name}"?`) || 'User preference';
    if (reason !== null) { await blacklistCompany(company.name, reason); load(); }
  };

  if (loading) return <div style={{ padding: 32 }}><Skeleton count={6} /></div>;

  const COLUMNS = [
    { key: 'name', label: 'Company', sortable: true },
    { key: 'industry', label: 'Industry' },
    { key: 'size', label: 'Size' },
    { key: 'is_blacklisted', label: 'Status', render: (v) => (
      <span style={{ fontSize: 12, color: v ? '#ef4444' : '#22c55e' }}>{v ? '● Blocked' : '● Active'}</span>
    )},
    { key: 'blacklist_reason', label: 'Reason', render: (v) => v || '—' },
    { key: 'id', label: 'Actions', sortable: false, render: (_, row) => (
      !row.is_blacklisted && (
        <button onClick={() => handleBlacklist(row)} style={{ padding: '4px 10px', borderRadius: 6, background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', color: '#ef4444', fontSize: 11, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          <ShieldOff size={11} /> Block
        </button>
      )
    )},
  ];

  return (
    <div style={{ padding: 28, maxWidth: 960 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h2 style={{ margin: '0 0 4px', fontSize: 20, fontWeight: 700, color: '#f1f5f9' }}>Companies</h2>
          <p style={{ margin: 0, fontSize: 13, color: '#475569' }}>{companies.length} companies tracked · {companies.filter(c => c.is_blacklisted).length} blocked</p>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {['all', 'blacklisted'].map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{
              padding: '6px 14px', borderRadius: 7, border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 600, textTransform: 'capitalize',
              background: filter === f ? 'rgba(99,102,241,0.15)' : 'rgba(255,255,255,0.04)',
              color: filter === f ? '#818cf8' : '#64748b',
            }}>{f}</button>
          ))}
        </div>
      </div>
      {filtered.length === 0 ? (
        <div style={{ padding: '48px 0', textAlign: 'center', color: '#475569', fontSize: 14 }}>
          <Shield size={36} style={{ marginBottom: 12, strokeWidth: 1, display: 'block', margin: '0 auto 12px' }} />
          {filter === 'blacklisted' ? 'No companies blocked yet.' : 'Companies will appear here as you add jobs.'}
        </div>
      ) : (
        <div style={{ padding: '20px 24px', borderRadius: 10, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
          <DataTable columns={COLUMNS} rows={filtered} />
        </div>
      )}
    </div>
  );
}
