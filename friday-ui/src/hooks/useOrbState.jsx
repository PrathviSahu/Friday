import { createContext, useContext, useRef, useState, useEffect, useCallback } from 'react';
import gsap from 'gsap';
import { useMicrophone } from './useMicrophone';
import { useFriday } from '../context/FridayContext';
import { useAudioQueue } from './useAudioQueue';
import { speak as backendSpeak } from '../services/ttsService';
import { vault } from '../services/secureVault';
import { unlockWithFingerprint } from '../hooks/useFingerprint';
// NOTE: spoken passphrase auth removed. Admin access is now granted via
// fingerprint or a WRITTEN (typed) password — see authenticateWithPassword.

// ── State definitions ────────────────────────────────────────────────────────
const STATE_CONFIG = {
    OFF:        { color: [0.0,  0.0,   0.0],  bloom: 0.0, ringSpeed: 0.0, label: ''                          },
    BOOTING:    { color: [0.0,  0.55,  0.9],  bloom: 0.4, ringSpeed: 0.3, label: 'INITIALIZING...'           },
    IDLE:       { color: [0.0,  0.55,  0.9],  bloom: 0.6, ringSpeed: 0.8, label: 'ONLINE AND READY'          },
    LISTENING:  { color: [1.0,  0.35,  0.0],  bloom: 1.4, ringSpeed: 2.8, label: 'LISTENING...'             },
    THINKING:   { color: [1.0,  0.50,  0.0],  bloom: 1.6, ringSpeed: 3.5, label: 'PROCESSING...'            },
    SPEAKING:   { color: [0.0,  0.80,  1.0],  bloom: 1.9, ringSpeed: 4.8, label: 'SPEAKING...'              },
    VERIFYING:  { color: [0.0,  0.55,  0.9],  bloom: 1.8, ringSpeed: 5.0, label: 'VERIFYING IDENTITY...'    },
    UNLOCKING:  { color: [0.0,  0.55,  0.9],  bloom: 2.5, ringSpeed: 7.0, label: 'IDENTITY CONFIRMED'       },
    UNLOCKED:   { color: [0.0,  0.55,  0.9],  bloom: 0.6, ringSpeed: 1.2, label: 'MONITORING SYSTEMS'       },
};

// Contextual idle messages that rotate
const IDLE_MESSAGES = [
    'ONLINE AND READY',
    'AWAITING YOUR COMMAND, BOSS.',
    'LISTENING FOR WAKE WORD.',
    'SECURE MODE ACTIVE.',
    'MONITORING SYSTEMS.',
    'ALL SYSTEMS NOMINAL.',
    'STANDING BY.',
];

const OrbContext = createContext(null);

