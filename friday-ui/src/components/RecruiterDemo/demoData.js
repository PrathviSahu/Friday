/**
 * demoData.js — Deterministic, recruiter-safe demonstration dataset.
 *
 * Explicitly labeled DEMO / MOCK / DRY-RUN.
 * Contains realistic job listings, applicant match data, mock recruiter emails,
 * mock interview calendar events, and architecture specifications.
 */

export const DEMO_CAPABILITIES = [
  { id: 'voice', icon: '🎙️', name: 'Voice AI & Neural TTS', desc: 'Sub-40ms fast-path intent engine with Microsoft Edge neural voice synthesis.' },
  { id: 'career', icon: '💼', name: 'Career Intelligence & ATS', desc: 'Autonomous job scraping, semantic JD match, skill gap analysis & packet assembly.' },
  { id: 'email', icon: '✉️', name: 'Email Agent & Safe Send', desc: 'Draft synthesis, multi-turn editing, and cryptographic SHA-256 approval gates.' },
  { id: 'calendar', icon: '📅', name: 'Calendar Scheduling', desc: 'Conflict detection, timezone calculation, and collision-free meeting booking.' },
  { id: 'trading', icon: '📈', name: 'Quantum Trading & TA', desc: 'Real-time candlestick charts with RSI, MACD, Bollinger Bands in read-only mode.' },
  { id: 'memory', icon: '🧠', name: 'Context & Memory Graph', desc: 'Persistent long-term facts with Google Gemini vector RAG and domain routing.' },
  { id: 'security', icon: '🛡️', name: 'Human-in-the-Loop Gate', desc: 'Cryptographic execution tokens, constant-time validation & single-use approvals.' },
];

export const DEMO_JOBS = [
  {
    id: 'demo_job_1',
    title: 'Senior Java Backend Engineer',
    company: 'FinTech Cloud Nexus',
    location: 'Mumbai, India (Hybrid)',
    salary: '₹14,00,000 - ₹18,00,000 / year',
    matchScore: 94,
    skills: ['Java 21', 'Spring Boot 3', 'Microservices', 'PostgreSQL', 'Kafka', 'Docker'],
    missingSkills: ['Kubernetes (Advanced)', 'GraphQL'],
    atsScore: 92,
    source: 'RemoteOK (Verified Partner)',
    description: 'Lead backend microservices development for high-frequency payment gateways with sub-50ms latency requirements.',
    badge: 'TOP MATCH',
  },
  {
    id: 'demo_job_2',
    title: 'Full-Stack Software Development Engineer',
    company: 'Quantum Scale AI',
    location: 'Bengaluru / Remote',
    salary: '₹12,00,000 - ₹16,00,000 / year',
    matchScore: 89,
    skills: ['Java', 'Spring Boot', 'React.js', 'TailwindCSS', 'REST APIs', 'FastAPI'],
    missingSkills: ['Redis Cluster'],
    atsScore: 88,
    source: 'Direct Portal',
    description: 'Build end-to-end intelligent dashboards and reactive UI interfaces backed by robust Spring Boot microservices.',
    badge: 'HIGH FIT',
  },
  {
    id: 'demo_job_3',
    title: 'Distributed Systems Platform Engineer',
    company: 'AeroCloud Systems',
    location: 'Pune / Remote',
    salary: '₹15,00,000 - ₹20,00,000 / year',
    matchScore: 82,
    skills: ['Java', 'Distributed Systems', 'gRPC', 'PostgreSQL'],
    missingSkills: ['Rust', 'eBPF'],
    atsScore: 79,
    source: 'Curated Demo',
    description: 'Architect mission-critical edge gateways with automated self-healing and zero-downtime rolling deploys.',
    badge: 'STRONG FIT',
  }
];

export const DEMO_EMAIL_THREAD = {
  id: 'demo_email_1',
  from: 'Sarah Jenkins <sarah.jenkins@fintechnexus.com>',
  subject: 'Interview Invitation: Senior Java Backend Engineer @ FinTech Cloud Nexus',
  date: 'Today at 10:45 AM',
  preview: 'Hi Prem, We reviewed your face recognition and AI operating system projects on GitHub...',
  fullBody: `Hi Prem,\n\nWe were extremely impressed by your F.R.I.D.A.Y. AI operating system repository and your Java/Spring Boot microservices architecture.\n\nWe would love to invite you for a 45-minute Technical Architecture discussion this Thursday at 3:00 PM IST.\n\nPlease let us know if that time works for you!\n\nBest regards,\nSarah Jenkins\nSenior Technical Recruiter | FinTech Cloud Nexus`,
  draftResponse: {
    to: 'sarah.jenkins@fintechnexus.com',
    subject: 'Re: Interview Invitation: Senior Java Backend Engineer @ FinTech Cloud Nexus',
    body: `Hi Sarah,\n\nThank you for reaching out! I would be delighted to speak with the FinTech Cloud Nexus team regarding the Senior Java Backend Engineer role.\n\nThursday at 3:00 PM IST works perfectly for me. Looking forward to our conversation!\n\nBest regards,\nPrathvi Sahu (Prem)\nFull-Stack SDE | github.com/prathvisahu`,
    status: 'DRAFT_PREPARED (APPROVAL_REQUIRED)',
    securityHash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  }
};

