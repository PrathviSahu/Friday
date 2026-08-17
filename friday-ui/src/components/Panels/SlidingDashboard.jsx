import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, LayoutGrid, Eye, Search, Sparkles, Pin, ExternalLink, ArrowLeft, Shield, Terminal, Zap, CheckCircle2 } from 'lucide-react';
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
  { id: 'todo',         label: 'Task Manager',         icon: '✅', category: 'Productivity',  tagline: 'Synced SQLite Task Matrix', description: 'Real-time task tracker, priority matrix, and intelligent checklists.', component: TodoCard },
  { id: 'system',       label: 'System Telemetry',     icon: '⚡', category: 'System',        tagline: 'Hardware Load & Sensors', description: 'Live CPU load, memory utilization, disk storage, and thermal metrics.', component: SystemMonitorCard },
  { id: 'weather',      label: 'Weather & Climate',    icon: '🌤️', category: 'Utilities',     tagline: 'Live Atmospheric Radar', description: 'Precision hyperlocal forecast, barometric data, and humidity monitoring.', component: WeatherCard },
  { id: 'search',       label: 'Web Intelligence',     icon: '🔍', category: 'Search',        tagline: 'Autonomous Query Engine', description: 'Multi-source real-time web scraping and research summarizer.', component: WebSearchCard },
  { id: 'email',        label: 'Smart Inbox',          icon: '✉️', category: 'Communication', tagline: 'AI Mail Triaging & Drafts', description: 'Autonomous inbox analysis, draft composition, and security-cleared sending.', component: EmailCard },
  { id: 'calendar',     label: 'Calendar & Agenda',    icon: '📅', category: 'Productivity',  tagline: 'Daily Briefings & Schedule', description: 'Intelligent schedule optimization, reminders, and calendar sync.', component: CalendarCard },
  { id: 'meetings',     label: 'Meeting Transcripts',  icon: '🎙️', category: 'Communication', tagline: 'Speech-to-Text & Summaries', description: 'Live audio transcription, smart meeting notes, and action item detection.', component: MeetingsCard },
  { id: 'whatsapp',     label: 'WhatsApp Desktop',     icon: '💬', category: 'Communication', tagline: 'Secure Messaging Relay', description: 'Direct contact intelligence, chat history search, and message automation.', component: WhatsAppCard },
  { id: 'documents',    label: 'Document AI',          icon: '📄', category: 'AI Tools',      tagline: 'Semantic OCR & Analysis', description: 'Multimodal document parsing, PDF analysis, and automated briefing creation.', component: DocumentsCard },
  { id: 'knowledge',    label: 'Second Brain',         icon: '🧠', category: 'Memory',        tagline: 'Vector Knowledge Graph', description: 'Persistent long-term memories, user preferences, and semantic recall.', component: KnowledgeCard },
  { id: 'learning',     label: 'Learning Coach',       icon: '🎓', category: 'AI Tools',      tagline: 'Interactive Knowledge Tutor', description: 'Personalized curriculum builder, active-recall drills, and quizzes.', component: LearningCoachCard },
  { id: 'devtools',     label: 'Developer Mode',       icon: '🛠️', category: 'System',        tagline: 'Diagnostics & API Inspector', description: 'Live route health checks, network logs, and backend telemetry debugger.', component: DevToolsCard },
  { id: 'coding',       label: 'Coding Assistant',     icon: '💻', category: 'AI Tools',      tagline: 'Multi-Language Synthesis', description: 'Code generator, regex builder, syntax linter, and logic refactorer.', component: CodingCard },
  { id: 'permissions',  label: 'Permission Center',    icon: '🛡️', category: 'Security',      tagline: 'Zero-Trust Access Control', description: 'Granular policy management, biometric gates, and capability audits.', component: PermissionCenterCard },
  { id: 'notifications',label: 'Notification Center',  icon: '🔔', category: 'System',        tagline: 'Event & Priority Hub', description: 'Aggregated real-time system alerts, proactive nudges, and urgent pings.', component: NotificationCenterCard },
  { id: 'autonomy',     label: 'Autonomy & Trust',     icon: '🤖', category: 'System',        tagline: 'Self-Governing Agent Mode', description: 'Configurable autonomy levels, risk guardrails, and automated approvals.', component: AutonomyCard },
  { id: 'macros',       label: 'Voice Macros',         icon: '🔗', category: 'Productivity',  tagline: 'Workflow Chaining Engine', description: 'Custom multi-action voice trigger sequences and macro automations.', component: MacrosCard },
];

