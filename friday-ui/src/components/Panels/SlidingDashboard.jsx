import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, LayoutGrid, Sliders, Eye, ChevronRight } from 'lucide-react';
import TodoCard from './TodoCard';
import SystemMonitorCard from './SystemMonitorCard';
import WeatherCard from './WeatherCard';
import WebSearchCard from './WebSearchCard';
import PermissionCenterCard from './PermissionCenterCard';
import NotificationCenterCard from './NotificationCenterCard';
import LearningCoachCard from './LearningCoachCard';
import DevToolsCard from './DevToolsCard';
import KnowledgeCard from './KnowledgeCard';
import EmailCard from './EmailCard';
import CalendarCard from './CalendarCard';
import MeetingsCard from './MeetingsCard';
import WhatsAppCard from './WhatsAppCard';
import DocumentsCard from './DocumentsCard';
import CodingCard from './CodingCard';
import AutonomyCard from './AutonomyCard';
import MacrosCard from './MacrosCard';

export const CAPSULES_CATALOG = [
  { id: 'todo',         label: 'Task Manager',         icon: '✅', category: 'Productivity',  component: TodoCard },
  { id: 'system',       label: 'System Telemetry',     icon: '⚡', category: 'System',        component: SystemMonitorCard },
  { id: 'weather',      label: 'Weather & Climate',    icon: '🌤️', category: 'Utilities',     component: WeatherCard },
  { id: 'search',       label: 'Web Intelligence',     icon: '🔍', category: 'Search',        component: WebSearchCard },
  { id: 'email',        label: 'Smart Inbox',          icon: '✉️', category: 'Communication', component: EmailCard },
  { id: 'calendar',     label: 'Calendar & Agenda',    icon: '📅', category: 'Productivity',  component: CalendarCard },
  { id: 'meetings',     label: 'Meeting Transcripts',  icon: '🎙️', category: 'Communication', component: MeetingsCard },
  { id: 'whatsapp',     label: 'WhatsApp Desktop',     icon: '💬', category: 'Communication', component: WhatsAppCard },
  { id: 'documents',    label: 'Document AI',          icon: '📄', category: 'AI Tools',      component: DocumentsCard },
  { id: 'knowledge',    label: 'Second Brain',         icon: '🧠', category: 'Memory',        component: KnowledgeCard },
  { id: 'learning',     label: 'Learning Coach',       icon: '🎓', category: 'AI Tools',      component: LearningCoachCard },
  { id: 'devtools',     label: 'Developer Mode',       icon: '🛠️', category: 'System',        component: DevToolsCard },
  { id: 'coding',       label: 'Coding Assistant',     icon: '💻', category: 'AI Tools',      component: CodingCard },
  { id: 'permissions',  label: 'Permission Center',    icon: '🛡️', category: 'Security',      component: PermissionCenterCard },
  { id: 'notifications',label: 'Notification Center',  icon: '🔔', category: 'System',        component: NotificationCenterCard },
  { id: 'autonomy',     label: 'Autonomy & Trust',     icon: '🤖', category: 'System',        component: AutonomyCard },
  { id: 'macros',       label: 'Voice Macros',         icon: '🔗', category: 'Productivity',  component: MacrosCard },
];