export const DEMO_CALENDAR_EVENT = {
  title: 'Tech Architecture Interview — FinTech Cloud Nexus',
  time: 'Thursday, Aug 20, 2026 · 3:00 PM - 3:45 PM IST',
  attendees: ['sarah.jenkins@fintechnexus.com', 'prem.sahu@friday.local'],
  location: 'Google Meet (Video Call)',
  collisionCheck: '0 Collisions Detected · Schedule Conflict Free',
  status: 'PROPOSED_EVENT (APPROVAL_REQUIRED)',
};

export const DEMO_TOUR_STEPS = [
  {
    step: 1,
    title: 'Meet F.R.I.D.A.Y.',
    subtitle: 'Personal AI Operating System',
    description: 'Engineered from scratch by Prathvi Sahu (Prem). An autonomous desktop assistant with Voice AI, Career Intelligence, and human-in-the-loop safeguards.',
    prompt: 'Who made you and what can you do?',
    response: 'I am F.R.I.D.A.Y., engineered by Prathvi Sahu (Prem), a Full-Stack SDE (Java/Spring Boot & React). I orchestrate voice control, job matching, email drafting, and real-time trading analysis.',
  },
  {
    step: 2,
    title: 'Sub-40ms Fast Path Intent Routing',
    subtitle: 'Instant Local Actions vs Neural Inference',
    description: 'Deterministic security handler intercepts system commands in <1ms without network round-trips.',
    prompt: 'Lock workstation display',
    response: 'Workstation display locked, Prem. All background sessions remain secured.',
    metric: '0.95 ms Local Execution',
  },
  {
    step: 3,
    title: 'Autonomous Career Intelligence',
    subtitle: 'Semantic Resume & Job Matcher',
    description: 'Analyzes JD requirements against verified skills with cosine semantic matching and ATS gap detection.',
    prompt: 'Find me Java roles above 12 LPA',
    response: 'Found 3 matching roles. Top match: Senior Java Backend Engineer at FinTech Cloud Nexus (94% match, ₹14-18 LPA).',
  },
  {
    step: 4,
    title: 'Deterministic Application Preparation',
    subtitle: 'Tailored Packet & Cover Letter Synthesis',
    description: 'Generates tailored application packet with cryptographic SHA-256 hash binding. Zero unauthorized submissions.',
    prompt: 'Prepare application for FinTech Cloud Nexus',
    response: 'Application packet assembled: Resume v3.2 selected, tailored cover letter generated, 2 skill gaps flagged. Ready for your review.',
  },
  {
    step: 5,
    title: 'Cryptographic Email & Calendar Gate',
    subtitle: 'Human-in-the-Loop Execution Boundary',
    description: 'Email and Calendar drafts require explicit owner approval. Modifying draft automatically bumps version and invalidates old tokens.',
    prompt: 'Draft reply to Sarah Jenkins for Thursday 3 PM',
    response: 'Interview confirmation drafted for Thursday 3:00 PM IST. Single-use approval token bound to SHA-256 draft hash. Action: DRY-RUN.',
  },
  {
    step: 6,
    title: 'Quantum Trading & Market Analysis',
    subtitle: 'Live Candlestick & Technical Indicators',
    description: 'Real-time WebSocket market feeds with multi-indicator technical analysis (RSI, MACD, SMA) in strict read-only mode.',
    prompt: 'Analyze BTC price momentum',
    response: 'BTC/USDT at $94,320. RSI (14) at 54.2 (Neutral). MACD bullish cross confirmed on 4H chart. No trading mutations enabled.',
  },
  {
    step: 7,
    title: 'Multi-Turn Context & Conversational Memory',
    subtitle: 'Cross-Domain Anaphora Resolution',
    description: 'Remembers pronouns and active entities across domain switches without re-explaining context.',
    prompt: 'What was the company name again?',
    response: 'The company is FinTech Cloud Nexus for the Senior Java Backend Engineer role.',
  },
  {
    step: 8,
    title: 'Architecture & Security Transparency',
    subtitle: 'Full-Stack Production Blueprint',
    description: 'Every subsystem is auditable: Rate limiting, CORS hardening, Fernet encryption, and constant-time token verification.',
    prompt: 'Show system architecture',
    response: 'Architecture: React/Vite (Vercel CDN) ➔ FastAPI Core (Render Docker) ➔ Groq Llama 3.3 70B & Edge-TTS ➔ SQLite WAL.',
  }
];

export const DEMO_ARCHITECTURE_LAYERS = [
  { layer: 'VOICE_STT', title: '1. Voice Audio & Speech-to-Text', desc: 'Browser Web Audio API ➔ Fast Whisper neural speech transcription with barge-in cancellation.' },
  { layer: 'INTENT_BRAIN', title: '2. Dual-Engine Intent Router', desc: 'Sub-1ms deterministic regex fast-path router ➔ Groq Llama 3.3 70B cloud fallback.' },
  { layer: 'CONTEXT_MEMORY', title: '3. Context Engine & Vector RAG', desc: 'Short-term session memory + Google Gemini text-embedding-004 long-term semantic memory.' },
  { layer: 'TOOL_EXECUTION', title: '4. Autonomous Agent Tools', desc: 'Career OS, Yahoo Finance TA, macOS control, Email draft, Calendar collision detector.' },
  { layer: 'SECURITY_GATE', title: '5. Cryptographic Approval Gate', desc: 'Single-use UUID approval tokens bound to SHA-256 payload digests. Zero blind mutations.' },
  { layer: 'AUDIT_PERSIST', title: '6. WAL Audit & Persistence', desc: 'SQLite 3 WAL database recording immutable audit logs with Fernet encrypted secrets.' },
];
