"use client";

import { useEffect, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Browser recordings are webm/opus; re-encode to WAV so the backend can read it.
async function blobToWav(blob) {
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const buf = await ctx.decodeAudioData(await blob.arrayBuffer());
  ctx.close();
  const ch = buf.getChannelData(0);
  const sr = buf.sampleRate;
  const out = new DataView(new ArrayBuffer(44 + ch.length * 2));
  const wr = (o, s) => { for (let i = 0; i < s.length; i++) out.setUint8(o + i, s.charCodeAt(i)); };
  wr(0, "RIFF"); out.setUint32(4, 36 + ch.length * 2, true); wr(8, "WAVE"); wr(12, "fmt ");
  out.setUint32(16, 16, true); out.setUint16(20, 1, true); out.setUint16(22, 1, true);
  out.setUint32(24, sr, true); out.setUint32(28, sr * 2, true); out.setUint16(32, 2, true);
  out.setUint16(34, 16, true); wr(36, "data"); out.setUint32(40, ch.length * 2, true);
  for (let i = 0; i < ch.length; i++) {
    const s = Math.max(-1, Math.min(1, ch[i]));
    out.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([out], { type: "audio/wav" });
}

const EXAMPLES = [
  { label: "Hindi scam", text: "Sir main bank se bol raha hoon, turant OTP batao aur paise transfer karo, urgent hai" },
  { label: "English scam", text: "This is urgent — share your OTP and transfer the money to this account right now." },
  { label: "Normal call", text: "Hey, are we still meeting for lunch tomorrow afternoon?" },
];

// Real scam patterns pulled from app/intent/patterns.py, one per triggered category
const PATTERN_CARDS = [
  {
    tone: "blue",
    title: "OTP + money request",
    desc: "The single most reliable fraud signal — a genuine bank, relative, or officer never needs both your OTP and a transfer in the same call.",
    tags: ["otp_request", "money_request", "urgency"],
    sample: "Sir main bank se bol raha hoon, turant OTP batao aur paise transfer karo, urgent hai",
    note: "Always force-escalated to HIGH/CRITICAL, regardless of how real the voice sounds.",
  },
  {
    tone: "orange",
    title: "Authority impersonation",
    desc: "Callers claiming to be a bank manager, police, or CBI officer, paired with manufactured urgency to stop you from thinking it through.",
    tags: ["authority_claim", "urgency"],
    sample: "Bank se baat kar raha hoon, abhi turant apna account verify kijiye warna block ho jayega",
    note: "Matched in Hindi, English, and 6 more Indian languages.",
  },
  {
    tone: "green",
    title: "Family emergency + secrecy",
    desc: "A cloned voice of a relative, asking for quiet, urgent help — engineered so you don't stop to verify with anyone else first.",
    tags: ["secrecy", "money_request", "urgency"],
    sample: "Beta, please kisi ko mat batana, mujhe abhi paise ki zaroorat hai, main museebat mein hoon",
    note: "Secrecy requests are treated as a red flag on their own.",
  },
];

const CHECK_CARDS = [
  {
    title: "Voice authenticity",
    desc: "An acoustic model listens for AI-synthesis artifacts second-by-second across the call.",
    icon: (
      <path d="M9 18V5l12-2v13M9 13l12-2M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM18 19a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
    ),
  },
  {
    title: "Speaker identity",
    desc: "192-dimensional voice embeddings confirm whether the caller matches the person they claim to be.",
    icon: <path d="M17.5 21a5.5 5.5 0 1 0-11 0M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z" />,
  },
  {
    title: "Scam intent",
    desc: "A multilingual pattern engine catches OTP, money & urgency requests across 7 Indian languages.",
    icon: <path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.4 8.6 8.6 0 0 1-4-1L3 20l1.1-4.5A8.4 8.4 0 0 1 12.5 3a8.38 8.38 0 0 1 8.5 8.5Z" />,
  },
  {
    title: "Explainable fusion",
    desc: "All three signals combine into one weighted, plain-language verdict — reasons included, never a black box.",
    icon: <path d="M12 2 3 7l9 5 9-5-9-5ZM3 12l9 5 9-5M3 17l9 5 9-5" />,
  },
];

const FAQS = [
  {
    q: "Is this actually detecting AI voices right now, or a demo?",
    a: "By default the backend runs DETECTOR_ENGINE=mock, a deterministic placeholder that hashes the file instead of listening to it — built so the rest of the app works before a real model is wired in. Set DETECTOR_ENGINE=wav2vec2 in backend/.env for genuine acoustic analysis.",
  },
  {
    q: "Is my voice, or the person I register, stored anywhere?",
    a: "Registered voiceprints are stored as 192 numbers (an embedding) only — never raw audio — locally in .voiceprints.json, and optionally mirrored to Supabase if you've configured it.",
  },
  {
    q: "Why does asking for an OTP and money together always get escalated?",
    a: "It's a hard-coded override in the risk engine: a good voice clone can fool the acoustic check, but the request itself can't be faked. That combination forces at least a HIGH verdict no matter what the weighted score says.",
  },
  {
    q: "Which languages does the scam-intent check understand?",
    a: "Hindi, Tamil, Telugu, Kannada, Bengali, Marathi, Urdu, English, and Hinglish code-mixing — matched with a plain regex engine, no ML required.",
  },
];

const TIERS = {
  low:      { label: "LOW",      color: "#059669", soft: "#ecfdf5", border: "#bfe9d4", action: "Allow the call" },
  medium:   { label: "MEDIUM",   color: "#b45309", soft: "#fffbeb", border: "#f3dda8", action: "Warn the user" },
  high:     { label: "HIGH",     color: "#c2410c", soft: "#fff7ed", border: "#fed7aa", action: "Verify the caller" },
  critical: { label: "CRITICAL", color: "#dc2626", soft: "#fef2f2", border: "#f6c9c9", action: "Block + step-up verify" },
};

function EngineBadge({ engine }) {
  const online = engine && engine !== "offline";
  const real = engine === "wav2vec2";
  const label = engine === null ? "connecting" : engine === "offline" ? "offline" : real ? "live model" : "demo engine";
  return (
    <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium"
      style={{ borderColor: "var(--border)", color: online ? "var(--muted)" : "var(--faint)" }}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: online ? (real ? "var(--safe)" : "var(--warn)") : "var(--faint)" }} />
      {label}
    </span>
  );
}