export default function SlidingDashboard({ isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('picker'); // 'picker' | 'active'
  const [selectedCapsule, setSelectedCapsule] = useState(null);
  const [activeCapsules, setActiveCapsules] = useState(() => {
    try {
      const saved = localStorage.getItem('friday_active_capsules');
      return saved ? JSON.parse(saved) : {};
    } catch (_) {
      return {};
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('friday_active_capsules', JSON.stringify(activeCapsules));
    } catch (_) {}
  }, [activeCapsules]);

  const toggleCapsule = (id) => {
    setActiveCapsules((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const activeCount = Object.values(activeCapsules).filter(Boolean).length;

  const ActiveComponent = selectedCapsule
    ? CAPSULES_CATALOG.find((c) => c.id === selectedCapsule)?.component
    : null;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(2, 3, 10, 0.75)',
              backdropFilter: 'blur(12px)',
              zIndex: 9000,
            }}
          />

          {/* Sliding Drawer Panel */}
          <motion.aside
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            style={{
              position: 'fixed',
              top: 0,
              right: 0,
              bottom: 0,
              width: selectedCapsule ? '680px' : '520px',
              maxWidth: '92vw',
              background: 'rgba(5, 12, 28, 0.96)',
              borderLeft: '1px solid rgba(0, 183, 255, 0.35)',
              boxShadow: '-20px 0 60px rgba(0, 183, 255, 0.15)',
              zIndex: 9001,
              display: 'flex',
              flexDirection: 'column',
              fontFamily: "'Space Grotesk', sans-serif",
            }}
          >
            {/* Drawer Header */}
            <div
              style={{
                padding: '20px 24px',
                borderBottom: '1px solid rgba(0, 183, 255, 0.2)',
                background: 'rgba(0, 183, 255, 0.04)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div
                  style={{
                    width: 38,
                    height: 38,
                    borderRadius: 10,
                    background: 'rgba(0, 183, 255, 0.12)',
                    border: '1px solid rgba(0, 183, 255, 0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 18,
                  }}
                >
                  ⚡
                </div>
                <div>
                  <h2
                    className="font-orbitron"
                    style={{
                      margin: 0,
                      fontSize: 15,
                      letterSpacing: '0.25em',
                      color: '#DFFAFF',
                      textTransform: 'uppercase',
                      textShadow: '0 0 12px rgba(0,183,255,0.5)',
                    }}
                  >
                    SLIDING DASHBOARD
                  </h2>
                  <p style={{ margin: '2px 0 0', fontSize: 11, color: '#00B7FF', opacity: 0.8, letterSpacing: '0.05em' }}>
                    {activeCount} Active Capsule{activeCount !== 1 ? 's' : ''} · Select any module to launch
                  </p>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {selectedCapsule && (
                  <button
                    onClick={() => setSelectedCapsule(null)}
                    style={{
                      background: 'rgba(0, 183, 255, 0.1)',
                      border: '1px solid rgba(0, 183, 255, 0.3)',
                      color: '#00D9FF',
                      borderRadius: 8,
                      padding: '6px 12px',
                      fontSize: 11,
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    ← All Capsules
                  </button>
                )}
                <button
                  onClick={onClose}
                  style={{
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    color: '#DFFAFF',
                    borderRadius: 8,
                    width: 34,
                    height: 34,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                  }}
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Navigation Bar */}
            <div
              style={{
                padding: '10px 24px',
                borderBottom: '1px solid rgba(255,255,255,0.05)',
                display: 'flex',
                gap: 12,
                background: 'rgba(0,0,0,0.2)',
              }}
            >
              <button
                onClick={() => {
                  setActiveTab('picker');
                  setSelectedCapsule(null);
                }}
                style={{
                  flex: 1,
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: activeTab === 'picker' ? '1px solid rgba(0,183,255,0.4)' : '1px solid transparent',
                  background: activeTab === 'picker' ? 'rgba(0,183,255,0.12)' : 'transparent',
                  color: activeTab === 'picker' ? '#00D9FF' : 'rgba(223,250,255,0.6)',
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                }}
              >
                <LayoutGrid size={14} /> Capsule Catalog
              </button>
              <button
                onClick={() => {
                  setActiveTab('active');
                }}
                style={{
                  flex: 1,
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: activeTab === 'active' ? '1px solid rgba(0,183,255,0.4)' : '1px solid transparent',
                  background: activeTab === 'active' ? 'rgba(0,183,255,0.12)' : 'transparent',
                  color: activeTab === 'active' ? '#00D9FF' : 'rgba(223,250,255,0.6)',
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                }}
              >
                <Eye size={14} /> Active Capsules ({activeCount})
              </button>
            </div>

            {/* Content Body */}
            <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
              {selectedCapsule && ActiveComponent ? (
                <div style={{ animation: 'fadeIn 0.2s ease-out' }}>
                  <ActiveComponent />
                </div>
              ) : activeTab === 'picker' ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
                  {CAPSULES_CATALOG.map((c) => {
                    const isActive = !!activeCapsules[c.id];
                    return (
                      <div
                        key={c.id}
                        onClick={() => setSelectedCapsule(c.id)}
                        style={{
                          padding: '14px 16px',
                          borderRadius: 12,
                          background: isActive ? 'rgba(0, 183, 255, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                          border: isActive ? '1px solid rgba(0, 183, 255, 0.4)' : '1px solid rgba(255, 255, 255, 0.06)',
                          cursor: 'pointer',
                          transition: 'all 0.2s ease',
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between',
                          gap: 12,
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span style={{ fontSize: 24 }}>{c.icon}</span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleCapsule(c.id);
                            }}
                            style={{
                              padding: '3px 8px',
                              borderRadius: 999,
                              fontSize: 10,
                              fontWeight: 700,
                              border: 'none',
                              cursor: 'pointer',
                              background: isActive ? '#00B7FF' : 'rgba(255,255,255,0.1)',
                              color: isActive ? '#02030A' : '#DFFAFF',
                            }}
                          >
                            {isActive ? 'ENABLED' : 'OFF'}
                          </button>
                        </div>
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 700, color: '#DFFAFF', marginBottom: 2 }}>
                            {c.label}
                          </div>
                          <div style={{ fontSize: 10, color: '#00B7FF', opacity: 0.75, display: 'flex', alignItems: 'center', gap: 4 }}>
                            {c.category} <ChevronRight size={10} />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {activeCount === 0 ? (
                    <div style={{ padding: 40, textAlign: 'center', color: 'rgba(223,250,255,0.4)', fontSize: 13 }}>
                      No capsules currently enabled. Switch to <b>Capsule Catalog</b> to activate modules.
                    </div>
                  ) : (
                    CAPSULES_CATALOG.filter((c) => activeCapsules[c.id]).map((c) => {
                      const Comp = c.component;
                      return (
                        <div
                          key={c.id}
                          style={{
                            borderRadius: 12,
                            border: '1px solid rgba(0, 183, 255, 0.25)',
                            background: 'rgba(2, 8, 22, 0.6)',
                            overflow: 'hidden',
                          }}
                        >
                          <div
                            style={{
                              padding: '10px 16px',
                              background: 'rgba(0, 183, 255, 0.08)',
                              borderBottom: '1px solid rgba(0, 183, 255, 0.15)',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                            }}
                          >
                            <span style={{ fontSize: 12, fontWeight: 700, color: '#00D9FF' }}>
                              {c.icon} {c.label}
                            </span>
                            <button
                              onClick={() => toggleCapsule(c.id)}
                              style={{
                                background: 'none',
                                border: 'none',
                                color: '#ff4d6d',
                                fontSize: 11,
                                cursor: 'pointer',
                                fontWeight: 600,
                              }}
                            >
                              Remove
                            </button>
                          </div>
                          <div style={{ padding: 12 }}>
                            <Comp />
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
