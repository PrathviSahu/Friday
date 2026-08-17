import { useState, Suspense, lazy, memo } from 'react';
import {
  Briefcase, FileText, ListChecks,
  Building2, Users, CalendarCheck, BarChart3,
  GraduationCap, SlidersHorizontal, Shield, KeyRound, X, ChevronLeft, Mic, MicOff, RotateCw
} from 'lucide-react';
import { useFriday } from '../../context/FridayContext';
import Skeleton from './components/Skeleton.jsx';

// Lazy-loaded modules — each module is its own chunk
const Opportunities   = lazy(() => import('./modules/Opportunities.jsx'));
const ResumeManager   = lazy(() => import('./modules/ResumeManager.jsx'));
const Applications    = lazy(() => import('./modules/Applications.jsx'));
const Companies       = lazy(() => import('./modules/Companies.jsx'));
const Recruiters      = lazy(() => import('./modules/Recruiters.jsx'));
const InterviewCenter = lazy(() => import('./modules/InterviewCenter.jsx'));
const Analytics       = lazy(() => import('./modules/Analytics.jsx'));
const LearningCenter  = lazy(() => import('./modules/LearningCenter.jsx'));
const Preferences     = lazy(() => import('./modules/Preferences.jsx'));
const PersonalVault   = lazy(() => import('./modules/PersonalVault.jsx'));
const AccountManager  = lazy(() => import('./modules/AccountManager.jsx'));

const NAV = [
  { id: 'opportunities',label: 'Opportunities',   Icon: Briefcase        },
  { id: 'resumes',      label: 'Resume Manager',  Icon: FileText         },
  { id: 'applications', label: 'Applications',    Icon: ListChecks       },
  { id: 'companies',    label: 'Companies',       Icon: Building2        },
  { id: 'recruiters',   label: 'Recruiters',      Icon: Users            },
  { id: 'interviews',   label: 'Interviews',      Icon: CalendarCheck    },
  { id: 'analytics',    label: 'Analytics',       Icon: BarChart3        },
  { id: 'learning',     label: 'Learning Center', Icon: GraduationCap    },
  { id: 'preferences',  label: 'Preferences',     Icon: SlidersHorizontal },
  { id: 'vault',        label: 'Personal Vault',  Icon: Shield           },
  { id: 'accounts',     label: 'Account Manager', Icon: KeyRound         },
];

const MODULE_MAP = {
  opportunities: Opportunities,
  resumes:      ResumeManager,
  applications: Applications,
  companies:    Companies,
  recruiters:   Recruiters,
  interviews:   InterviewCenter,
  analytics:    Analytics,
  learning:     LearningCenter,
  preferences:  Preferences,
  vault:        PersonalVault,
  accounts:     AccountManager,
};