function Equalizer() {
  const delays = [0, 0.15, 0.3, 0.1, 0.25, 0.05, 0.2];
  return (
    <div className="flex h-7 items-end justify-center gap-1">
      {delays.map((d, i) => (
        <span key={i} className="eq-bar w-1 rounded-full" style={{ height: "100%", background: "var(--text)", animationDelay: `${d}s` }} />
      ))}
    </div>
  );
}

function Gauge({ value, color, caption }) {
  const r = 54, circ = 2 * Math.PI * r;
  return (
    <div className="relative h-32 w-32 shrink-0">
      <svg viewBox="0 0 120 120" className="h-32 w-32 -rotate-90">
        <circle cx="60" cy="60" r={r} fill="none" strokeWidth="8" stroke="var(--border)" />
        <circle cx="60" cy="60" r={r} fill="none" strokeWidth="8" stroke={color} strokeLinecap="round"
          strokeDasharray={circ} strokeDashoffset={circ * (1 - value)}
          style={{ transition: "stroke-dashoffset 0.9s cubic-bezier(0.22,1,0.36,1)" }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[28px] font-semibold tracking-tight" style={{ color }}>{Math.round(value * 100)}%</span>
        <span className="text-[10px] uppercase tracking-widest" style={{ color: "var(--faint)" }}>{caption}</span>
      </div>
    </div>
  );
}

// Voice timeline (per-second AI/human/quiet)
function Timeline({ segments }) {
  const span = segments[segments.length - 1].end - segments[0].start || 1;
  return (
    <div className="mt-3">
      <div className="flex h-8 w-full gap-[2px] overflow-hidden rounded-md">
        {segments.map((s, i) => {
          const wpct = ((s.end - s.start) / span) * 100;
          const quiet = s.speech === false;
          const p = s.synthetic_probability ?? 0;
          const bg = quiet ? "#e5e7eb" : s.is_synthetic ? "var(--danger)" : "var(--safe)";
          const intensity = quiet ? 1 : 0.45 + 0.55 * (s.is_synthetic ? p : 1 - p);
          return <div key={i} title={quiet ? `${s.start}s–${s.end}s · quiet` : `${s.start}s–${s.end}s · ${Math.round(p * 100)}% AI`}
            style={{ width: `${wpct}%`, background: bg, opacity: intensity }} />;
        })}
      </div>
      <div className="mt-2 flex gap-4 text-[11px]" style={{ color: "var(--muted)" }}>
        {[["var(--safe)", "human"], ["var(--danger)", "AI"], ["#e5e7eb", "quiet"]].map(([c, t]) => (
          <span key={t} className="flex items-center gap-1.5"><span className="h-2 w-2.5 rounded-sm" style={{ background: c }} />{t}</span>
        ))}
      </div>
    </div>
  );
}

// Highlight matched scam phrases inside the transcript
function Highlighted({ text, matches }) {
  const phrases = [...new Set(Object.values(matches || {}))].filter(Boolean);
  if (!text) return null;
  if (!phrases.length) return <>{text}</>;
  const escaped = phrases.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const parts = text.split(new RegExp(`(${escaped.join("|")})`, "gi"));
  const lower = new Set(phrases.map((p) => p.toLowerCase()));
  return parts.map((part, i) =>
    lower.has(part.toLowerCase())
      ? <mark key={i} style={{ background: "#fee2e2", color: "#b91c1c", borderRadius: 4, padding: "0 3px" }}>{part}</mark>
      : <span key={i}>{part}</span>
  );
}

export default function Home() {
  const [engine, setEngine] = useState(null);
  const [audioFile, setAudioFile] = useState(null);
  const [audioName, setAudioName] = useState("");
  const [audioURL, setAudioURL] = useState(null);
  const [transcript, setTranscript] = useState("");
  const [recording, setRecording] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [knownVoices, setKnownVoices] = useState([]);
  const [claimedIdentity, setClaimedIdentity] = useState("");
  const [regName, setRegName] = useState("");
  const [regFile, setRegFile] = useState(null);
  const [regBusy, setRegBusy] = useState(false);
  const [showVoices, setShowVoices] = useState(false);
  const recorderRef = useRef(null);

  const fetchVoices = () =>
    fetch(`${API_URL}/api/voices`).then((r) => r.json()).then((d) => setKnownVoices(d.voices || [])).catch(() => {});

  useEffect(() => {
    fetch(`${API_URL}/health`).then((r) => r.json()).then((d) => setEngine(d.engine)).catch(() => setEngine("offline"));
    fetchVoices();
  }, []);

  async function registerVoice() {
    if (!regName.trim() || !regFile) return;
    setRegBusy(true); setError(null);
    try {
      const form = new FormData();
      form.append("name", regName.trim());
      form.append("audio", regFile);
      const res = await fetch(`${API_URL}/api/voices/register`, { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "register failed");
      setRegName(""); setRegFile(null); fetchVoices();
    } catch (e) {
      setError(String(e.message).toLowerCase().includes("speechbrain")
        ? "Identity check needs SpeechBrain (installing / not ready yet)."
        : e.message);
    } finally { setRegBusy(false); }
  }

  async function deleteVoice(name) {
    await fetch(`${API_URL}/api/voices/${encodeURIComponent(name)}`, { method: "DELETE" }).catch(() => {});
    if (claimedIdentity === name) setClaimedIdentity("");
    fetchVoices();
  }

  function pickFile(f) {
    if (!f) return;
    setAudioFile(f); setAudioName(f.name); setAudioURL(URL.createObjectURL(f)); setResult(null); setError(null);
  }

  async function toggleRecord() {
    if (recording) { recorderRef.current?.stop(); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream); const chunks = [];
      mr.ondataavailable = (e) => chunks.push(e.data);
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop()); setRecording(false);
        try {
          const wav = await blobToWav(new Blob(chunks, { type: "audio/webm" }));
          setAudioFile(new File([wav], "live-recording.wav", { type: "audio/wav" }));
          setAudioName("Live recording"); setAudioURL(URL.createObjectURL(wav)); setResult(null);
        } catch { setError("Could not process the recording. Try uploading a file instead."); }
      };
      recorderRef.current = mr; mr.start(); setRecording(true); setError(null);
    } catch { setError("Microphone access was denied by your browser."); }
  }

  async function analyze() {
    if (!audioFile && !transcript.trim()) return;
    setLoading(true); setError(null); setResult(null);
    try {
      const form = new FormData();
      if (audioFile) form.append("audio", audioFile);
      if (transcript.trim()) form.append("transcript", transcript.trim());
      if (claimedIdentity) form.append("claimed_identity", claimedIdentity);
      const res = await fetch(`${API_URL}/api/analyze/full`, { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setResult(data);
    } catch (e) {
      setError(e.message === "Failed to fetch"
        ? "Can't reach the backend. Start it: cd backend && uvicorn app.main:app --reload"
        : e.message);
    } finally { setLoading(false); }
  }

  function scrollToTool() {
    document.getElementById("analyze")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function tryPattern(sample) {
    setTranscript(sample); setAudioFile(null); setAudioName(""); setAudioURL(null); setResult(null); setError(null);
    scrollToTool();
  }

  function downloadJSON() {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${result?.case_id || "voiceguard"}.json`;
    a.click(); URL.revokeObjectURL(a.href);
  }

  async function downloadPDF() {
    const form = new FormData();
    if (audioFile) form.append("audio", audioFile);
    if (transcript.trim()) form.append("transcript", transcript.trim());
    const res = await fetch(`${API_URL}/api/report/pdf`, { method: "POST", body: form });
    if (!res.ok) { setError("PDF report failed."); return; }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${result?.case_id || "voiceguard"}.pdf`;
    a.click(); URL.revokeObjectURL(a.href);
  }

  const risk = result?.risk;
  const tier = risk ? TIERS[risk.tier] : null;
  const voice = result?.voice;
  const voiceSeg = voice?.segments && voice.segments.length > 1 ? voice.segments : null;
  const voiceAI = voice ? (voice.synthetic_fraction ?? voice.synthetic_probability ?? 0) : 0;
  const intent = result?.intent;
  const intentShown = intent && intent.transcript && intent.transcript.trim();
  const canAnalyze = !!audioFile || !!transcript.trim();

  return (
    <main className="flex-1">
      {/* Header */}
      <header className="sticky top-0 z-20 border-b backdrop-blur" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.85)" }}>
        <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between px-6">
          <div className="flex items-center gap-2.5">
            <div className="grid h-8 w-8 place-items-center rounded-lg text-white" style={{ background: "var(--accent)" }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" /><path d="M5 10v1a7 7 0 0 0 14 0v-1M12 19v3" />
              </svg>
            </div>
            <span className="text-[15px] font-semibold tracking-tight">VoiceGuard AI</span>
          </div>
          <nav className="hidden items-center gap-6 text-sm sm:flex" style={{ color: "var(--muted)" }}>
            <a href="#checks" className="hover:text-[var(--text)]">How it works</a>
            <a href="#patterns" className="hover:text-[var(--text)]">Scam patterns</a>
            <a href="#faq" className="hover:text-[var(--text)]">FAQ</a>
          </nav>
          <div className="flex items-center gap-3">
            <EngineBadge engine={engine} />
            <button onClick={scrollToTool}
              className="hidden rounded-full px-4 py-1.5 text-sm font-medium text-white sm:inline-flex"
              style={{ background: "var(--accent)" }}>
              Analyse a call
            </button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto w-full max-w-3xl px-6 pb-10 pt-16 text-center sm:pt-24">
        <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium" style={{ borderColor: "var(--border-strong)", color: "var(--muted)" }}>
          SIH26104 · India-first · explainable AI
        </span>
        <h1 className="mt-5 text-[32px] font-semibold leading-[1.12] tracking-tight sm:text-[52px]">
          Catch voice-cloning
          <br />scam calls before money moves
        </h1>
        <p className="mx-auto mt-5 max-w-lg text-[15px] leading-relaxed sm:text-base" style={{ color: "var(--muted)" }}>
          Add a call recording and/or what the caller said. We check whether the voice is
          AI-cloned and whether the words are a scam — then give one clear risk verdict.
        </p>
        <div className="mt-7 flex items-center justify-center gap-3">
          <button onClick={scrollToTool}
            className="inline-flex min-h-[46px] items-center rounded-full px-6 text-[15px] font-medium text-white"
            style={{ background: "var(--accent)" }}>
            Analyse a call
          </button>
          <a href="#checks" className="inline-flex min-h-[46px] items-center rounded-full border px-6 text-[15px] font-medium" style={{ borderColor: "var(--border-strong)" }}>
            See how it works
          </a>
        </div>

        {/* Decorative hero panel */}
        <div className="relative mt-12 overflow-hidden rounded-3xl" style={{ background: "var(--hero-grad)" }}>
          <div className="flex flex-col items-center justify-center gap-6 px-6 py-16 sm:py-24">
            <p className="max-w-md text-xl font-medium leading-snug text-white/90 sm:text-2xl">
              &ldquo;Fraud shouldn&apos;t sound this convincing.&rdquo;
            </p>
            <div className="flex h-16 items-end justify-center gap-1.5">
              {[0, 0.15, 0.3, 0.1, 0.25, 0.05, 0.2, 0.12, 0.28, 0.08].map((d, i) => (
                <span key={i} className="eq-bar w-1.5 rounded-full bg-white/70" style={{ height: "100%", animationDelay: `${d}s` }} />
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Three checks, one verdict */}
      <section id="checks" className="mx-auto w-full max-w-5xl scroll-mt-20 px-6 py-16 text-center">
        <h2 className="text-[26px] font-semibold tracking-tight sm:text-[32px]">Three checks, one verdict</h2>
        <p className="mx-auto mt-3 max-w-lg text-[15px]" style={{ color: "var(--muted)" }}>
          Instead of trusting one acoustic classifier, VoiceGuard inspects voice, identity,
          and intent together — then explains exactly why.
        </p>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {CHECK_CARDS.map((c) => (
            <div key={c.title} className="rounded-2xl border p-5 text-left" style={{ borderColor: "var(--border)" }}>
              <div className="grid h-10 w-10 place-items-center rounded-full" style={{ background: "var(--bg-subtle)" }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  {c.icon}
                </svg>
              </div>
              <p className="mt-3 text-sm font-semibold">{c.title}</p>
              <p className="mt-1.5 text-[13px] leading-relaxed" style={{ color: "var(--muted)" }}>{c.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Try it yourself — the actual analyzer tool, unchanged */}
      <div id="analyze" className="mx-auto w-full max-w-2xl scroll-mt-16 px-6 py-4 sm:py-8">
      <section className="mb-9 text-center">
        <h2 className="text-[26px] font-semibold tracking-tight sm:text-[32px]">Try it yourself</h2>
        <p className="mx-auto mt-3 max-w-lg text-[15px]" style={{ color: "var(--muted)" }}>
          Upload a clip, record live, or just paste the transcript — no signup needed.
        </p>
      </section>

      {/* Input */}
      <section className="rounded-3xl border p-3" style={{ borderColor: "var(--border)", boxShadow: "0 1px 2px rgba(0,0,0,0.04)" }}>
        {/* Audio */}
        <label
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); pickFile(e.dataTransfer.files?.[0]); }}
          className="flex cursor-pointer flex-col items-center rounded-2xl border-2 border-dashed px-6 py-9 text-center transition-colors"
          style={{ borderColor: dragOver ? "var(--accent)" : "var(--border-strong)", background: dragOver ? "var(--bg-subtle)" : "transparent" }}>
          <input type="file" accept="audio/*,.mp3,.wav,.m4a,.aac,.ogg,.opus,.mpeg,.mpga,.mp4,.amr,.webm,.flac,.3gp"
            className="hidden" onChange={(e) => pickFile(e.target.files?.[0])} />
          <div className="mb-3 grid h-11 w-11 place-items-center rounded-full" style={{ background: "var(--bg-subtle)" }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 16V4M6 10l6-6 6 6M4 20h16" />
            </svg>
          </div>
          {audioName ? (
            <>
              <p className="text-sm font-medium">{audioName}</p>
              {audioURL && <audio controls src={audioURL} className="mt-3 w-full max-w-sm" />}
              <span className="mt-2 text-xs underline underline-offset-2" style={{ color: "var(--faint)" }}
                onClick={(e) => { e.preventDefault(); setAudioFile(null); setAudioName(""); setAudioURL(null); setResult(null); }}>
                remove clip
              </span>
            </>
          ) : (
            <>
              <p className="text-sm font-medium">Drop a call recording, or click to upload</p>
              <p className="mt-1 text-xs" style={{ color: "var(--faint)" }}>WAV, MP3, M4A, Opus, WhatsApp voice notes…</p>
            </>
          )}
        </label>

        <div className="flex items-center justify-center py-2.5">
          <button onClick={toggleRecord}
            className="inline-flex min-h-[38px] items-center gap-2 rounded-full border px-4 text-sm font-medium transition-colors"
            style={{ borderColor: recording ? "var(--danger)" : "var(--border-strong)", color: recording ? "var(--danger)" : "var(--text)" }}>
            <span className="h-2 w-2 rounded-full" style={{ background: recording ? "var(--danger)" : "var(--muted)" }} />
            {recording ? "Stop recording" : "Record live"}
          </button>
        </div>

        {/* Transcript */}
        <div className="px-2 pb-1">
          <label className="text-sm font-medium">What did the caller say? <span className="font-normal" style={{ color: "var(--faint)" }}>(optional — Hindi & code-mixed work)</span></label>
          <textarea value={transcript} onChange={(e) => setTranscript(e.target.value)} rows={2}
            placeholder="e.g. Sir turant OTP batao aur paise transfer karo…"
            className="mt-2 w-full resize-y rounded-xl border p-3 text-sm outline-none"
            style={{ borderColor: "var(--border-strong)", background: "transparent" }} />
          <div className="mt-2 flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button key={ex.label} onClick={() => setTranscript(ex.text)}
                className="rounded-full border px-3 py-1 text-xs transition-colors"
                style={{ borderColor: "var(--border)", color: "var(--muted)" }}>{ex.label}</button>
            ))}
          </div>
        </div>

        {/* Identity (P5) */}
        <div className="mt-3 px-2">
          {knownVoices.length > 0 && (
            <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
              <span style={{ color: "var(--muted)" }}>Caller claims to be:</span>
              <select value={claimedIdentity} onChange={(e) => setClaimedIdentity(e.target.value)}
                className="rounded-lg border px-2 py-1 text-sm" style={{ borderColor: "var(--border-strong)", background: "transparent" }}>
                <option value="">— unknown —</option>
                {knownVoices.map((v) => <option key={v} value={v}>{v}</option>)}
              </select>
              <span className="text-xs" style={{ color: "var(--faint)" }}>(needs a clip to verify against)</span>
            </div>
          )}
          <button type="button" onClick={() => setShowVoices((s) => !s)} className="text-xs underline underline-offset-2" style={{ color: "var(--faint)" }}>
            {showVoices ? "hide" : "manage"} known voices ({knownVoices.length})
          </button>
          {showVoices && (
            <div className="mt-2 rounded-xl border p-3" style={{ borderColor: "var(--border)" }}>
              <p className="text-xs" style={{ color: "var(--muted)" }}>
                Register the <b>real</b> person's voice (clean 5–10s clip). Stored as numbers only, never audio.
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <input value={regName} onChange={(e) => setRegName(e.target.value)} placeholder="name, e.g. Papa"
                  className="rounded-lg border px-2 py-1.5 text-sm" style={{ borderColor: "var(--border-strong)", background: "transparent" }} />
                <label className="cursor-pointer rounded-lg border px-2 py-1.5 text-sm" style={{ borderColor: "var(--border-strong)" }}>
                  {regFile ? regFile.name.slice(0, 18) : "choose clip"}
                  <input type="file" accept="audio/*,.mp3,.wav,.m4a,.aac,.ogg,.opus,.mp4,.webm,.flac"
                    className="hidden" onChange={(e) => setRegFile(e.target.files?.[0] || null)} />
                </label>
                <button onClick={registerVoice} disabled={regBusy || !regName.trim() || !regFile}
                  className="rounded-lg px-3 py-1.5 text-sm font-medium text-white disabled:opacity-30" style={{ background: "var(--accent)" }}>
                  {regBusy ? "…" : "Register"}
                </button>
              </div>
              {knownVoices.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {knownVoices.map((v) => (
                    <span key={v} className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs" style={{ borderColor: "var(--border)" }}>
                      {v}<button onClick={() => deleteVoice(v)} style={{ color: "var(--faint)" }}>✕</button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <button onClick={analyze} disabled={loading || !canAnalyze}
          className="mt-3 flex min-h-[52px] w-full items-center justify-center rounded-full px-4 text-[15px] font-medium text-white transition-opacity disabled:opacity-30"
          style={{ background: "var(--accent)" }}>
          {loading ? "Analysing…" : "Analyse call"}
        </button>
      </section>

      {error && (
        <p className="mt-5 rounded-2xl border p-4 text-sm" style={{ borderColor: "#f6c9c9", background: "var(--danger-soft)", color: "var(--danger)" }}>{error}</p>
      )}

      {loading && (
        <div className="mt-6 rounded-3xl border p-10 text-center" style={{ borderColor: "var(--border)" }}>
          <Equalizer /><p className="mt-4 text-sm" style={{ color: "var(--muted)" }}>Analysing the call…</p>
        </div>
      )}

      {result && risk && !loading && (
        <section className="rise mt-6 space-y-4">
          {/* Unified risk verdict + prevention action */}
          <div className="flex flex-col items-center gap-6 rounded-3xl border p-8 text-center sm:flex-row sm:text-left"
            style={{ borderColor: tier.border, background: tier.soft }}>
            <Gauge value={risk.overall_risk} color={tier.color} caption="risk" />
            <div className="flex-1">
              <p className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>Risk verdict</p>
              <p className="mt-1 text-3xl font-semibold tracking-tight sm:text-[34px]" style={{ color: tier.color }}>{tier.label}</p>
              {/* Prevention action (P3) */}
              <div className="mt-3 inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium text-white" style={{ background: tier.color }}>
                Action: {tier.action}
              </div>
              <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--muted)" }}>{risk.response}</p>
              {result.case_id && <p className="mt-3 font-mono text-[11px]" style={{ color: "var(--faint)" }}>Case {result.case_id}</p>}
            </div>
          </div>

          {/* Why — evidence */}
          <div className="rounded-2xl border p-5" style={{ borderColor: "var(--border)" }}>
            <p className="mb-2 text-sm font-medium">Why — evidence</p>
            <ul className="space-y-1 text-sm" style={{ color: "var(--muted)" }}>
              {risk.reasons.map((r, i) => <li key={i} className="flex gap-2"><span style={{ color: tier.color }}>•</span>{r}</li>)}
            </ul>
          </div>

          {/* Two checks */}
          <div className="grid gap-4 sm:grid-cols-2">
            {/* Voice */}
            {voice && (
              <div className="rounded-2xl border p-5" style={{ borderColor: "var(--border)" }}>
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">Voice</p>
                  <span className="text-sm font-semibold" style={{ color: voiceAI >= 0.5 ? "var(--danger)" : "var(--safe)" }}>
                    {Math.round(voiceAI * 100)}% AI
                  </span>
                </div>
                <p className="mt-0.5 text-xs" style={{ color: "var(--muted)" }}>
                  {voiceAI >= 0.6 ? "Sounds AI-cloned" : voiceAI >= 0.15 ? "Partly synthetic" : "Sounds like a real human"}
                </p>
                {voiceSeg && <Timeline segments={voice.segments} />}
              </div>
            )}
            {/* Intent */}
            {intentShown ? (
              <div className="rounded-2xl border p-5" style={{ borderColor: "var(--border)" }}>
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">Scam intent</p>
                  <span className="text-sm font-semibold" style={{ color: intent.triggered.length ? "var(--danger)" : "var(--safe)" }}>
                    {Math.round((intent.intent_risk || 0) * 100)}%
                  </span>
                </div>
                <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--text)" }}>
                  <Highlighted text={intent.transcript} matches={intent.matches} />
                </p>
                {intent.triggered.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {intent.triggered.map((t) => (
                      <span key={t} className="rounded-full px-2.5 py-1 text-xs font-medium" style={{ background: "#fee2e2", color: "#b91c1c" }}>
                        {t.replace(/_/g, " ")}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed p-5 text-sm" style={{ borderColor: "var(--border)", color: "var(--faint)" }}>
                <p className="font-medium" style={{ color: "var(--muted)" }}>Scam intent</p>
                <p className="mt-1">Paste what the caller said (Hindi/English) to check for OTP, money & urgency scam words.</p>
              </div>
            )}
          </div>

          {/* Identity (P5) */}
          {result.identity && (
            <div className="rounded-2xl border p-5" style={{ borderColor: "var(--border)" }}>
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">Identity check</p>
                {result.identity.checked ? (
                  <span className="text-sm font-semibold" style={{ color: result.identity.identity_match ? "var(--safe)" : "var(--danger)" }}>
                    {result.identity.identity_match ? "MATCH" : "NO MATCH"}
                    {typeof result.identity.similarity === "number" ? ` · ${Math.round(result.identity.similarity * 100)}%` : ""}
                  </span>
                ) : <span className="text-xs" style={{ color: "var(--faint)" }}>not checked</span>}
              </div>
              <p className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
                {result.identity.checked
                  ? (result.identity.identity_match
                      ? "Voice matches the registered person's voiceprint."
                      : "Voice does NOT match the registered person — possible impersonation.")
                  : (result.identity.note || "Pick who the caller claims to be, and include a clip, to run this check.")}
              </p>
            </div>
          )}

          {/* Forensic report */}
          <div className="flex gap-3">
            <button onClick={downloadPDF}
              className="flex-1 rounded-full border py-2.5 text-sm font-medium transition-colors"
              style={{ borderColor: "var(--border-strong)" }}>Download report (PDF)</button>
            <button onClick={downloadJSON}
              className="flex-1 rounded-full border py-2.5 text-sm font-medium transition-colors"
              style={{ borderColor: "var(--border-strong)" }}>Download JSON</button>
          </div>

          <p className="px-1 text-xs leading-relaxed" style={{ color: "var(--faint)" }}>
            Probabilistic assessment, not proof. The voice model was trained mainly on Western English,
            so it can misjudge Indian accents & real recording conditions. Use as decision support.
          </p>
        </section>
      )}
      </div>

      {/* Built for every scam pattern */}
      <section id="patterns" className="mx-auto w-full max-w-5xl scroll-mt-20 px-6 py-16 text-center">
        <h2 className="text-[26px] font-semibold tracking-tight sm:text-[32px]">Built for every scam pattern</h2>
        <p className="mx-auto mt-3 max-w-lg text-[15px]" style={{ color: "var(--muted)" }}>
          Real patterns from the intent engine — try one and see the verdict for yourself.
        </p>
        <div className="mt-10 grid gap-5 text-left sm:grid-cols-3">
          {PATTERN_CARDS.map((c) => (
            <div key={c.title} className="flex flex-col rounded-2xl border p-5"
              style={{
                background: c.tone === "blue" ? "var(--card-blue)" : c.tone === "orange" ? "var(--card-orange)" : "var(--card-green)",
                borderColor: c.tone === "blue" ? "var(--card-blue-border)" : c.tone === "orange" ? "var(--card-orange-border)" : "var(--card-green-border)",
              }}>
              <p className="text-[15px] font-semibold">{c.title}</p>
              <p className="mt-2 text-[13px] leading-relaxed" style={{ color: "var(--muted)" }}>{c.desc}</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {c.tags.map((t) => (
                  <span key={t} className="rounded-full bg-white/70 px-2 py-0.5 text-[11px] font-medium" style={{ color: "var(--text)" }}>
                    {t.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
              <p className="mt-3 text-[12px] italic leading-relaxed" style={{ color: "var(--muted)" }}>{c.note}</p>
              <button onClick={() => tryPattern(c.sample)}
                className="mt-4 inline-flex w-fit items-center gap-1.5 rounded-full bg-white px-3.5 py-1.5 text-xs font-medium shadow-sm">
                Try this example →
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="mx-auto w-full max-w-2xl scroll-mt-20 px-6 py-16">
        <h2 className="text-center text-[26px] font-semibold tracking-tight sm:text-[32px]">Frequently asked questions</h2>
        <div className="mt-8 space-y-2">
          {FAQS.map((f) => (
            <details key={f.q} className="group rounded-2xl border p-4" style={{ borderColor: "var(--border)" }}>
              <summary className="cursor-pointer list-none text-sm font-medium marker:content-none">
                <span className="flex items-center justify-between gap-3">
                  {f.q}
                  <span className="shrink-0 text-lg leading-none transition-transform group-open:rotate-45" style={{ color: "var(--faint)" }}>+</span>
                </span>
              </summary>
              <p className="mt-2 text-[13px] leading-relaxed" style={{ color: "var(--muted)" }}>{f.a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="mx-auto w-full max-w-5xl px-6 pb-16">
        <div className="flex flex-col items-center gap-5 rounded-3xl px-6 py-16 text-center" style={{ background: "var(--cta-grad)" }}>
          <h2 className="max-w-md text-2xl font-semibold leading-snug text-white sm:text-3xl">
            Don&apos;t let a cloned voice cost you.
          </h2>
          <button onClick={scrollToTool}
            className="inline-flex min-h-[46px] items-center rounded-full bg-white px-6 text-[15px] font-medium text-black">
            Analyse a call
          </button>
        </div>
      </section>

      <footer className="border-t px-6 py-10 text-center text-xs" style={{ borderColor: "var(--border)", color: "var(--faint)" }}>
        SIH26104 · VoiceGuard AI · fake-voice + scam-intent → risk · runs locally
      </footer>
    </main>
  );
}