export function OrbProvider({ children }) {
    const [appState,   setAppState]   = useState('BOOTING');
    const [stateLabel, setLabel]      = useState('INITIALIZING...');
    const [responseMessage, setResponseMessage] = useState('');
    const [voices, setVoices] = useState([]);
    const [voiceName, setVoiceName] = useState(typeof window !== 'undefined' ? localStorage.getItem('friday_voice') || '' : '');
    const [audioEnabled, setAudioEnabled] = useState(typeof window !== 'undefined' ? (localStorage.getItem('friday_audio_enabled') === 'true') : false);
    const [ttsLoading, setTtsLoading] = useState(false);
    const [isHovered,  setIsHovered]  = useState(false);
    const [authStep,   setAuthStep]   = useState(null); // null | auth step object
    const [workspace,  setWorkspace]  = useState('lockscreen');
    const [conversationMode, setConversationMode] = useState('idle');
    const [wakeCount, setWakeCount] = useState(0);
    // ── Access model ─────────────────────────────────────────────────────────
    // Two modes:
    //   'normal' — anyone can issue voice commands, no authentication.
    //   'admin'  — privileged; requires fingerprint OR a written (typed)
    //              password before commands are accepted. Opens locked by default.
    // There is NO spoken passphrase anymore.
    const [mode, setModeState] = useState('admin');
    const [adminAuthed, setAdminAuthed] = useState(false);
    // `locked` is derived: normal mode is never locked; admin mode is locked
    // until the user authenticates. Defaults to locked (admin).
    const [locked, setLocked] = useState(true);
    const lockedRef = useRef(true);
    const modeRef = useRef('admin');
    const adminAuthedRef = useRef(false);
    const idleMsgRef  = useRef(0);
    const idleTimer   = useRef(null);
    const commandTimersRef = useRef([]);
    const failedAttemptsRef = useRef(0);
    const { micEnabled, setMicEnabled, setState } = useFriday();

    // Call real microphone hook
    const { audioLevelRef, waveformRef, start: startMic, stop: stopMic } = useMicrophone();

    const uniforms = useRef({
        color:      [0.0, 0.35, 0.65],
        bloom:      0.4,
        ringSpeed:  0.3,
        audioLevel: 0.0,
        isHovered:  false,
        breathScale: 1.0,
    });

    // Single AudioContext, created + resumed on the first user gesture and kept
    // alive. Playback through a BufferSource on a running context is never
    // autoplay-blocked — this is what makes backend TTS audio actually sound.
    const audioCtxRef = useRef(null);

    // ── Transition ────────────────────────────────────────────────────────────
    const transitionTo = useCallback((nextState) => {
        const cfg = STATE_CONFIG[nextState];
        if (!cfg) return;

        clearInterval(idleTimer.current);
        setLabel(cfg.label);

        gsap.to(uniforms.current, {
            bloom:     cfg.bloom,
            ringSpeed: cfg.ringSpeed,
            duration:  1.2,
            ease:      'power2.inOut',
        });
        gsap.to(uniforms.current.color, {
            0: cfg.color[0],
            1: cfg.color[1],
            2: cfg.color[2],
            duration: 1.2,
            ease: 'power2.inOut',
            onComplete: () => {
                setAppState(nextState);
                // Rotate idle messages after settling
                if (nextState === 'IDLE') startIdleRotation();
            },
        });
    }, []);

    // ── Idle message rotation ────────────────────────────────────────────────
    const startIdleRotation = useCallback(() => {
        clearInterval(idleTimer.current);
        idleTimer.current = setInterval(() => {
            idleMsgRef.current = (idleMsgRef.current + 1) % IDLE_MESSAGES.length;
            setLabel(IDLE_MESSAGES[idleMsgRef.current]);
        }, 4500);
    }, []);

    // ── Authentication sequence ──────────────────────────────────────────────
    // Shortened authentication for faster unlock experience
    const AUTH_STEPS = [
        { id: 'voice_detected', label: 'VOICE',        icon: '🎙️', delay: 0     },  // Quick detection
        { id: 'identity',       label: 'ID CONFIRMED', icon: '✓', delay: 500 },  // Fast identity check
        { id: 'welcome',        label: 'WELCOME',    icon: '★', delay: 800 },  // Immediate welcome
    ];
    useEffect(() => {
        return () => {
            (commandTimersRef.current || []).forEach((timerId) => clearTimeout(timerId));
            commandTimersRef.current = [];
        };
    }, []);

    // Keep live refs so speech callbacks (which may capture a stale closure)
    // read current auth state.
    useEffect(() => { lockedRef.current = locked; }, [locked]);
    useEffect(() => { modeRef.current = mode; }, [mode]);
    useEffect(() => { adminAuthedRef.current = adminAuthed; }, [adminAuthed]);
    // Admin mode is locked until authenticated; normal mode is always open.
    useEffect(() => {
        setLocked(mode === 'admin' && !adminAuthed);
    }, [mode, adminAuthed]);

    // Command/animation timers shared across the wake response and real auth flows.
    const clearCommandTimers = useCallback(() => {
        (commandTimersRef.current || []).forEach((timerId) => clearTimeout(timerId));
        commandTimersRef.current = [];
    }, []);

    const scheduleTimer = useCallback((callback, delay) => {
        const timerId = window.setTimeout(callback, delay);
        commandTimersRef.current.push(timerId);
    }, []);
    const playTone = useCallback(() => {
        if (typeof window === 'undefined') return;
        try {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (!AudioCtx) return;
            const ctx = new AudioCtx();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(440, ctx.currentTime);
            gain.gain.setValueAtTime(0.08, ctx.currentTime);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            setTimeout(() => {
                gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.15);
                osc.stop(ctx.currentTime + 0.2);
                setTimeout(() => { try { ctx.close(); } catch (e) {} }, 300);
            }, 1);
        } catch (e) {
            // ignore tone failure
        }
    }, []);

    const playAudioAsset = useCallback(async (assetPath) => {
        if (typeof window === 'undefined') return false;
        try {
            const response = await fetch(assetPath);
            if (!response.ok) return false;
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            audio.volume = 1.0;
            return new Promise((resolve) => {
                const cleanup = () => {
                    URL.revokeObjectURL(url);
                    audio.onended = null;
                    audio.onerror = null;
                };
                audio.onended = () => {
                    cleanup();
                    resolve(true);
                };
                audio.onerror = () => {
                    cleanup();
                    resolve(false);
                };
                audio.play().catch(() => {
                    cleanup();
                    resolve(false);
                });
            });
        } catch (e) {
            return false;
        }
    }, []);

    // Initialize audio queue for backend-played audio files
    const { enqueue, stop: queueStop, clear: queueClear, isPlaying: queueIsPlaying } = useAudioQueue({
        audioContextRef: audioCtxRef,
        onStart: () => {
            setResponseMessage((msg) => msg);
            transitionTo('SPEAKING');
        },
        onEnd: () => {
            transitionTo('IDLE');
            setResponseMessage('');
        },
        onError: (e) => {
            console.warn('Audio queue error', e);
        },
    });

    const speakText = useCallback(async (text) => {
        if (typeof window === 'undefined') return false;
        // Try backend Edge TTS first (asynchronously generate and enqueue audio)
        try {
            setTtsLoading(true);
            const url = await backendSpeak(text);
            if (url) {
                // enqueue backend audio for playback
                enqueue(url);
                setTtsLoading(false);
                return true;
            }
        } catch (err) {
            console.warn('Backend TTS failed, falling back to browser TTS', err);
            setTtsLoading(false);
        }

        const CUSTOM_VOICE_ASSETS = {
            'en-IE-EmilyNeural': '/voices/en-IE-EmilyNeural.mp3',
        };

        // If a pre-generated Edge Neural asset exists for this voice, play it instead
        if (voiceName && CUSTOM_VOICE_ASSETS[voiceName]) {
            const played = await playAudioAsset(CUSTOM_VOICE_ASSETS[voiceName]);
            if (played) return true;
        }

        if (!window.speechSynthesis) {
            playTone();
            return false;
        }

        try {
            window.speechSynthesis.resume?.();
        } catch (e) {
            // ignore resume failures
        }

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;
        const available = window.speechSynthesis.getVoices() || [];
        const normalize = (input = '') => input.toString().toLowerCase();
        const voiceLabel = (voice) => `${normalize(voice.name)} ${normalize(voice.voiceURI)} ${normalize(voice.lang)}`;

        const preferenceMatchers = [
            /emily|emilyneural/, // top priority
            /neural/,
            /google uk english female/, // good Chrome voice
            /google uk english male/, // still better than default
            /google us english/, // high-quality US voice
            /microsoft zira desktop/, // good Windows voice
            /microsoft heather desktop/,
            /microsoft hazel desktop/, 
            /en-IE/, // prefer Irish if available
            /en-GB/, // UK English fallback
            /en-US/, // US English fallback
            /en-/, // any English voice
        ];

        const scoreVoice = (voice) => {
            const label = voiceLabel(voice);
            let score = 0;

            for (let i = 0; i < preferenceMatchers.length; i += 1) {
                if (preferenceMatchers[i].test(label)) {
                    score += (preferenceMatchers.length - i) * 15;
                }
            }
            if (/default|native|standard/.test(label)) score -= 20;
            if (/female|woman|woman/.test(label)) score += 5;
            if (/male|man|paul|david|alex/.test(label) && !/neural/.test(label)) score -= 10;
            return score;
        };

        const findBestAvailableVoice = () => {
            if (!available.length) return null;
            return available.slice().sort((a, b) => scoreVoice(b) - scoreVoice(a))[0];
        };

        const matchesVoiceName = (x) => x.name === voiceName || x.voiceURI === voiceName;
        let v = null;
        if (voiceName) v = available.find(matchesVoiceName);
        if (!v) v = findBestAvailableVoice();
        if (v) {
            utterance.voice = v;
            if (v.name !== voiceName && v.voiceURI !== voiceName) {
                setVoiceName(v.name);
            }
            console.debug('Friday selected TTS voice:', v.name, v.voiceURI, v.lang);
        } else {
            console.warn('Friday could not find any speechSynthesis voice, using default output');
        }

        return new Promise((resolve) => {
            let resolved = false;
            let timeoutId;
            const finish = (result) => {
                if (resolved) return;
                resolved = true;
                clearTimeout(timeoutId);
                resolve(result);
            };
            utterance.onstart = () => finish(true);
            utterance.onerror = () => finish(false);
            utterance.onend = () => finish(true);
            try {
                window.speechSynthesis.cancel();
                window.speechSynthesis.speak(utterance);
                timeoutId = setTimeout(() => finish(false), 4000);
            } catch (e) {
                console.warn('SpeechSynthesis speak failed', e);
                finish(false);
            }
        }).then((started) => {
            if (!started) {
                playTone();
            }
            return started;
        });
    }, [playAudioAsset, playTone, voiceName, enqueue]);

    // Attempt to unlock audio autoplay by briefly playing a silent buffer.
    const unlockAudio = useCallback(async () => {
        if (typeof window === 'undefined') return;
        try {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (!AudioCtx) return;
            let ctx = audioCtxRef.current;
            if (!ctx) {
                ctx = new AudioCtx();
                audioCtxRef.current = ctx;
            }
            // resume context (some browsers start it suspended until a gesture)
            if (ctx.state === 'suspended') await ctx.resume();
            // play a 1-frame silent buffer to satisfy autoplay-unlock policies
            const buffer = ctx.createBuffer(1, 1, ctx.sampleRate);
            const src = ctx.createBufferSource();
            src.buffer = buffer;
            src.connect(ctx.destination);
            src.start(0);
            // NOTE: intentionally do NOT close the context — it is reused for
            // all playback so audio is never autoplay-blocked.
        } catch (e) {
            // ignore; best-effort
        }
    }, []);

    // Load available voices and keep updated
    useEffect(() => {
        if (typeof window === 'undefined' || !window.speechSynthesis) return;
        const preferredPattern = /emily|emilyneural/i;

        const findPreferredVoice = (vs) => {
            return vs.find(v => preferredPattern.test(`${v.name} ${v.voiceURI}`) && (v.lang || '').startsWith('en-IE'))
                || vs.find(v => preferredPattern.test(`${v.name} ${v.voiceURI}`))
                || vs.find(v => (v.lang || '').startsWith('en-IE'))
                || vs.find(v => (v.lang || '').startsWith('en'))
                || vs[0];
        };

        const load = () => {
            const vs = window.speechSynthesis.getVoices() || [];
            setVoices(vs);
            if (!vs.length) return;

            const storedVoice = voiceName ? vs.find(v => v.name === voiceName || v.voiceURI === voiceName) : null;
            const preferredVoice = findPreferredVoice(vs);
            const storedIsPreferred = storedVoice && preferredPattern.test(`${storedVoice.name} ${storedVoice.voiceURI}`);

            if (!storedVoice || !storedIsPreferred) {
                // Override an old stored voice if a better preferred option exists.
                setVoiceName(preferredVoice.name);
            } else if (!voiceName && preferredVoice) {
                setVoiceName(preferredVoice.name);
            }
        };
        load();
        window.speechSynthesis.onvoiceschanged = load;
        return () => { window.speechSynthesis.onvoiceschanged = null; };
    }, [voiceName]);

    // enable audio via user gesture: unlock audio and optionally speak a confirmation
    const enableAudioFromGesture = useCallback(async (opts = { speakConfirmation: true }) => {
        if (typeof window === 'undefined') return false;
        try {
            try {
                window.speechSynthesis?.resume?.();
            } catch (e) {
                // ignore resume failures
            }
            unlockAudio();
            setAudioEnabled(true);
            // Enabling voice also turns on the microphone, otherwise FRIDAY can
            // speak but never hear the user's commands.
            setMicEnabled(true);
            try {
                if (typeof window !== 'undefined') localStorage.setItem('friday_audio_enabled', 'true');
            } catch (e) {}

            if (opts.speakConfirmation) {
                playTone();
                try {
                    window.speechSynthesis?.resume?.();
                } catch (e) {}
                const conf = 'Voice engine online.';
                const started = await speakText(conf);
                setResponseMessage(conf);
                if (!started) {
                    setResponseMessage('Voice enabled. Audio may still be blocked.');
                }
                setTimeout(() => setResponseMessage(''), 1600);
            }
            return true;
        } catch (e) {
            console.warn('enableAudioFromGesture failed', e);
            return false;
        }
    }, [unlockAudio, speakText, setMicEnabled]);

    // persist voice selection
    useEffect(() => {
        try {
            if (typeof window !== 'undefined') localStorage.setItem('friday_voice', voiceName || '');
        } catch (e) {}
    }, [voiceName]);

    // persist whether audio was enabled via user gesture
    useEffect(() => {
        try {
            if (typeof window !== 'undefined') localStorage.setItem('friday_audio_enabled', audioEnabled ? 'true' : 'false');
        } catch (e) {}
    }, [audioEnabled]);

    // ── Admin authentication ──────────────────────────────────────────────────
    // Admin access is granted ONLY by fingerprint or a written (typed) password.
    // No spoken passphrase. On success we play the verification animation and
    // mark the session as admin-authed.
    const playUnlockAnimation = useCallback(() => {
        // Unlock is triggered by a user gesture (fingerprint / password submit),
        // so this is a valid moment to bring audio + mic online. FRIDAY should
        // start listening and be able to speak immediately after unlock.
        try { unlockAudio(); } catch (e) { /* ignore */ }
        setAudioEnabled(true);
        setMicEnabled(true);
        try { if (typeof window !== 'undefined') localStorage.setItem('friday_audio_enabled', 'true'); } catch (e) {}

        transitionTo('LISTENING');
        setAuthStep(AUTH_STEPS[0]);
        setResponseMessage('');
        let maxDelay = 0;
        AUTH_STEPS.forEach((step) => {
            maxDelay = Math.max(maxDelay, step.delay);
            scheduleTimer(() => {
                setAuthStep(step);
                if (step.id === 'scanning_voice') transitionTo('THINKING');
                if (step.id === 'voice_match')    transitionTo('VERIFYING');
                if (step.id === 'identity')       transitionTo('UNLOCKING');
            }, step.delay);
        });

        scheduleTimer(() => {
            setAdminAuthed(true);
            setWorkspace('unlocked');
            setAuthStep(null);
            setResponseMessage('');
            setConversationMode('idle');
            transitionTo('UNLOCKED');
            setState('verified');
        }, maxDelay + 2200);
    }, [transitionTo, setState, scheduleTimer, unlockAudio, setMicEnabled]);

    // Switch between 'normal' and 'admin'. Leaving admin drops privileges.
    const setMode = useCallback((next) => {
        if (next !== 'admin' && next !== 'normal') return;
        setModeState(next);
        if (next === 'normal') {
            vault.lock();
            setAdminAuthed(false);
            setWorkspace('unlocked');
            setAuthStep(null);
            setResponseMessage('');
            transitionTo('IDLE');
        }
    }, [transitionTo]);

    // Lock down: drop admin privileges and return to the admin lock screen.
    const lockNow = useCallback(() => {
        vault.lock();
        setAdminAuthed(false);
        setWorkspace('lockscreen');
        setAuthStep(null);
        setResponseMessage('');
        setConversationMode('idle');
        setState('idle');
        transitionTo('IDLE');
    }, [transitionTo, setState]);

    // Written (typed) password sign-in for admin mode. The first password ever
    // entered becomes the admin password (creates the vault); later sign-ins
    // must match it. Returns { ok } and speaks a denial on failure.
    const authenticateWithPassword = useCallback(async (password) => {
        const pw = String(password || '').trim();
        if (!pw) return { ok: false, reason: 'empty' };
        try {
            const ok = await vault.unlock(pw);
            if (ok) {
                failedAttemptsRef.current = 0;
                playUnlockAnimation();
                return { ok: true };
            }
            failedAttemptsRef.current += 1;
            const intruder = failedAttemptsRef.current >= 3;
            if (intruder) failedAttemptsRef.current = 0;
            const msg = intruder
                ? 'You are not my boss. Unauthorized access attempt detected.'
                : 'That is not the password.';
            setResponseMessage(msg);
            speakText(msg);
            return { ok: false, reason: 'wrong', intruder };
        } catch (err) {
            console.warn('Vault unlock failed:', err);
            const msg = 'Secure crypto is unavailable here — use a localhost origin or password.';
            setResponseMessage(msg);
            return { ok: false, reason: 'crypto', error: err && err.message };
        }
    }, [playUnlockAnimation, speakText]);

    const unlockWithFingerprintFlow = useCallback(async () => {
        if (modeRef.current !== 'admin' || !lockedRef.current) return { ok: false, reason: 'blocked' };
        const res = await unlockWithFingerprint();
        if (res.ok) {
            playUnlockAnimation();
        } else if (res.reason === 'cancelled') {
            setResponseMessage('Fingerprint cancelled.');
        } else if (res.reason === 'unsupported') {
            setResponseMessage('Fingerprint not supported on this device.');
        } else {
            setResponseMessage('Fingerprint unavailable.');
        }
        return res;
    }, [playUnlockAnimation]);

    const runAuthSequence = useCallback((command = 'wake', opts = { speakImmediately: false }) => {
        const wakeResponses = [
            'Yes boss? I am listening.',
            'You rang? Speak clearly this time.',
            'What is it now? Make it quick.',
        ];

        const responseMap = {
            trading: 'Opening trading systems now.',
            engineering: 'Opening the engineering console.',
            lock: 'Securing the system and locking down access.',
            vscode: 'Opening Visual Studio Code.',
            browser: 'Opening your browser.',
            dashboard: 'Displaying the dashboard.',
        };

        const sarcasticResponses = [
            'Fine, I will do it. You are the boss.',
            'Sure, because I have nothing better to do.',
            'Again? Alright, this time I mean it.',
        ];

        const getWakeResponse = () => {
            if (wakeCount === 0) return wakeResponses[0];
            if (wakeCount === 1) return wakeResponses[1];
            return sarcasticResponses[Math.min(wakeCount - 2, sarcasticResponses.length - 1)];
        };

        const responseText = command === 'wake'
            ? getWakeResponse()
            : responseMap[command] || 'Acknowledged. Processing your request.';

        const speakResponseImmediately = async (text) => {
            unlockAudio();
            const started = await speakText(text);
            if (!started) {
                setResponseMessage(text + ' — audio blocked, click "Enable Voice".');
            }
        };

        clearCommandTimers();

        // While locked, only the wake/ambient path runs; real commands are gated
        // in LockScreen too, but stay defensive here.
        if (lockedRef.current && command !== 'wake') {
            return;
        }

        if (command === 'wake') {
            setConversationMode('awaiting-command');
            setResponseMessage('');
            transitionTo('LISTENING');
            setAuthStep({ id: 'wake', label: 'WAKE', icon: '🎙️', delay: 0 });
            setWakeCount((count) => count + 1);

            if (opts.speakImmediately) {
                speakResponseImmediately(responseText);
            }

            // Very short timeout before clearing the auth step
            scheduleTimer(() => {
                setAuthStep(null);
                setResponseMessage('');
                setConversationMode('idle');
                transitionTo('LISTENING');
            }, 800);
            return;
        }

        transitionTo('LISTENING');
        setAuthStep(AUTH_STEPS[0]);
        setResponseMessage('');
        let maxDelay = 0;

        AUTH_STEPS.forEach((step) => {
            maxDelay = Math.max(maxDelay, step.delay);
            scheduleTimer(() => {
                setAuthStep(step);
                if (step.id === 'scanning_voice') transitionTo('THINKING');
                if (step.id === 'voice_match')    transitionTo('VERIFYING');
                if (step.id === 'identity')       transitionTo('UNLOCKING');
            }, step.delay);
        });

        if (command === 'engineering') {
            scheduleTimer(() => {
                setLabel('OPENING ENGINEERING CONSOLE');
            }, 600);
        }
        if (command === 'vscode') {
            scheduleTimer(() => {
                setLabel('OPENING VISUAL STUDIO CODE');
            }, 600);
        }
        if (command === 'browser') {
            scheduleTimer(() => {
                setLabel('OPENING BROWSER');
            }, 600);
        }
        if (command === 'dashboard') {
            scheduleTimer(() => {
                setLabel('DISPLAYING DASHBOARD');
            }, 600);
        }

        scheduleTimer(() => {
            setAuthStep(null);
            setResponseMessage('');
            transitionTo('IDLE');
            setConversationMode('idle');
            // Route to the requested workspace view once the auth animation ends.
            if (command === 'trading') setWorkspace('trading');
            else if (command === 'dashboard') setWorkspace('dashboard');
            else setWorkspace('unlocked');
        }, maxDelay + 600);
    }, [transitionTo, speakText, audioEnabled, setWorkspace]);

    // ── Micro level + breathing loop ─────────────────────────────────────────
    useEffect(() => {
        let raf;
        const animate = () => {
            const t = Date.now() * 0.001;
            
            // Read actual mic input from hook, fall back to subtle sine wave if zero/denied
            const micLevel = audioLevelRef.current;
            const fallbackMic = 0.06 + 0.04 * Math.sin(t * 2.5);
            uniforms.current.audioLevel = micLevel > 0.01 ? micLevel : fallbackMic;

            // Breathing scale: 1.0 → 1.03 → 1.0 over ~3s
            uniforms.current.breathScale = 1.0 + 0.03 * Math.sin(t * 2.1);
            uniforms.current.isHovered = isHovered;

            raf = requestAnimationFrame(animate);
        };
        animate();
        return () => cancelAnimationFrame(raf);
    }, [isHovered, audioLevelRef]);

    useEffect(() => {
        if (!startMic || !stopMic) return;
        if (appState === 'LISTENING' && micEnabled) {
            // attempt to unlock audio before starting mic to satisfy autoplay policies
            unlockAudio();
            startMic().catch(() => {});
        } else {
            stopMic();
        }
    }, [appState, micEnabled, startMic, stopMic]);

    // ── Boot sequence ────────────────────────────────────────────────────────
    useEffect(() => {
        const t = setTimeout(() => transitionTo('IDLE'), 2200);
        return () => clearTimeout(t);
    }, [transitionTo]);

    // Expose a small debug helper to trigger auth sequences from the console
    useEffect(() => {
        if (typeof window === 'undefined') return;
        window.fridayRunCommand = (cmd, opts) => runAuthSequence(cmd, opts || {});
        return () => {
            try {
                if (window.fridayRunCommand) delete window.fridayRunCommand;
            } catch (e) {}
        };
    }, [runAuthSequence]);

    return (
        <OrbContext.Provider value={{
            appState, stateLabel, responseMessage, authStep, workspace, setWorkspace,
            conversationMode, setConversationMode,
            locked, mode, setMode, adminAuthed,
            unlockWithFingerprintFlow, authenticateWithPassword, lockNow,
            uniforms, isHovered, setIsHovered,
            waveformRef, audioLevelRef, start: startMic, stop: stopMic,
            transitionTo, runAuthSequence, speakText, setResponseMessage,
            // voices
            voices, voiceName, setVoiceName,
            // tts
            ttsLoading, isSpeaking: queueIsPlaying,
            // audio enable
            audioEnabled, enableAudioFromGesture,
        }}>
            {children}
        </OrbContext.Provider>
    );
}

export const useOrbState = () => useContext(OrbContext);