const CareerOS = memo(function CareerOS({ onClose }) {
  const [active, setActive]       = useState('opportunities');
  const [collapsed, setCollapsed] = useState(() => {
    return typeof window !== 'undefined' ? window.innerWidth < 768 : false;
  });
  const [refreshKey, setRefreshKey] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  const { micEnabled, setMicEnabled } = useFriday();
  const isMuted = !micEnabled;

  const handleRefresh = () => {
    setRefreshing(true);
    setRefreshKey(k => k + 1);
    setTimeout(() => setRefreshing(false), 600);
  };

  const ActiveModule = MODULE_MAP[active] || Opportunities;
  const activeNav    = NAV.find(n => n.id === active);

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 100,
      background: '#080B14',
      display: 'flex', flexDirection: 'column',
      fontFamily: "'Inter', 'Space Grotesk', system-ui, sans-serif",
    }}>
      {/* ── Top Header ─────────────────────────────────────────────────────── */}
      <div style={{
        height: 52, borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', alignItems: 'center', padding: '0 14px', gap: 10,
        flexShrink: 0,
      }}>
        {/* Sidebar toggle */}
        <button onClick={() => setCollapsed(c => !c)} style={iconBtn} className="hidden md:flex">
          <ChevronLeft size={16} style={{ transform: collapsed ? 'rotate(180deg)' : 'none', transition: '200ms' }} />
        </button>

        {/* Breadcrumb */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1, overflow: 'hidden' }}>
          <span style={{ fontSize: 11, color: '#64748b', fontWeight: 600, whiteSpace: 'nowrap' }}>
            Career OS
          </span>
          <span style={{ color: '#1e293b' }}>/</span>
          <span style={{ fontSize: 11, color: '#94a3b8', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {activeNav?.label}
          </span>
        </div>

        {/* Refresh Button */}
        <button
          onClick={handleRefresh}
          title="Refresh Data"
          className="hidden sm:flex"
          style={{
            alignItems: 'center', gap: 5,
            padding: '4px 10px', borderRadius: 999,
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            color: '#94a3b8',
            fontSize: 10, fontWeight: 600, cursor: 'pointer', transition: 'all 200ms',
          }}
        >
          <RotateCw size={12} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
          <span>REFRESH</span>
        </button>

        {/* Voice Mute / Mic Off Button */}
        <button
          onClick={() => setMicEnabled(prev => !prev)}
          title={isMuted ? "FRIDAY Voice Muted" : "FRIDAY Active"}
          style={{
            display: 'flex', alignItems: 'center', gap: 5,
            padding: '4px 10px', borderRadius: 999,
            background: isMuted ? 'rgba(239, 68, 68, 0.15)' : 'rgba(99, 102, 241, 0.15)',
            border: isMuted ? '1px solid rgba(239, 68, 68, 0.35)' : '1px solid rgba(99, 102, 241, 0.35)',
            color: isMuted ? '#f87171' : '#818cf8',
            fontSize: 10, fontWeight: 600, cursor: 'pointer', transition: 'all 200ms',
          }}
        >
          {isMuted ? <MicOff size={12} /> : <Mic size={12} />}
          <span className="hidden sm:inline">{isMuted ? 'MIC OFF' : 'MIC ON'}</span>
        </button>

        {/* Close */}
        <button onClick={onClose} style={{ ...iconBtn, color: '#ef4444', background: 'rgba(239, 68, 68, 0.1)' }} title="Return to Main HUD">
          <X size={16} />
        </button>
      </div>

      {/* ── Mobile Horizontal Navigation Strip ──────────────────────────────── */}
      <div className="flex md:hidden items-center gap-1.5 px-3 py-2 border-b border-white/5 bg-[#050812] overflow-x-auto scrollbar-none shrink-0">
        {NAV.map(({ id, label, Icon }) => {
          const isActive = active === id;
          return (
            <button
              key={id}
              onClick={() => setActive(id)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-medium whitespace-nowrap transition ${
                isActive
                  ? 'bg-[#6366f1]/25 text-[#818cf8] border border-[#6366f1]/50 font-semibold'
                  : 'bg-white/[0.03] text-slate-400 border border-white/[0.06] hover:text-white'
              }`}
            >
              <Icon size={11} />
              <span>{label}</span>
            </button>
          );
        })}
      </div>

      {/* ── Body ─────────────────────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* ── Desktop Sidebar ──────────────────────────────────────────────── */}
        <div className="hidden md:flex" style={{
          width: collapsed ? 56 : 220, flexShrink: 0, overflow: 'hidden',
          borderRight: '1px solid rgba(255,255,255,0.05)',
          padding: '12px 8px', flexDirection: 'column', gap: 2,
          transition: 'width 220ms ease',
        }}>
          {NAV.map(({ id, label, Icon }) => {
            const isActive = active === id;
            return (
              <button key={id} onClick={() => setActive(id)} title={collapsed ? label : ''} style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: collapsed ? '9px 0' : '9px 12px',
                justifyContent: collapsed ? 'center' : 'flex-start',
                borderRadius: 8, border: 'none', cursor: 'pointer', width: '100%',
                background: isActive ? 'rgba(99,102,241,0.12)' : 'transparent',
                color: isActive ? '#818cf8' : '#475569',
                transition: 'all 150ms ease',
              }}
                onMouseEnter={e => { if (!isActive) e.currentTarget.style.color = '#94a3b8'; }}
                onMouseLeave={e => { if (!isActive) e.currentTarget.style.color = '#475569'; }}
              >
                <Icon size={15} style={{ flexShrink: 0 }} />
                {!collapsed && (
                  <span style={{ fontSize: 13, fontWeight: isActive ? 600 : 500, whiteSpace: 'nowrap', overflow: 'hidden' }}>
                    {label}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* ── Main Content ─────────────────────────────────────────────────── */}
        <div style={{ flex: 1, overflow: 'auto', minWidth: 0 }}>
          <Suspense fallback={
            <div style={{ padding: 32 }}>
              <Skeleton count={6} />
            </div>
          }>
            <ActiveModule
              key={`${active}_${refreshKey}`}
              onNavigate={setActive}
            />
          </Suspense>
        </div>
      </div>
    </div>
  );
});

export default CareerOS;

const iconBtn = {
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  width: 30, height: 30, borderRadius: 7, border: 'none', cursor: 'pointer',
  background: 'rgba(255,255,255,0.04)', color: '#64748b',
  transition: 'all 150ms ease',
};