const CATEGORIES = ['All', 'AI Tools', 'System', 'Productivity', 'Communication', 'Security', 'Utilities'];

export default function SlidingDashboard({ isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('picker'); // 'picker' | 'active'
  const [selectedCapsule, setSelectedCapsule] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
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

  const toggleCapsule = (id, e) => {
    if (e) e.stopPropagation();
    setActiveCapsules((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const activeCount = Object.values(activeCapsules).filter(Boolean).length;

  const currentCapsuleObj = useMemo(() => {
    return CAPSULES_CATALOG.find((c) => c.id === selectedCapsule);
  }, [selectedCapsule]);

  const filteredCapsules = useMemo(() => {
    return CAPSULES_CATALOG.filter((c) => {
      const matchCat = selectedCategory === 'All' || c.category.toLowerCase() === selectedCategory.toLowerCase() || (selectedCategory === 'Utilities' && c.category === 'Search');
      const matchQuery = !searchQuery.trim() || 
        c.label.toLowerCase().includes(searchQuery.toLowerCase()) || 
        c.tagline.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.category.toLowerCase().includes(searchQuery.toLowerCase());
      return matchCat && matchQuery;
    });
  }, [selectedCategory, searchQuery]);

  const ActiveComponent = currentCapsuleObj ? currentCapsuleObj.component : null;

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
            className="fixed inset-0 bg-[#02030A]/80 backdrop-blur-md z-[9000]"
          />

          {/* Sliding Drawer Panel */}
          <motion.aside
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 320, damping: 32 }}
            className={`fixed top-0 right-0 h-full ${
              selectedCapsule ? 'w-full md:w-[740px]' : 'w-full md:w-[580px]'
            } max-w-full bg-[#030914]/95 border-l border-[#00B7FF]/35 shadow-[-20px_0_60px_rgba(0,183,255,0.18)] z-[9001] flex flex-col font-sans backdrop-blur-2xl`}
          >
            {/* ── Top Futuristic Stark Header ── */}
            <div className="px-5 py-4 border-b border-[#00B7FF]/25 bg-gradient-to-r from-[#00B7FF]/10 via-transparent to-[#001428] flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-[#00B7FF]/15 border border-[#00B7FF]/45 flex items-center justify-center text-lg shadow-[0_0_15px_rgba(0,183,255,0.3)]">
                  ⚡
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="font-orbitron text-sm sm:text-base tracking-[0.25em] text-[#DFFAFF] uppercase drop-shadow-[0_0_10px_rgba(0,183,255,0.6)]">
                      STARK DASHBOARD
                    </h2>
                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#22ff99]/15 border border-[#22ff99]/40 text-[8px] font-orbitron tracking-wider text-[#22ff99] uppercase">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#22ff99] animate-pulse shadow-[0_0_6px_#22ff99]" />
                      17/17 ONLINE
                    </span>
                  </div>
                  <p className="text-[10.5px] text-[#00B7FF]/80 font-mono tracking-wider mt-0.5">
                    {activeCount} MODULES ARMED · AUTONOMOUS CORES READY
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {selectedCapsule && (
                  <button
                    onClick={() => setSelectedCapsule(null)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#00B7FF]/15 border border-[#00B7FF]/40 text-[#00D9FF] text-[11px] font-orbitron tracking-wider uppercase transition hover:bg-[#00B7FF]/25 hover:border-[#00B7FF]"
                  >
                    <ArrowLeft size={13} /> Grid
                  </button>
                )}
                <button
                  onClick={onClose}
                  className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 text-[#DFFAFF] flex items-center justify-center transition"
                  title="Close Dashboard"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* ── Sub Navigation & Search Bar ── */}
            {!selectedCapsule && (
              <div className="px-5 py-3 border-b border-[#00B7FF]/15 bg-[#000814]/70 flex flex-col gap-3">
                {/* Search + Tab Bar */}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                  <div className="relative flex-1">
                    <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#00B7FF]/50" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search 17 capsules (e.g. 'email', 'coding', 'cpu')..."
                      className="w-full pl-9 pr-3 py-2 rounded-lg bg-[#020610]/90 border border-[#00B7FF]/25 text-[#DFFAFF] text-xs font-mono placeholder:text-[#00B7FF]/35 focus:outline-none focus:border-[#00D9FF] focus:shadow-[0_0_12px_rgba(0,217,255,0.25)] transition"
                    />
                    {searchQuery && (
                      <button
                        onClick={() => setSearchQuery('')}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-[#DFFAFF]/40 hover:text-[#DFFAFF]"
                      >
                        ✕
                      </button>
                    )}
                  </div>

                  <div className="flex gap-1.5 p-1 rounded-lg bg-[#020610]/80 border border-[#00B7FF]/20">
                    <button
                      onClick={() => setActiveTab('picker')}
                      className={`px-3 py-1.5 rounded text-[10px] font-orbitron tracking-wider uppercase transition flex items-center gap-1.5 ${
                        activeTab === 'picker'
                          ? 'bg-[#00B7FF]/25 text-[#00D9FF] border border-[#00B7FF]/50 shadow-[0_0_8px_rgba(0,183,255,0.3)]'
                          : 'text-[#DFFAFF]/60 hover:text-[#DFFAFF]'
                      }`}
                    >
                      <LayoutGrid size={12} /> Catalog
                    </button>
                    <button
                      onClick={() => setActiveTab('active')}
                      className={`px-3 py-1.5 rounded text-[10px] font-orbitron tracking-wider uppercase transition flex items-center gap-1.5 ${
                        activeTab === 'active'
                          ? 'bg-[#00B7FF]/25 text-[#00D9FF] border border-[#00B7FF]/50 shadow-[0_0_8px_rgba(0,183,255,0.3)]'
                          : 'text-[#DFFAFF]/60 hover:text-[#DFFAFF]'
                      }`}
                    >
                      <Eye size={12} /> Active ({activeCount})
                    </button>
                  </div>
                </div>

                {/* Category Pills */}
                {activeTab === 'picker' && (
                  <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
                    {CATEGORIES.map((cat) => {
                      const isSel = selectedCategory === cat;
                      return (
                        <button
                          key={cat}
                          onClick={() => setSelectedCategory(cat)}
                          className={`px-2.5 py-1 rounded-full text-[9.5px] font-orbitron tracking-wider uppercase whitespace-nowrap transition ${
                            isSel
                              ? 'bg-[#00D9FF]/20 text-[#00D9FF] border border-[#00D9FF]/60 shadow-[0_0_10px_rgba(0,217,255,0.2)]'
                              : 'bg-white/[0.03] text-[#DFFAFF]/50 border border-white/[0.06] hover:border-[#00B7FF]/30 hover:text-[#DFFAFF]'
                          }`}
                        >
                          {cat}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* ── Main Content Viewport ── */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
              {selectedCapsule && ActiveComponent ? (
                /* Selected Single Capsule Workspace */
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className="space-y-4"
                >
                  <div className="p-4 rounded-xl bg-gradient-to-r from-[#00B7FF]/10 via-[#001020] to-transparent border border-[#00B7FF]/30 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-3xl">{currentCapsuleObj?.icon}</span>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-orbitron text-base text-[#DFFAFF] tracking-wider uppercase font-semibold">
                            {currentCapsuleObj?.label}
                          </h3>
                          <span className="px-2 py-0.5 rounded text-[8.5px] font-orbitron tracking-wider bg-[#00B7FF]/15 text-[#00D9FF] border border-[#00B7FF]/30 uppercase">
                            {currentCapsuleObj?.category}
                          </span>
                        </div>
                        <p className="text-xs text-[#00B7FF]/80 font-mono mt-0.5">
                          {currentCapsuleObj?.tagline}
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={(e) => toggleCapsule(currentCapsuleObj.id, e)}
                      className={`px-3 py-1.5 rounded-lg text-[10px] font-orbitron tracking-wider uppercase transition flex items-center gap-1.5 ${
                        activeCapsules[currentCapsuleObj.id]
                          ? 'bg-[#22ff99]/20 text-[#22ff99] border border-[#22ff99]/50 shadow-[0_0_10px_rgba(34,255,153,0.3)]'
                          : 'bg-white/5 text-[#DFFAFF]/60 border border-white/10 hover:border-[#00B7FF]/40'
                      }`}
                    >
                      <Pin size={12} />
                      {activeCapsules[currentCapsuleObj.id] ? 'Pinned' : 'Pin to Active'}
                    </button>
                  </div>

                  <div className="rounded-xl border border-[#00B7FF]/25 bg-[#020612]/90 p-4 shadow-[0_8px_32px_rgba(0,0,0,0.5)]">
                    <ActiveComponent />
                  </div>
                </motion.div>
              ) : activeTab === 'picker' ? (
                /* Catalog Grid */
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {filteredCapsules.map((c) => {
                    const isActive = !!activeCapsules[c.id];
                    return (
                      <motion.div
                        key={c.id}
                        whileHover={{ scale: 1.02, y: -2 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => setSelectedCapsule(c.id)}
                        className={`group relative p-4 rounded-xl border cursor-pointer transition-all duration-300 flex flex-col justify-between gap-3 ${
                          isActive
                            ? 'bg-gradient-to-br from-[#00B7FF]/15 via-[#001020]/90 to-[#020610] border-[#00B7FF]/50 shadow-[0_0_20px_rgba(0,183,255,0.12)]'
                            : 'bg-gradient-to-br from-[#001428]/40 via-[#010814]/80 to-[#02040a] border-white/[0.08] hover:border-[#00B7FF]/40 hover:shadow-[0_0_18px_rgba(0,183,255,0.1)]'
                        }`}
                      >
                        {/* Header with Icon & Pin Button */}
                        <div className="flex items-center justify-between">
                          <div className="w-10 h-10 rounded-lg bg-[#00B7FF]/10 border border-[#00B7FF]/20 flex items-center justify-center text-xl group-hover:scale-110 group-hover:border-[#00B7FF]/50 transition shadow-[0_0_10px_rgba(0,183,255,0.15)]">
                            {c.icon}
                          </div>
                          
                          <div className="flex items-center gap-1.5">
                            <button
                              onClick={(e) => toggleCapsule(c.id, e)}
                              title={isActive ? 'Active module' : 'Click to activate'}
                              className={`px-2 py-0.5 rounded text-[8.5px] font-orbitron tracking-widest uppercase transition ${
                                isActive
                                  ? 'bg-[#22ff99]/20 text-[#22ff99] border border-[#22ff99]/50 shadow-[0_0_8px_rgba(34,255,153,0.3)] font-bold'
                                  : 'bg-white/5 text-[#DFFAFF]/40 border border-white/10 hover:border-[#00B7FF]/40 hover:text-[#00D9FF]'
                              }`}
                            >
                              {isActive ? '● ARMED' : 'OFF'}
                            </button>
                          </div>
                        </div>

                        {/* Title & Description */}
                        <div>
                          <div className="flex items-center justify-between">
                            <h4 className="font-orbitron text-xs sm:text-sm font-bold text-[#DFFAFF] group-hover:text-[#00D9FF] tracking-wider uppercase transition">
                              {c.label}
                            </h4>
                            <span className="text-[9px] font-mono text-[#00B7FF]/60 uppercase">
                              {c.category}
                            </span>
                          </div>
                          <p className="text-[10px] text-[#DFFAFF]/60 font-sans line-clamp-2 mt-1 leading-relaxed">
                            {c.description}
                          </p>
                        </div>

                        {/* Footer Launch Indicator */}
                        <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between text-[9px] font-orbitron tracking-widest text-[#00D9FF]/70 group-hover:text-[#00D9FF] uppercase">
                          <span>LAUNCH CAPSULE</span>
                          <span className="transform group-hover:translate-x-1 transition">→</span>
                        </div>
                      </motion.div>
                    );
                  })}
                  {filteredCapsules.length === 0 && (
                    <div className="col-span-full py-16 text-center text-[#DFFAFF]/40 font-mono text-xs">
                      No capsules found matching "{searchQuery}".
                    </div>
                  )}
                </div>
              ) : (
                /* Active Capsules Multi-Stream */
                <div className="space-y-4">
                  {activeCount === 0 ? (
                    <div className="py-16 text-center space-y-3">
                      <div className="text-4xl">⚡</div>
                      <h4 className="font-orbitron text-sm text-[#DFFAFF] tracking-wider uppercase">
                        No Active Capsules Armed
                      </h4>
                      <p className="text-xs text-[#00B7FF]/60 font-mono max-w-sm mx-auto">
                        Switch to the <b>Catalog</b> tab and click "OFF" to arm and pin modules into your telemetry stream.
                      </p>
                      <button
                        onClick={() => setActiveTab('picker')}
                        className="px-4 py-2 rounded-lg bg-[#00B7FF]/20 border border-[#00B7FF]/50 text-[#00D9FF] font-orbitron text-xs tracking-wider uppercase hover:bg-[#00B7FF]/35 transition"
                      >
                        Open Capsule Catalog
                      </button>
                    </div>
                  ) : (
                    CAPSULES_CATALOG.filter((c) => activeCapsules[c.id]).map((c) => {
                      const Comp = c.component;
                      return (
                        <motion.div
                          key={c.id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="rounded-xl border border-[#00B7FF]/30 bg-[#020612]/90 overflow-hidden shadow-[0_8px_30px_rgba(0,0,0,0.6)]"
                        >
                          <div className="px-4 py-3 bg-gradient-to-r from-[#00B7FF]/15 via-[#001020] to-[#020612] border-b border-[#00B7FF]/20 flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                              <span className="text-lg">{c.icon}</span>
                              <div>
                                <span className="font-orbitron text-xs font-bold text-[#00D9FF] tracking-wider uppercase">
                                  {c.label}
                                </span>
                                <span className="text-[8.5px] font-mono text-[#00B7FF]/60 ml-2 uppercase">
                                  {c.category}
                                </span>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => setSelectedCapsule(c.id)}
                                className="px-2.5 py-1 rounded bg-[#00B7FF]/15 border border-[#00B7FF]/40 text-[#00D9FF] text-[9px] font-orbitron tracking-wider uppercase hover:bg-[#00B7FF]/30 transition"
                              >
                                Maximize ↗
                              </button>
                              <button
                                onClick={(e) => toggleCapsule(c.id, e)}
                                className="px-2 py-1 text-[9px] font-mono text-red-400 hover:text-red-300 transition"
                              >
                                Unpin
                              </button>
                            </div>
                          </div>
                          <div className="p-4">
                            <Comp />
                          </div>
                        </motion.div>
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
