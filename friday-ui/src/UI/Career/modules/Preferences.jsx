import { useState, useEffect } from 'react';
import { getPreferences, updatePreferences, learnFromText } from '../../../api/careerApi.js';
import { SkeletonCard } from '../components/Skeleton.jsx';
import { Brain, Send } from 'lucide-react';


export default function Preferences() {
  const [prefs, setPrefs]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving]   = useState(null);
  const [learnText, setLearnText] = useState('');
  const [learnResult, setLearnResult] = useState(null);
  const [learning, setLearning]   = useState(false);

  const load = () => {
    getPreferences().then(d => setPrefs(d.preferences)).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const save = async (key, value) => {
    setSaving(key);
    await updatePreferences({ [key]: value });
    setSaving(null);
    load();
  };

  const handleLearn = async () => {
    if (!learnText.trim()) return;
    setLearning(true);
    const result = await learnFromText(learnText);
    setLearnResult(result);
    setLearnText('');
    setLearning(false);
    load();
  };

  if (loading) return <div style={{ padding: 32 }}><SkeletonCard lines={5} /></div>;

  return (
    <div style={{ padding: 32, maxWidth: 740 }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, color: '#f1f5f9', margin: '0 0 6px', letterSpacing: '-0.02em' }}>
        Career Preferences
      </h2>
      <p style={{ fontSize: 13, color: '#475569', margin: '0 0 32px' }}>
        F.R.I.D.A.Y. uses these to filter, rank, and analyze every opportunity.
      </p>

      {/* Tell Friday */}
      <div style={{ padding: '20px', borderRadius: 10, background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.15)', marginBottom: 32 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
          <Brain size={14} style={{ color: '#6366f1' }} />
          <span style={{ fontSize: 12, fontWeight: 600, color: '#6366f1', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Tell F.R.I.D.A.Y.</span>
        </div>
        <p style={{ fontSize: 13, color: '#94a3b8', margin: '0 0 12px', lineHeight: 1.6 }}>
          Say anything natural — she'll learn and update your preferences automatically.
        </p>
        <div style={{ display: 'flex', gap: 10 }}>
          <input value={learnText} onChange={e => setLearnText(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleLearn()}
            placeholder={`e.g. "Don't show me Infosys", "Minimum 8 LPA", "I prefer remote"`}
            style={{ flex: 1, padding: '9px 12px', borderRadius: 8, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', color: '#e2e8f0', fontSize: 13, fontFamily: 'inherit', outline: 'none' }} />
          <button onClick={handleLearn} disabled={learning || !learnText.trim()} style={{ padding: '9px 16px', borderRadius: 8, background: '#6366f1', border: 'none', color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Send size={13} /> {learning ? 'Learning…' : 'Tell'}
          </button>
        </div>
        {learnResult && (
          <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 8, background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)', fontSize: 13, color: '#86efac' }}>
            ✓ {learnResult.explanation}
          </div>
        )}
      </div>

      {/* Numeric prefs */}
      <Section title="Compensation">
        <Field label="Minimum Salary (LPA / Annual)">
          <NumberInput value={prefs?.min_salary || 0} onSave={v => save('min_salary', v)} saving={saving === 'min_salary'} />
        </Field>
        <Field label="Notice Period (days)">
          <NumberInput value={prefs?.notice_period_days || 0} onSave={v => save('notice_period_days', v)} saving={saving === 'notice_period_days'} />
        </Field>
      </Section>

      <Section title="Work Style">
        <Field label="Preferred Work Type">
          <RadioGroup value={prefs?.preferred_remote || 'any'} options={['any', 'remote', 'hybrid', 'onsite']} onSave={v => save('preferred_remote', v)} />
        </Field>
        <Field label="Experience Level">
          <RadioGroup value={prefs?.experience_level || 'any'} options={['any', 'junior', 'mid', 'senior']} onSave={v => save('experience_level', v)} />
        </Field>
        <Field label="Visa Required">
          <RadioGroup value={prefs?.visa_required ? 'yes' : 'no'} options={['no', 'yes']} onSave={v => save('visa_required', v === 'yes')} />
        </Field>
      </Section>

      {/* Tag-based prefs */}
      {[
        ['Preferred Tech Stack', 'preferred_tech_stack'],
        ['Avoided Tech Stack', 'avoided_tech_stack'],
        ['Preferred Roles', 'preferred_roles'],
        ['Avoided Roles', 'avoided_roles'],
        ['Preferred Countries', 'preferred_countries'],
        ['Preferred Cities', 'preferred_cities'],
        ['Preferred Industries', 'preferred_industries'],
        ['Company Blacklist', 'blacklisted_companies'],
        ['Favorite Companies', 'favorite_companies'],
        ['Job Types', 'job_types'],
      ].reduce((groups, item, i) => {
        const groupIdx = Math.floor(i / 4);
        (groups[groupIdx] = groups[groupIdx] || []).push(item);
        return groups;
      }, []).map((group, gi) => (
        <Section key={gi} title={gi === 0 ? 'Technology' : gi === 1 ? 'Location & Roles' : 'Companies'}>
          {group.map(([label, key]) => (
            <Field key={key} label={label}>
              <TagInput values={prefs?.[key] || []} onSave={v => save(key, v)} saving={saving === key} />
            </Field>
          ))}
        </Section>
      ))}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 28 }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>{title}</div>
      <div style={{ padding: '4px 0', borderRadius: 10, border: '1px solid rgba(255,255,255,0.06)', overflow: 'hidden' }}>
        {children}
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, padding: '14px 20px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
      <span style={{ fontSize: 13, color: '#94a3b8', fontWeight: 500, paddingTop: 4, minWidth: 180 }}>{label}</span>
      <div style={{ flex: 1 }}>{children}</div>
    </div>
  );
}

function NumberInput({ value, onSave, saving }) {
  const [v, setV] = useState(value);
  return (
    <div style={{ display: 'flex', gap: 8 }}>
      <input type="number" value={v} onChange={e => setV(+e.target.value)}
        style={{ width: 120, padding: '7px 10px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#e2e8f0', fontSize: 13, outline: 'none' }} />
      <button onClick={() => onSave(v)} disabled={saving} style={{ padding: '7px 14px', borderRadius: 7, background: '#6366f1', border: 'none', color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
        {saving ? '…' : 'Save'}
      </button>
    </div>
  );
}

function RadioGroup({ value, options, onSave }) {
  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
      {options.map(opt => (
        <button key={opt} onClick={() => onSave(opt)} style={{
          padding: '5px 12px', borderRadius: 6, border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 500, textTransform: 'capitalize',
          background: value === opt ? 'rgba(99,102,241,0.15)' : 'rgba(255,255,255,0.04)',
          color: value === opt ? '#818cf8' : '#64748b',
        }}>{opt}</button>
      ))}
    </div>
  );
}

function TagInput({ values = [], onSave }) {
  const [input, setInput] = useState('');
  const remove = (v) => onSave(values.filter(x => x !== v));
  const add = () => {
    const val = input.trim();
    if (!val || values.includes(val)) return;
    onSave([...values, val]);
    setInput('');
  };
  return (
    <div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: values.length ? 8 : 0 }}>
        {values.map(v => (
          <span key={v} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 10px', borderRadius: 999, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)', fontSize: 12, color: '#818cf8' }}>
            {v}
            <button onClick={() => remove(v)} style={{ background: 'none', border: 'none', color: '#475569', cursor: 'pointer', padding: 0, fontSize: 12, lineHeight: 1 }}>×</button>
          </span>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && add()}
          placeholder="Add and press Enter" style={{ flex: 1, padding: '7px 10px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#e2e8f0', fontSize: 12, outline: 'none', fontFamily: 'inherit' }} />
        <button onClick={add} style={{ padding: '7px 12px', borderRadius: 7, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)', color: '#94a3b8', fontSize: 12, cursor: 'pointer' }}>Add</button>
      </div>
    </div>
  );
}
