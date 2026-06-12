import React, { useState, useEffect, useMemo, useRef } from "react";
import { isCloudStorageEnabled, getStoredRoom, clearStoredRoom, createRoomSession, joinRoomByCode } from "./storage.js";
import {
  ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";
import {
  clamp, pick, clone, money, fmtNum, letter,
  TOTAL_WEEKS, calOf, brandEvent, migrateCalEvents, monthIdxOf, weekOfMonth, isPLEWeek,
  MARKETS, STIPS, FINISHES, PROMO_TONES, SEG_KINDS, EVENTS, REDUCE_COST,
  OBJ_TEMPLATES, THEME, BRAND_CONFIG, BRAND_KEYS,
  emptyBooking, buildInitialState, unitById, activeUnits, unitAvailable, titleHeldBy,
  marketTravel, LOCAL_TRAVEL, DEFAULT_MARKET, venueSeats, VENUE,
  pushNews, capUsed, findFeudMulti, getSides,
  simulateShow, issueObjectives, applyEventChoice, reduceStatus, advanceWeek,
  moraleLabel, faAsk, releaseUnit, signFreeAgent, clearTheAir,
  tradePayrollCheck, acceptTrade, rejectTrade,
  powerScore, brandRankings, OPPORTUNITIES, useOpportunity, applyPodcast,
  STAFF_ROLES, makeCustomUnit, startNextSeason, trainUnit, TRAIN_TIERS,
  computePillars, fmtSoc, handleOf, engagement, addPost, applyViewershipRules,
  gradePromoAI, gradePodcastAI, aiSocialTakes, hashPin,
  parsePodcastDialogue, PODCAST_HOST_VOICE, playPodcastNeural, generatePodcastEpisodeAI,
  PODCAST_TONES, PODCAST_LENGTHS, hasAnthropicKey,
} from "./game.js";

/* ---------------- podcast speech (neural TTS + browser fallback) ---------------- */
function usePodcastSpeech() {
  const [speaking, setSpeaking] = useState(false);
  const [status, setStatus] = useState("");
  const [voiceMode, setVoiceMode] = useState("edge");
  const abortRef = useRef(null);
  const idxRef = useRef(0);
  const segsRef = useRef([]);
  const cancelRef = useRef(false);

  useEffect(() => () => {
    abortRef.current?.abort();
    if (typeof window !== "undefined" && window.speechSynthesis) window.speechSynthesis.cancel();
  }, []);

  const pickVoice = (speaker) => {
    const voices = window.speechSynthesis.getVoices().filter((v) => v.lang.startsWith("en"));
    const hint = PODCAST_HOST_VOICE[speaker];
    if (hint?.voiceRe) {
      const match = voices.find((v) => hint.voiceRe.test(v.name));
      if (match) return match;
    }
    let h = 0;
    for (const ch of speaker) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    return voices[h % Math.max(1, voices.length)] || null;
  };

  const speakBrowserNext = () => {
    if (cancelRef.current || idxRef.current >= segsRef.current.length) {
      setSpeaking(false);
      setStatus(cancelRef.current ? "" : "Done (basic browser voice)");
      idxRef.current = 0;
      return;
    }
    const { speaker, text } = segsRef.current[idxRef.current];
    const u = new SpeechSynthesisUtterance(text);
    const hint = PODCAST_HOST_VOICE[speaker] || {};
    u.rate = hint.rate ?? 0.95;
    u.pitch = hint.pitch ?? 1;
    const voice = pickVoice(speaker);
    if (voice) u.voice = voice;
    u.onend = () => { idxRef.current += 1; setTimeout(speakBrowserNext, 400); };
    u.onerror = () => { idxRef.current += 1; setTimeout(speakBrowserNext, 200); };
    setStatus(`Speaking (basic): ${speaker}`);
    setVoiceMode("browser");
    window.speechSynthesis.speak(u);
  };

  const speakBrowser = (script, hosts) => {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      setStatus("Browser speech not supported.");
      return;
    }
    window.speechSynthesis.getVoices();
    cancelRef.current = false;
    const segs = parsePodcastDialogue(script, hosts);
    if (!segs.length) {
      setStatus('Use lines like Maya Cruz: "Welcome back to NXT Unfiltered…"');
      return;
    }
    segsRef.current = segs;
    idxRef.current = 0;
    setSpeaking(true);
    speakBrowserNext();
  };

  const stop = () => {
    cancelRef.current = true;
    abortRef.current?.abort();
    abortRef.current = null;
    if (typeof window !== "undefined" && window.speechSynthesis) window.speechSynthesis.cancel();
    setSpeaking(false);
    setStatus("");
    idxRef.current = 0;
  };

  const speak = async (script, hosts) => {
    if (!(script || "").trim()) return;
    stop();
    cancelRef.current = false;
    setSpeaking(true);
    setVoiceMode("edge");
    setStatus("Loading neural voices…");
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const mode = await playPodcastNeural(script, hosts, setStatus, controller.signal);
      setVoiceMode(mode);
      setStatus(`Done — ${mode === "openai" ? "OpenAI HD" : "neural Edge"} voice`);
      setSpeaking(false);
    } catch (e) {
      if (e?.name === "AbortError") { setSpeaking(false); setStatus(""); return; }
      setStatus("Neural voice unavailable — falling back to basic browser voice.");
      speakBrowser(script, hosts);
    } finally {
      abortRef.current = null;
    }
  };

  return { speak, stop, speaking, status, voiceMode };
}

/* ---------------- avatar ---------------- */
function Ava({ src, name, size = 36, ring }) {
  const initials = (name || "?").split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  const border = ring ? "2px solid " + ring : "1px solid rgba(255,255,255,0.1)";
  if (src) return <img src={src} alt={name} className="rounded-full object-cover flex-shrink-0" style={{ width: size, height: size, border }} />;
  return (
    <div className="rounded-full flex items-center justify-center font-semibold flex-shrink-0 bfg-display"
      style={{ width: size, height: size, background: "rgba(255,255,255,0.06)", color: "#a1a1aa", fontSize: Math.max(9, size * 0.34), border }}>
      {initials}
    </div>
  );
}

function fileToThumb(file, max = 256) {
  return new Promise((res, rej) => {
    const fr = new FileReader();
    fr.onload = () => {
      const img = new Image();
      img.onload = () => {
        const sc = Math.min(1, max / Math.max(img.width, img.height));
        const c = document.createElement("canvas");
        c.width = Math.max(1, Math.round(img.width * sc));
        c.height = Math.max(1, Math.round(img.height * sc));
        c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
        res(c.toDataURL("image/jpeg", 0.72));
      };
      img.onerror = rej;
      img.src = fr.result;
    };
    fr.onerror = rej;
    fr.readAsDataURL(file);
  });
}

/* ================================================================
   UI ATOMS
   ================================================================ */
const display = { fontFamily: "Inter, system-ui, sans-serif", fontWeight: 800, letterSpacing: "-0.02em" };
const labelStyle = { color: "#a1a1aa", fontSize: "0.75rem", fontWeight: 500 };

function Pill({ children, color = "#444", text = "#fff", style = {} }) {
  return (
    <span className="bfg-pill" style={{ background: color, color: text, ...style }}>
      {children}
    </span>
  );
}
const AlPill = ({ al }) => (
  <Pill color={al === "F" ? "#1f6feb" : al === "H" ? "#b91c1c" : "#6b7280"}>{al === "F" ? "FACE" : al === "H" ? "HEEL" : "TWEENER"}</Pill>
);

const DEFAULT_AL_FILTER = { F: true, H: true, N: true };

function filterUnitsByAl(units, alFilter) {
  return units.filter((u) => alFilter[u.al]);
}

function AlFilterToggles({ filter, onChange, compact }) {
  const opts = [
    { k: "F", label: "Face", color: "#3b82f6" },
    { k: "H", label: "Heel", color: "#ef4444" },
    { k: "N", label: "Tweener", color: "#a855f7" },
  ];
  return (
    <div className={"flex gap-1.5 flex-wrap " + (compact ? "" : "mb-1")}>
      {opts.map(({ k, label, color }) => (
        <button key={k} type="button" onClick={() => onChange({ ...filter, [k]: !filter[k] })}
          className={"rounded-full font-medium transition-all " + (compact ? "text-xs px-2.5 py-1" : "text-xs px-3 py-1.5")}
          style={{
            background: filter[k] ? color + "22" : "rgba(255,255,255,0.04)",
            color: filter[k] ? "#fff" : "#71717a",
            border: `1px solid ${filter[k] ? color + "55" : "rgba(255,255,255,0.08)"}`,
          }}>
          {label}
        </button>
      ))}
    </div>
  );
}

function Bar({ pct, color, h = 6 }) {
  return (
    <div className="bfg-bar-track" style={{ height: h }}>
      <div className="bfg-bar-fill" style={{ width: clamp(pct, 0, 100) + "%", background: color }} />
    </div>
  );
}

function GradeBadge({ score, size = "lg" }) {
  const g = letter(score);
  const col = score >= 80 ? "#22c55e" : score >= 65 ? "#d4af37" : score >= 50 ? "#f59e0b" : "#ef4444";
  return (
    <span className={size === "lg" ? "text-2xl bfg-display" : "text-base bfg-display"} style={{ color: col }}>{g}</span>
  );
}

function Btn({ children, onClick, kind = "primary", theme, disabled, small }) {
  const base = small ? "px-3.5 py-1.5 text-xs" : "px-4 py-2.5 text-sm";
  const styles = kind === "primary"
    ? {
      background: theme ? `linear-gradient(180deg, ${theme.primary}, ${theme.primary}dd)` : "linear-gradient(180deg, #d4af37, #b8941f)",
      color: "#0a0a0c",
      boxShadow: theme ? `0 4px 20px ${theme.glow}44` : "0 4px 16px rgba(212,175,55,0.25)",
      border: "1px solid rgba(255,255,255,0.12)",
    }
    : kind === "danger"
      ? { background: "rgba(127,29,29,0.85)", color: "#fecaca", border: "1px solid rgba(239,68,68,0.35)" }
      : { background: "rgba(255,255,255,0.06)", color: "#e4e4e7", border: "1px solid rgba(255,255,255,0.1)" };
  return (
    <button onClick={onClick} disabled={disabled}
      className={base + " rounded-lg font-semibold transition-all " + (disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer hover:brightness-110 active:scale-[0.98]")}
      style={{ ...styles }}>
      {children}
    </button>
  );
}

function Section({ title, right, children, theme }) {
  return (
    <div className="bfg-card p-4 mb-3">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h3 className="bfg-display-accent" style={{ color: theme ? theme.primary : "#d4af37" }}>{title}</h3>
        {right}
      </div>
      {children}
    </div>
  );
}

function Sel({ value, onChange, children, w = "auto" }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}
      className="bfg-select"
      style={{ maxWidth: w === "100%" ? "100%" : 260, width: w }}>
      {children}
    </select>
  );
}

/* ================================================================
   SETUP SCREEN
   ================================================================ */
function SetupScreen({ onStart }) {
  const [names, setNames] = useState({ wcw: "", sd: "", nxt: "" });
  const ok = BRAND_KEYS.every((k) => names[k].trim().length > 0);
  return (
    <div className="bfg-page min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-lg bfg-shell">
        <div className="text-center mb-8">
          <div className="text-4xl bfg-display" style={{ color: "#fff" }}>
            Bound For <span style={{ color: "#d4af37" }}>Glory</span>
          </div>
          <div className="text-sm mt-2 font-medium tracking-widest uppercase" style={{ color: "#71717a" }}>GM Mod</div>
          <div className="text-xs mt-3" style={{ color: "#a1a1aa" }}>
            WCW · SmackDown · NXT — One season. 48 weeks. One champion brand.
          </div>
        </div>
        <div className="bfg-card p-5">
          {BRAND_KEYS.map((k) => {
            const t = THEME[k]; const c = BRAND_CONFIG[k];
            return (
              <div key={k} className="mb-4 last:mb-0">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-base bfg-display" style={{ color: t.primary }}>{c.name}</span>
                  <span className="text-xs" style={{ color: "#71717a" }}>{c.show} · {c.owner}</span>
                </div>
                <input
                  value={names[k]}
                  onChange={(e) => setNames({ ...names, [k]: e.target.value })}
                  placeholder={"Who's running " + c.name + "?"}
                  className="bfg-input"
                  style={{ borderColor: t.primary + "44" }}
                />
              </div>
            );
          })}
          <div className="bfg-alert bfg-alert-info mt-4 mb-4">
            Hot-seat play: each GM books their show on the same device, then the week advances together.
          </div>
          <Btn onClick={() => ok && onStart(names)} disabled={!ok}>Customize Rosters →</Btn>
          <div className="text-xs mt-3" style={{ color: "#71717a" }}>You'll tune stats on each roster before Week 1 kicks off.</div>
        </div>
      </div>
    </div>
  );
}

/* ================================================================
   HEADER + WEEK STRIP
   ================================================================ */
function TopBar({ state, theme, onReset, onMode, logo, onlineTag }) {
  const wk = state.week, mIdx = monthIdxOf(wk), cal = calOf(state, mIdx), wom = weekOfMonth(wk);
  return (
    <div className="bfg-glass sticky top-0 z-40 px-4 pt-4 pb-3">
      <div className="bfg-shell flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          {logo && <img src={logo} alt="" className="rounded-lg object-cover flex-shrink-0" style={{ width: 32, height: 32, border: "1px solid rgba(255,255,255,0.1)" }} />}
          <div className="min-w-0">
            <div className="text-base bfg-display truncate" style={{ color: "#fff" }}>
              Bound For <span style={{ color: theme.primary }}>Glory</span>
            </div>
            <div className="text-xs font-medium" style={{ color: "#71717a" }}>GM Mod</div>
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          {onlineTag && <Pill color="#16a34a" text="#dcfce7">{onlineTag}</Pill>}
          <Pill color={theme.primary} text="#0a0a0c">Week {wk}/{TOTAL_WEEKS}</Pill>
          <Pill color="rgba(255,255,255,0.1)" text="#d4d4d8">{cal.month} · Wk {wom}</Pill>
          {wom === 4 && (() => {
            const ev = brandEvent(state, mIdx, state.activeBrand);
            return ev
              ? <Pill color={theme.accent || "#b91c1c"}>PLE: {ev.ple}</Pill>
              : <Pill color="#27272a" text="#a1a1aa">No PLE this month</Pill>;
          })()}
          {onMode && <button onClick={onMode} className="bfg-link">Mode</button>}
          <button onClick={onReset} className="bfg-link">Reset</button>
        </div>
      </div>
    </div>
  );
}

function BrandSwitch({ state, onPick }) {
  return (
    <div className="flex gap-2 px-4 pt-3 bfg-shell">
      {BRAND_KEYS.map((k) => {
        const t = THEME[k]; const active = state.activeBrand === k; const locked = state.locked[k];
        return (
          <button key={k} onClick={() => onPick(k)}
            className={"bfg-brand-btn " + (active ? "bfg-brand-btn-active" : "")}
            style={{
              background: active ? `linear-gradient(180deg, ${t.deep}, rgba(0,0,0,0.4))` : undefined,
              borderColor: active ? t.primary + "66" : undefined,
              boxShadow: active ? `0 4px 24px ${t.glow}33` : undefined,
            }}>
            <div className="text-sm bfg-display" style={{ color: active ? t.primary : "#71717a" }}>
              {BRAND_CONFIG[k].name}{locked ? " ✓" : ""}
            </div>
            <div className="text-xs truncate mt-0.5" style={{ color: active ? "#a1a1aa" : "#52525b" }}>{state.players[k]}</div>
          </button>
        );
      })}
    </div>
  );
}

/* ================================================================
   DASHBOARD
   ================================================================ */
function Dashboard({ state, theme, onKickOffSeason, onGoRoster }) {
  const pill = useMemo(() => {
    const out = {}; BRAND_KEYS.forEach((k) => (out[k] = computePillars(state.brands[k]))); return out;
  }, [state]);
  const viewData = useMemo(() => {
    const byWeek = {};
    BRAND_KEYS.forEach((k) => state.brands[k].viewHist.forEach((h) => {
      byWeek[h.week] = byWeek[h.week] || { week: "W" + h.week, _w: h.week };
      byWeek[h.week][k] = Math.round(h.v / 1000);
    }));
    return Object.values(byWeek).sort((a, b) => a._w - b._w);
  }, [state]);
  if (state.screen === "rosterSetup") {
    return (
      <div className="pb-20">
        <Section title="Roster Setup" theme={theme}>
          <div className="text-sm mb-4 leading-relaxed" style={{ color: "#a1a1aa" }}>
            Before the season starts, open each brand's roster and edit <span style={{ color: "#fff", fontWeight: 600 }}>Overall · Work Rate · Promo Skill · Psychology · Charisma · Stamina · Star Power</span>.
          </div>
          <div className="flex flex-wrap gap-2">
            <Btn theme={theme} onClick={onGoRoster}>Edit Rosters</Btn>
            <Btn theme={theme} onClick={onKickOffSeason}>Kick Off Season — Week 1</Btn>
          </div>
        </Section>
      </div>
    );
  }
  const radarData = [
    { axis: "Story", wcw: pill.wcw.story, sd: pill.sd.story, nxt: pill.nxt.story },
    { axis: "Sponsors", wcw: pill.wcw.sponsor, sd: pill.sd.sponsor, nxt: pill.nxt.sponsor },
    { axis: "PLE & Fans", wcw: pill.wcw.ple, sd: pill.sd.ple, nxt: pill.nxt.ple },
    { axis: "Growth", wcw: pill.wcw.growth, sd: pill.sd.growth, nxt: pill.nxt.growth },
    { axis: "Profit", wcw: pill.wcw.profit, sd: pill.sd.profit, nxt: pill.nxt.profit },
  ];
  const sorted = [...BRAND_KEYS].sort((a, b) => pill[b].power - pill[a].power);
  const report = state.brands[state.activeBrand].lastMonthReport;
  return (
    <div className="pb-20">
      <Section title="Brand Power Standings" theme={theme} right={<span className="text-xs" style={{ color: "#71717a" }}>Story 34% · PLE 26% · Growth 22%</span>}>
        {sorted.map((k, i) => {
          const t = THEME[k]; const p = pill[k]; const b = state.brands[k];
          return (
            <div key={k} className="bfg-card-inner p-3 mb-2">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm bfg-display" style={{ color: "#71717a" }}>#{i + 1}</span>
                  <span className="text-base bfg-display" style={{ color: t.primary }}>{BRAND_CONFIG[k].name}</span>
                  <span className="text-xs" style={{ color: "#71717a" }}>{state.players[k]}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium uppercase tracking-wide" style={{ color: "#71717a" }}>Power</span>
                  <span className="text-xl bfg-display" style={{ color: t.primary }}>{Math.round(p.power)}</span>
                  <GradeBadge score={p.power} size="sm" />
                </div>
              </div>
              <div className="grid grid-cols-5 gap-1.5 mt-3 text-center">
                {[["Story", p.story], ["Sponsor", p.sponsor], ["PLE", p.ple], ["Growth", p.growth], ["Profit", p.profit]].map(([lab, v]) => (
                  <div key={lab} className="rounded-lg py-1.5" style={{ background: "rgba(255,255,255,0.04)" }}>
                    <div className="text-xs" style={{ color: "#71717a" }}>{lab}</div>
                    <div className="text-sm font-semibold" style={{ color: "#fff" }}>{Math.round(v)}</div>
                  </div>
                ))}
              </div>
              <div className="flex gap-3 mt-2 text-xs flex-wrap" style={{ color: "#71717a" }}>
                <span>📺 {fmtNum(b.viewership)}</span>
                <span>💰 <span style={{ color: b.cash < 0 ? "#ef4444" : "#22c55e" }}>{money(b.cash)}</span></span>
                <span>❤️ Fan Inv {Math.round(b.fanInv)}</span>
                <span>⭐ Pop {Math.round(b.pop)}</span>
              </div>
            </div>
          );
        })}
      </Section>

      <Section title="The 5 Pillars — Head to Head" theme={theme}>
        <div style={{ width: "100%", height: 260 }}>
          <ResponsiveContainer>
            <RadarChart data={radarData} outerRadius="70%">
              <PolarGrid stroke="#ffffff22" />
              <PolarAngleAxis dataKey="axis" tick={{ fill: "#9ca3af", fontSize: 11 }} />
              <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
              <Radar name="WCW" dataKey="wcw" stroke={THEME.wcw.primary} fill={THEME.wcw.primary} fillOpacity={0.18} />
              <Radar name="SmackDown" dataKey="sd" stroke={THEME.sd.primary} fill={THEME.sd.primary} fillOpacity={0.18} />
              <Radar name="NXT" dataKey="nxt" stroke={THEME.nxt.primary} fill={THEME.nxt.primary} fillOpacity={0.18} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </Section>

      {viewData.length > 1 && (
        <Section title="Viewership War (thousands)" theme={theme}>
          <div style={{ width: "100%", height: 220 }}>
            <ResponsiveContainer>
              <LineChart data={viewData}>
                <CartesianGrid stroke="#ffffff14" />
                <XAxis dataKey="week" tick={{ fill: "#9ca3af", fontSize: 10 }} />
                <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} />
                <Tooltip contentStyle={{ background: "#15151c", border: "1px solid #ffffff22", fontSize: 12 }} />
                <Line type="monotone" dataKey="wcw" name="WCW" stroke={THEME.wcw.primary} dot={false} />
                <Line type="monotone" dataKey="sd" name="SmackDown" stroke={THEME.sd.primary} dot={false} />
                <Line type="monotone" dataKey="nxt" name="NXT" stroke={THEME.nxt.primary} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Section>
      )}

      {report && (
        <Section title={"Last Month Report — " + report.month} theme={theme}>
          {report.objectives.map((o, i) => (
            <div key={i} className="text-xs mb-1 flex justify-between gap-2">
              <span style={{ color: o.done ? "#22c55e" : "#ef4444" }}>{o.done ? "✓" : "✗"} {o.text}</span>
              {o.done && <span style={{ color: "#22c55e" }}>{money(o.payout)}</span>}
            </div>
          ))}
          <div className="text-xs mt-1" style={{ color: "#9ca3af" }}>
            Base sponsor income {money(report.base)} · objective bonuses {money(report.payouts)}
          </div>
          {report.notes.map((n, i) => (
            <div key={i} className="text-xs mt-1" style={{ color: "#f59e0b" }}>• {n}</div>
          ))}
        </Section>
      )}

      <Section title="Newswire" theme={theme}>
        <div className="max-h-64 overflow-y-auto pr-1">
          {state.news.length === 0 && <div className="text-xs" style={{ color: "#9ca3af" }}>Quiet week. Too quiet.</div>}
          {state.news.map((n) => (
            <div key={n.id} className="text-xs mb-1 flex gap-2 items-start">
              <Pill color={THEME[n.brand].primary} text="#0b0b0f" style={{ flexShrink: 0 }}>{`W${n.week}`}</Pill>
              <span style={{ color: n.kind === "good" ? "#86efac" : n.kind === "bad" ? "#fca5a5" : "#d1d5db" }}>{n.text}</span>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}

/* ================================================================
   BOOKING TAB
   ================================================================ */
function UnitPicker({ brand, ids, onChange, exclude = [], theme, label, alFilter = DEFAULT_AL_FILTER }) {
  const pool = filterUnitsByAl(brand.units, alFilter);
  const avail = pool.filter((u) => unitAvailable(u) && !ids.includes(u.id) && !exclude.includes(u.id));
  return (
    <div className="flex-1 min-w-0">
      <div className="text-xs font-bold mb-1" style={{ color: "#9ca3af" }}>{label}</div>
      <div className="flex flex-wrap gap-1 mb-1">
        {ids.map((id) => {
          const u = unitById(brand, id);
          return (
            <button key={id} onClick={() => onChange(ids.filter((x) => x !== id))}
              className="text-xs px-2 py-1 rounded font-bold"
              style={{ background: theme.primary + "22", color: "#fff", border: "1px solid " + theme.primary + "55" }}>
              {u?.name} ✕
            </button>
          );
        })}
        {ids.length === 0 && <span className="text-xs" style={{ color: "#6b7280" }}>empty</span>}
      </div>
      <Sel value="" w="100%" onChange={(id) => id && onChange([...ids, id])}>
        <option value="">+ add wrestler / team…</option>
        {avail.map((u) => (
          <option key={u.id} value={u.id}>{u.name} ({u.al} · {u.ovr}{u.type === "t" ? " · TEAM" : ""})</option>
        ))}
      </Sel>
    </div>
  );
}

function MatchCard({ brand, m, idx, isMain, isPLE, cal, theme, onChange, onRemove }) {
  const upd = (patch) => onChange({ ...m, ...patch });
  const sides = getSides(m);
  const stipObj = STIPS.find((s) => s.id === m.stip) || STIPS[0];
  const isBR = !!stipObj.br;
  const allIn = sides.flat();
  const feud = findFeudMulti(brand, sides);
  const title = brand.titles.find((t) => t.id === m.titleId);
  const champWarning = title && title.champ && !allIn.includes(title.champ);
  const [showNotes, setShowNotes] = useState(!!m.notes);
  const [alFilter, setAlFilter] = useState(DEFAULT_AL_FILTER);
  const sideLabel = (i) => "Side " + String.fromCharCode(65 + i);
  const setSide = (i, ids) => { const ns = sides.map((s) => [...s]); ns[i] = ids; upd({ sides: ns }); };
  const addSide = () => { if (sides.length >= 8) return; upd({ sides: [...sides.map((s) => [...s]), []] }); };
  const dropSide = (i) => { if (sides.length <= 2) return; const ns = sides.filter((_, ix) => ix !== i); upd({ sides: ns, winner: 0 }); };
  return (
    <div className="rounded-lg p-2 mb-2" style={{ background: "#00000033", border: "1px solid " + (isMain ? theme.primary + "66" : "#ffffff14") }}>
      <div className="flex justify-between items-center mb-2">
        <div className="text-xs font-black" style={{ ...display, color: isMain ? theme.primary : "#9ca3af" }}>
          {isMain ? "★ MAIN EVENT" : "Match " + (idx + 1)}
          {sides.length > 2 && !isBR && <span className="ml-1" style={{ color: "#a78bfa" }}>{sides.length}-WAY</span>}
          {feud && <span className="ml-2" style={{ color: "#f97316" }}>🔥 feud heat {Math.round(feud.heat)}</span>}
        </div>
        <button onClick={onRemove} className="text-xs" style={{ color: "#ef4444" }}>remove</button>
      </div>

      {isBR ? (
        <div>
          <UnitPicker brand={brand} ids={allIn} exclude={[]} onChange={(ids) => upd({ sides: ids.map((id) => [id]) })} theme={theme} label="Entrants (6+)" />
          <div className="mt-2">
            <div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Last one standing</div>
            <Sel value={String(m.winner || 0)} onChange={(v) => upd({ winner: parseInt(v, 10) })}>
              {allIn.map((id, i) => <option key={id} value={i}>{unitById(brand, id)?.name}</option>)}
            </Sel>
          </div>
        </div>
      ) : (
        <>
          <div className="mb-2">
            <div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Filter roster</div>
            <AlFilterToggles filter={alFilter} onChange={setAlFilter} compact />
          </div>
          <div className="flex gap-2 flex-col sm:flex-row sm:flex-wrap">
            {sides.map((sideIds, i) => (
              <div key={i} className="flex-1 min-w-0">
                <UnitPicker brand={brand} ids={sideIds} exclude={sides.filter((_, ix) => ix !== i).flat()} onChange={(ids) => setSide(i, ids)} theme={theme} label={sideLabel(i)} alFilter={alFilter} />
                {sides.length > 2 && <button onClick={() => dropSide(i)} className="text-xs underline" style={{ color: "#ef4444" }}>drop {sideLabel(i)}</button>}
              </div>
            ))}
          </div>
          {sides.length < 8 && (
            <button onClick={addSide} className="text-xs mt-1 underline" style={{ color: theme.primary }}>
              + Add {sideLabel(sides.length)} {sides.length === 2 ? "(Triple Threat)" : sides.length === 3 ? "(Fatal 4-Way)" : ""}
            </button>
          )}
        </>
      )}

      <div className="flex flex-wrap gap-2 mt-2 items-end">
        <div>
          <div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Stipulation</div>
          <Sel value={m.stip} onChange={(v) => upd({ stip: v })}>
            {STIPS.filter((s) => !s.ple || isPLE).map((s) => <option key={s.id} value={s.id}>{s.n}</option>)}
          </Sel>
        </div>
        {!isBR && (
          <div>
            <div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Winner</div>
            <Sel value={String(m.winner || 0)} onChange={(v) => upd({ winner: parseInt(v, 10) })}>
              {sides.map((_, i) => <option key={i} value={i}>{sideLabel(i)}</option>)}
            </Sel>
          </div>
        )}
        <div>
          <div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Finish</div>
          <Sel value={m.finish} onChange={(v) => upd({ finish: v })}>
            {FINISHES.map((f) => <option key={f} value={f}>{f}</option>)}
          </Sel>
        </div>
        <div className="min-w-0">
          <div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Championship</div>
          <Sel value={m.titleId} onChange={(v) => upd({ titleId: v })}>
            <option value="">— non-title —</option>
            {brand.titles.map((t) => <option key={t.id} value={t.id}>{t.name}{t.champ ? "" : " (VACANT)"}</option>)}
          </Sel>
        </div>
        <label className="flex items-center gap-1 text-xs" style={{ color: "#d1d5db" }}>
          <input type="checkbox" checked={m.contender} onChange={(e) => upd({ contender: e.target.checked })} /> #1 Contender
        </label>
        {isPLE && feud && (
          <label className="flex items-center gap-1 text-xs font-bold" style={{ color: "#f97316" }}>
            <input type="checkbox" checked={m.blowoff} onChange={(e) => upd({ blowoff: e.target.checked })} /> 🔥 BLOWOFF (ends the feud)
          </label>
        )}
        {isPLE && cal && cal.theme === "mitb" && (
          <label className="flex items-center gap-1 text-xs font-bold" style={{ color: "#d4af37" }}>
            <input type="checkbox" checked={!!m.mitb} onChange={(e) => upd({ mitb: e.target.checked })} /> 💼 MITB ladder match
          </label>
        )}
        {isPLE && cal && cal.theme === "rumble" && (
          <label className="flex items-center gap-1 text-xs font-bold" style={{ color: "#d4af37" }}>
            <input type="checkbox" checked={!!m.rumble} onChange={(e) => upd({ rumble: e.target.checked })} /> 🏆 Rumble match
          </label>
        )}
        <button onClick={() => setShowNotes(!showNotes)} className="text-xs underline" style={{ color: "#9ca3af" }}>{showNotes ? "hide story" : "+ story"}</button>
      </div>
      {showNotes && (
        <textarea value={m.notes || ""} onChange={(e) => upd({ notes: e.target.value.slice(0, 300) })} rows={2}
          placeholder="Optional story for this match — spots, the story being told, how it ends…"
          className="w-full rounded p-2 text-xs mt-2" style={{ background: "#101016", color: "#eee", border: "1px solid #ffffff22" }} />
      )}
      {stipObj.fat >= 3 && <div className="text-xs mt-1" style={{ color: "#fdba74" }}>⚠ {stipObj.n} is brutal — heavy fatigue for everyone involved.</div>}
      {stipObj.multi && sides.length < 3 && !isBR && <div className="text-xs mt-1" style={{ color: "#fdba74" }}>⚠ {stipObj.n} works best with 3+ sides.</div>}
      {champWarning && <div className="text-xs mt-1" style={{ color: "#f59e0b" }}>⚠ Champion isn't in this match — the title can't change hands.</div>}
    </div>
  );
}

function BookingTab({ state, mutateL, mutateG, theme, canAct }) {
  const bKey = state.activeBrand;
  const brand = state.brands[bKey];
  const cfg = BRAND_CONFIG[bKey];
  const booking = state.booking[bKey];
  const locked = state.locked[bKey];
  const wk = state.week, mIdx = monthIdxOf(wk);
  const ev = brandEvent(state, mIdx, bKey);
  const hostPLE = !!(isPLEWeek(wk) && ev);
  const twoShow = hostPLE && (brand.fiveShow ?? !!cfg.extraPLE);
  const tvDone = twoShow && (brand.results || []).some((r) => r.week === wk && (r.season || 1) === (state.season || 1));
  const isPLE = hostPLE && (!twoShow || tvDone);
  const offWeek = isPLEWeek(wk) && !hostPLE;
  const tvRes = twoShow && tvDone && !locked ? [...(brand.results || [])].reverse().find((r) => r.week === wk) : null;
  const [grading, setGrading] = useState(false);
  const [gradeErr, setGradeErr] = useState(null);
  const script = booking.script || { mode: "quick", text: "", grade: null };

  const addMatch = () => mutateL((s) => {
    s.booking[bKey].matches.push({ id: "m" + Date.now(), sides: [[], []], stip: "std", finish: "Clean", winner: 0, titleId: "", contender: false, blowoff: false, notes: "" });
  });
  const addSeg = () => mutateL((s) => {
    s.booking[bKey].segments.push({ id: "s" + Date.now(), kind: SEG_KINDS[0], speakerId: "", targetId: "", tone: PROMO_TONES[0] });
  });

  const staleGrade = script.grade && script.grade.textLen !== script.text.length;

  /* MITB cash-in availability */
  const liveCases = (state.cases || []).filter((c) => {
    if (c.brandKey !== bKey) return false;
    const holder = unitById(brand, c.holderId);
    const title = brand.titles.find((t) => t.id === c.titleId);
    return holder && unitAvailable(holder) && title && title.champ && title.champ !== c.holderId;
  });

  const valid = (() => {
    if (booking.matches.length < 3) return "Book at least 3 matches.";
    for (const m of booking.matches) {
      const sides = getSides(m);
      const stipObj = STIPS.find((s) => s.id === m.stip) || STIPS[0];
      if (stipObj.br) { if (sides.flat().length < 6) return "Battle Royal needs at least 6 entrants."; }
      else { if (sides.length < 2 || sides.some((sd) => !sd.length)) return "Every side of every match needs at least one wrestler."; }
    }
    if (script.mode === "quick") { for (const sg of booking.segments) if (!sg.speakerId) return "Every segment needs a speaker."; }
    if (script.mode === "script" && !script.grade) return "Get your show script graded by AI before going live.";
    if (script.mode === "script" && staleGrade) return "Script changed since grading — re-grade before going live.";
    if (brand.activeEvent) return "Resolve the post-PLE fallout first (see popup).";
    return null;
  })();

  const belowStandard = booking.matches.length < cfg.minTV;

  const cardString = () => booking.matches.map((m, i) => {
    const sides = getSides(m);
    const stipObj = STIPS.find((s) => s.id === m.stip) || STIPS[0];
    const names = stipObj.br
      ? `${sides.flat().length}-Entrant Battle Royal (${sides.flat().map((id) => unitById(brand, id)?.name).join(", ")})`
      : sides.map((ids) => ids.map((id) => unitById(brand, id)?.name).join(" & ")).join(" vs ");
    const t = brand.titles.find((x) => x.id === m.titleId);
    const wIdx = clamp(parseInt(m.winner, 10) || 0, 0, sides.length - 1);
    const wNames = (sides[wIdx] || []).map((id) => unitById(brand, id)?.name).join(" & ");
    return `${i + 1}. ${names} — ${stipObj.n}${t ? " for the " + t.name : ""} — planned finish: ${wNames || "?"} wins (${m.finish})${m.notes ? " — story: " + m.notes : ""}`;
  }).join("\n");

  const gradeNow = async () => {
    if (!script.text.trim() || script.text.trim().length < 80) { setGradeErr("Give the AI something real — at least a paragraph."); return; }
    setGrading(true); setGradeErr(null);
    try {
      const g = await gradePromoAI(brand, { brandName: cfg.name, week: wk, pleName: isPLE ? ev.ple : null }, script.text, cardString());
      mutateL((s) => { s.booking[bKey].script.grade = { ...g, textLen: s.booking[bKey].script.text.length }; });
    } catch (e) {
      setGradeErr("Grading failed (network or parse error). Try again, or switch to Quick segments.");
    }
    setGrading(false);
  };

  if (locked && brand.lastResult && brand.lastResult.week === wk) {
    return <ResultCard res={brand.lastResult} theme={theme} cfg={cfg} />;
  }

  if (!canAct) {
    return (
      <div className="px-3 pb-24">
        <Section title={cfg.show + " — " + state.players[bKey] + "'s brand"} theme={theme}>
          <div className="text-sm" style={{ color: "#9ca3af" }}>
            {state.players[bKey] ? state.players[bKey] + " hasn't gone live yet this week. You can watch, but only they can book." : "Unclaimed brand."}
          </div>
        </Section>
      </div>
    );
  }

  return (
    <div className="px-3 pb-24">
      {tvRes && (
        <div className="rounded-xl p-2 mb-2 flex justify-between items-center flex-wrap gap-2" style={{ background: "#14532d33", border: "1px solid #16a34a55" }}>
          <span className="text-sm font-bold" style={{ color: "#86efac" }}>✓ TV done: {tvRes.rating.toFixed(1)}/10</span>
          <span className="text-xs" style={{ color: "#9ca3af" }}>Now the big one: book {ev.ple}. {cfg.show} is in the books.</span>
        </div>
      )}
      <Section theme={theme}
        title={isPLE ? "🏟 " + ev.ple + (ev.stadium ? " — STADIUM SHOW" : " — PLE") : twoShow ? cfg.show + " (TV night — PLE later this week)" : cfg.show}
        right={<Pill color={theme.primary} text="#0b0b0f">{cfg.matchFormat}</Pill>}>
        <div className="text-xs mb-2" style={{ color: "#9ca3af" }}>
          {isPLE
            ? "PLEs are graded harder — but blowing off hot feuds here pays out in rating, fan investment, and story score."
            : "Build feuds, defend gold, keep main events clean (or don't — heels gotta heel)."}
          {isPLE && ev.theme === "mitb" && " 💼 MITB night: flag one match as the ladder match — the winner gets a briefcase."}
          {isPLE && ev.theme === "rumble" && " 🏆 Rumble night: flag the Rumble match — winner gets a rocket strapped to them."}
          {offWeek && " Other brands have their PLE this week, but your TV still airs — counter-program them."}
          {twoShow && !isPLE && " You run TWO shows this week — tonight's TV, then " + ev.ple + "."}
        </div>

        <div className="rounded-lg p-2 mb-2 flex flex-wrap gap-2 items-center" style={{ background: "#00000033", border: "1px solid #ffffff14" }}>
          <span className="text-xs font-black" style={{ ...display, color: "#9ca3af" }}>📍 TOUR STOP</span>
          <Sel value={booking.market || DEFAULT_MARKET} onChange={(v) => mutateL((s) => { s.booking[bKey].market = v; })}>
            <optgroup label="Big Markets">{MARKETS.filter((m) => m.tier === "big").map((m) => {
              const tag = m.id === cfg.homeMarket ? " (HQ)"
                : m.id === "msg" && bKey === "nxt" ? " (NXT HQ)"
                : m.id === "msg" ? " (NXT HQ)" : "";
              return <option key={m.id} value={m.id}>{m.flag} {m.n}{tag}</option>;
            })}</optgroup>
            <optgroup label="Mid Markets">{MARKETS.filter((m) => m.tier === "mid").map((m) => <option key={m.id} value={m.id}>{m.flag} {m.n}</option>)}</optgroup>
            <optgroup label="Small Markets">{MARKETS.filter((m) => m.tier === "small").map((m) => <option key={m.id} value={m.id}>{m.flag} {m.n}</option>)}</optgroup>
            <optgroup label="🌍 International">{MARKETS.filter((m) => m.tier === "intl").map((m) => <option key={m.id} value={m.id}>{m.flag} {m.n}</option>)}</optgroup>
          </Sel>
          {(() => {
            const mkSel = MARKETS.find((x) => x.id === (booking.market || DEFAULT_MARKET)) || MARKETS[0];
            const hq = MARKETS.find((x) => x.id === cfg.homeMarket);
            const travel = marketTravel(mkSel);
            const seats = venueSeats(isPLE, false, mkSel);
            return (
              <span className="text-xs" style={{ color: "#9ca3af" }}>
                {hq ? `HQ: ${hq.n} · ` : ""}Tonight: {mkSel.n.split(",")[0]} · {fmtNum(seats)} seats · travel {money(travel)} · gate = show grade + story
              </span>
            );
          })()}
        </div>
        <div className="text-xs mb-2" style={{ color: "#6b7280" }}>
          Every brand uses the same {fmtNum(VENUE.tv)}-seat building ({fmtNum(VENUE.ple)} on PLEs). Pick any market — MSG, Atlanta, London, wherever. Same travel rules, same gate math. You win on the card you book.
        </div>

        {booking.matches.map((m, i) => (
          <MatchCard key={m.id} brand={brand} m={m} idx={i}
            isMain={i === booking.matches.length - 1} isPLE={isPLE} cal={ev} theme={theme}
            onChange={(nm) => mutateL((s) => { s.booking[bKey].matches[i] = nm; })}
            onRemove={() => mutateL((s) => { s.booking[bKey].matches.splice(i, 1); })} />
        ))}
        <Btn kind="ghost" onClick={addMatch} small>+ Add Match</Btn>
        {belowStandard && <div className="text-xs mt-2" style={{ color: "#f59e0b" }}>⚠ Below the {cfg.minTV}-match standard — the rating takes a hit.</div>}
      </Section>

      {liveCases.length > 0 && (
        <Section title="💼 Money in the Bank — Cash-In" theme={theme}>
          {!booking.cashIn ? (
            <div className="flex flex-wrap gap-2 items-end">
              {liveCases.map((c) => {
                const holder = unitById(brand, c.holderId);
                const title = brand.titles.find((t) => t.id === c.titleId);
                const champ = unitById(brand, title.champ);
                return (
                  <div key={c.id} className="rounded-lg p-2 flex-1" style={{ background: "#00000044", border: "1px solid #d4af3744" }}>
                    <div className="text-sm font-bold" style={{ color: "#d4af37" }}>{c.name}</div>
                    <div className="text-xs mb-2" style={{ color: "#d1d5db" }}>{holder.name} can cash in on {champ?.name} ({title.name})</div>
                    <div className="flex gap-2">
                      <Btn small theme={theme} onClick={() => mutateL((s) => { s.booking[bKey].cashIn = { caseId: c.id, winner: "holder" }; })}>Cash in — WINS</Btn>
                      <Btn small kind="ghost" onClick={() => mutateL((s) => { s.booking[bKey].cashIn = { caseId: c.id, winner: "champ" }; })}>Cash in — FAILS</Btn>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="flex justify-between items-center flex-wrap gap-2">
              <div className="text-sm font-bold" style={{ color: "#d4af37" }}>
                ARMED: cash-in happens tonight after the matches — {booking.cashIn.winner === "holder" ? "briefcase holder WINS the title" : "champion SURVIVES"}.
              </div>
              <button className="text-xs underline" style={{ color: "#ef4444" }} onClick={() => mutateL((s) => { s.booking[bKey].cashIn = null; })}>cancel</button>
            </div>
          )}
        </Section>
      )}

      <Section title="Creative — Promos & Story" theme={theme}
        right={
          <div className="flex gap-1">
            {[["quick", "Quick Segments"], ["script", "📝 Long-form Script"]].map(([id, label]) => (
              <button key={id} onClick={() => mutateL((s) => { s.booking[bKey].script.mode = id; })}
                className="px-2 py-1 rounded-full text-xs font-black"
                style={{ ...display, background: script.mode === id ? theme.primary : "#ffffff10", color: script.mode === id ? "#0b0b0f" : "#9ca3af" }}>
                {label}
              </button>
            ))}
          </div>
        }>
        {script.mode === "quick" && (<>
          <div className="flex justify-between items-center mb-2">
            <div className="text-xs" style={{ color: "#6b7280" }}>{booking.segments.length === 0 ? "No segments — fine, but promos build feuds and stars." : booking.segments.length + " segment(s)"}</div>
            <Btn kind="ghost" onClick={addSeg} small>+ Add Segment</Btn>
          </div>
          {booking.segments.map((sg, i) => (
            <div key={sg.id} className="rounded-lg p-2 mb-2 flex flex-wrap gap-2 items-end" style={{ background: "#00000033", border: "1px solid #ffffff14" }}>
              <div>
                <div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Type</div>
                <Sel value={sg.kind} onChange={(v) => mutateL((s) => { s.booking[bKey].segments[i].kind = v; })}>
                  {SEG_KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
                </Sel>
              </div>
              <div className="min-w-0">
                <div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Speaker</div>
                <Sel value={sg.speakerId} onChange={(v) => mutateL((s) => { s.booking[bKey].segments[i].speakerId = v; })}>
                  <option value="">— pick —</option>
                  {activeUnits(brand).map((u) => <option key={u.id} value={u.id}>{u.name} (PS {u.ps || "?"})</option>)}
                </Sel>
              </div>
              <div className="min-w-0">
                <div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Target (optional)</div>
                <Sel value={sg.targetId} onChange={(v) => mutateL((s) => { s.booking[bKey].segments[i].targetId = v; })}>
                  <option value="">— none —</option>
                  {brand.units.filter((u) => u.id !== sg.speakerId).map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
                </Sel>
              </div>
              <div>
                <div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Tone</div>
                <Sel value={sg.tone} onChange={(v) => mutateL((s) => { s.booking[bKey].segments[i].tone = v; })}>
                  {PROMO_TONES.map((t) => <option key={t} value={t}>{t}</option>)}
                </Sel>
              </div>
              <button onClick={() => mutateL((s) => { s.booking[bKey].segments.splice(i, 1); })} className="text-xs" style={{ color: "#ef4444" }}>remove</button>
            </div>
          ))}
        </>)}

        {script.mode === "script" && (<>
          <div className="text-xs mb-2" style={{ color: "#9ca3af" }}>
            Write the WHOLE show as a timeline, in order — promos and segments woven between the booked matches. The AI grades the creative and folds it into the show rating.
          </div>
          <textarea
            value={script.text}
            onChange={(e) => mutateL((s) => { s.booking[bKey].script.text = e.target.value; })}
            placeholder={"Cold open: " + (brand.titles[0] && brand.titles[0].champ ? (unitById(brand, brand.titles[0].champ)?.name || "your champ") : "your top star") + " walks out to a thunderous pop…"}
            rows={12}
            className="w-full rounded p-3 text-sm"
            style={{ background: "#101016", color: "#eee", border: "1px solid " + theme.primary + "44" }}
          />
          <div className="flex items-center justify-between mt-2 flex-wrap gap-2">
            <span className="text-xs" style={{ color: "#6b7280" }}>{script.text.length.toLocaleString()} characters</span>
            <Btn theme={theme} small disabled={grading} onClick={gradeNow}>{grading ? "⏳ The grader is reading…" : "🤖 Grade the Script"}</Btn>
          </div>
          {gradeErr && <div className="text-xs mt-2" style={{ color: "#f59e0b" }}>{gradeErr}</div>}
          {script.grade && (
            <div className="rounded-lg p-3 mt-2" style={{ background: "#00000044", border: "1px solid " + theme.primary + "44" }}>
              <div className="flex items-center gap-3">
                <span className="text-3xl font-black" style={{ ...display, color: script.grade.score >= 75 ? "#22c55e" : script.grade.score >= 55 ? "#d4af37" : "#ef4444" }}>{script.grade.score}</span>
                <GradeBadge score={script.grade.score} size="sm" />
                <span className="text-xs italic" style={{ color: "#d1d5db" }}>"{script.grade.verdict}"</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2 text-xs">
                <div>{script.grade.strengths.map((x, i) => <div key={i} style={{ color: "#86efac" }}>+ {x}</div>)}</div>
                <div>{script.grade.weaknesses.map((x, i) => <div key={i} style={{ color: "#fca5a5" }}>− {x}</div>)}</div>
              </div>
              <div className="text-xs mt-2" style={{ color: "#9ca3af" }}>This creative grade folds into tonight's show rating.</div>
              {staleGrade && <div className="text-xs mt-1" style={{ color: "#f59e0b" }}>You edited the script after grading — re-grade before going live.</div>}
            </div>
          )}
        </>)}
      </Section>

      <div className="sticky bottom-14">
        <div className="rounded-xl p-3 flex items-center justify-between gap-2 flex-wrap" style={{ background: "#0b0b0fdd", border: "1px solid " + theme.primary + "55", backdropFilter: "blur(6px)" }}>
          <div className="text-xs" style={{ color: valid ? "#f59e0b" : "#86efac" }}>{valid || "Card is ready. Go live."}</div>
          <Btn theme={theme} disabled={!!valid} onClick={() => mutateG((s) => { simulateShow(s, bKey); })}>▶ GO LIVE</Btn>
        </div>
      </div>
    </div>
  );
}

/* ================================================================
   RESULT CARD
   ================================================================ */
function Stars({ q }) {
  const stars = Math.round((q / 100) * 5 * 2) / 2;
  return <span style={{ color: "#d4af37" }}>{("★").repeat(Math.floor(stars))}{stars % 1 ? "½" : ""}</span>;
}

function ResultCard({ res, theme, cfg }) {
  return (
    <div className="px-3 pb-24">
      <div className="rounded-2xl p-4 mb-3 text-center" style={{ background: theme.grad, border: "1px solid " + theme.primary + "66" }}>
        <div className="text-xs font-bold tracking-widest" style={{ color: res.isPLE ? (theme.accent || "#9ca3af") : "#9ca3af", textTransform: "uppercase" }}>{res.isPLE ? "PREMIUM LIVE EVENT" : "WEEKLY TELEVISION"} · WEEK {res.week}</div>
        <div className="text-2xl font-black mt-1" style={{ ...display, color: "#fff" }}>{res.eventName}</div>
        <div className="flex items-center justify-center gap-3 mt-2">
          <span className="text-5xl font-black" style={{ ...display, color: theme.primary }}>{res.rating.toFixed(1)}</span>
          <GradeBadge score={res.rating * 10} />
        </div>
        <div className="flex justify-center gap-3 mt-2 text-xs flex-wrap" style={{ color: "#d1d5db" }}>
          <span>📺 {fmtNum(res.viewership)} <span style={{ color: res.viewDelta >= 0 ? "#86efac" : "#fca5a5" }}>({res.viewDelta >= 0 ? "+" : ""}{fmtNum(res.viewDelta)})</span></span>
          <span>🎟 {fmtNum(res.att)}/{fmtNum(res.capSeats)} — {res.selloutTag}</span>
          {res.market && <span>📍 {res.marketFlag} {res.market}</span>}
          <span style={{ color: res.net >= 0 ? "#86efac" : "#fca5a5" }}>{res.net >= 0 ? "▲" : "▼"} {money(res.net)}</span>
        </div>
      </div>

      {res.heatNotes.map((h, i) => (
        <div key={i} className="rounded-lg p-2 mb-2 text-sm font-bold" style={{ background: "#7c2d1233", border: "1px solid #f9731655", color: "#fdba74" }}>{h}</div>
      ))}

      {res.script && (
        <Section title="Creative Grade — folded into the show rating" theme={theme}>
          <div className="flex items-center gap-3">
            <span className="text-3xl font-black" style={{ ...display, color: res.script.score >= 75 ? "#22c55e" : res.script.score >= 55 ? "#d4af37" : "#ef4444" }}>{res.script.score}</span>
            <GradeBadge score={res.script.score} size="sm" />
            <span className="text-xs italic" style={{ color: "#d1d5db" }}>"{res.script.verdict}"</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2 text-xs">
            <div>{(res.script.strengths || []).map((x, i) => <div key={i} style={{ color: "#86efac" }}>+ {x}</div>)}</div>
            <div>{(res.script.weaknesses || []).map((x, i) => <div key={i} style={{ color: "#fca5a5" }}>− {x}</div>)}</div>
          </div>
        </Section>
      )}

      <Section title="The Card" theme={theme}>
        {res.matches.map((m, i) => (
          <div key={i} className="rounded-lg p-2 mb-2" style={{ background: "#00000033", border: "1px solid #ffffff14" }}>
            <div className="flex justify-between items-start gap-2 flex-wrap">
              <div>
                <div className="text-sm font-bold" style={{ color: "#fff" }}>{m.isMain ? "★ " : ""}{m.names}</div>
                <div className="text-xs" style={{ color: "#9ca3af" }}>{m.stip} · {m.finish} · Winner: {m.winner}{m.feudLinked ? " · 🔥 feud" : ""}{m.repeats > 0 ? " · ⚠ repeat ×" + m.repeats : ""}</div>
                {m.titleNote && <div className="text-xs mt-1 font-bold" style={{ color: theme.primary }}>{m.titleNote}</div>}
                {m.notes && <div className="text-xs mt-1 italic" style={{ color: "#6b7280" }}>{m.notes}</div>}
              </div>
              <div className="text-right">
                <div className="text-lg font-black" style={{ color: "#fff" }}>{m.q}</div>
                <div className="text-xs"><Stars q={m.q} /></div>
              </div>
            </div>
          </div>
        ))}
        {res.segments.length > 0 && <div className="text-xs font-bold mt-2 mb-1" style={{ color: "#9ca3af", ...display }}>SEGMENTS</div>}
        {res.segments.map((sg, i) => (
          <div key={i} className="text-xs mb-1 flex justify-between" style={{ color: "#d1d5db" }}>
            <span>{sg.kind}: <b>{sg.who}</b>{sg.target ? " → " + sg.target : ""} ({sg.tone}){sg.feudLinked ? " 🔥" : ""}</span>
            <span style={{ color: "#fff" }}>{sg.q}</span>
          </div>
        ))}
      </Section>

      <Section title="Box Office" theme={theme}>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="rounded p-2" style={{ background: "#16a34a18" }}>
            <div style={{ color: "#86efac" }} className="font-bold mb-1">REVENUE {money(res.revenue)}</div>
            <div style={{ color: "#d1d5db" }}>Gate {money(res.gate)}{res.gateMult ? <span style={{ color: "#9ca3af" }}> ({Math.round(res.gateMult * 100)}% of base — show + story)</span> : ""}</div>
            <div style={{ color: "#d1d5db" }}>Merch {money(res.merch)}</div>
            <div style={{ color: "#d1d5db" }}>TV/Streaming {money(res.tvMoney)}</div>
            <div style={{ color: "#d1d5db" }}>Ad spots {money(res.adRev)}</div>
            {res.pleBonus > 0 && <div style={{ color: "#d1d5db" }}>PLE buys {money(res.pleBonus)}</div>}
          </div>
          <div className="rounded p-2" style={{ background: "#dc262618" }}>
            <div style={{ color: "#fca5a5" }} className="font-bold mb-1">COSTS {money(res.costs)}</div>
            <div style={{ color: "#d1d5db" }}>Payroll {money(res.payroll)}</div>
            <div style={{ color: "#d1d5db" }}>Production {money(res.production)}</div>
            <div style={{ color: "#d1d5db" }}>Logistics {money(res.logistics)}</div>
          </div>
        </div>
        <div className="text-xs mt-2" style={{ color: "#9ca3af" }}>{cfg.perkNote}</div>
      </Section>

      <div className="text-center text-xs mt-2" style={{ color: "#9ca3af" }}>
        Show locked for Week {res.week}. Waiting on the other GMs — then advance the week from the bottom bar.
      </div>
    </div>
  );
}

/* ================================================================
   ROSTER TAB
   ================================================================ */
function NumEdit({ label, value, min, max, onChange }) {
  return (
    <label className="text-xs font-medium" style={labelStyle}>
      {label}
      <input type="number" value={value} min={min} max={max}
        onChange={(e) => onChange(clamp(parseInt(e.target.value || "0", 10), min, max))}
        className="bfg-input w-16 ml-1.5 py-1 text-center text-sm" />
    </label>
  );
}

function AddSuperstar({ state, mutateG, theme, bKey }) {
  const brand = state.brands[bKey];
  const cfg = BRAND_CONFIG[bKey];
  const [open, setOpen] = useState(false);
  const blank = { name: "", div: "", al: "F", sex: "M", type: "s", ovr: 75, rs: 75, ps: 70, psych: 72, cha: 70, sta: 80, pop: 70, mom: 50, salM: 0.5, yrs: 2, deb: true, bio: "" };
  const [f, setF] = useState(blank);
  const divs = [...new Set(brand.units.map((u) => u.div))];
  const sal = Math.round(f.salM * 1000000);
  const overCap = capUsed(brand) + sal > cfg.cap;
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));
  if (!open) return <Btn small theme={theme} onClick={() => setOpen(true)}>➕ Add New Superstar</Btn>;
  return (
    <div className="rounded-lg p-3 mb-2" style={{ background: "#00000044", border: "1px solid " + theme.primary + "44" }}>
      <div className="text-sm font-black mb-2" style={{ ...display, color: theme.primary }}>New Signing</div>
      <div className="flex flex-wrap gap-2 items-end">
        <input value={f.name} onChange={(e) => set("name", e.target.value)} placeholder="Name"
          className="rounded px-2 py-2 text-sm" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22" }} />
        <Sel value={f.div} onChange={(v) => set("div", v)}>
          <option value="">division…</option>
          {divs.map((d) => <option key={d} value={d}>{d}</option>)}
        </Sel>
        <Sel value={f.al} onChange={(v) => set("al", v)}><option value="F">Face</option><option value="H">Heel</option><option value="N">Tweener</option></Sel>
        <Sel value={f.sex} onChange={(v) => set("sex", v)}><option value="M">Male</option><option value="F">Female</option></Sel>
        <Sel value={f.type} onChange={(v) => set("type", v)}><option value="s">Singles</option><option value="t">Tag Team</option></Sel>
      </div>
      <div className="flex flex-wrap gap-3 mt-2 items-end">
        <NumEdit label="Overall" value={f.ovr} min={40} max={99} onChange={(v) => set("ovr", v)} />
        <NumEdit label="Work Rate" value={f.rs} min={40} max={99} onChange={(v) => set("rs", v)} />
        <NumEdit label="Promo Skill" value={f.ps} min={35} max={99} onChange={(v) => set("ps", v)} />
        <NumEdit label="Psychology" value={f.psych} min={40} max={99} onChange={(v) => set("psych", v)} />
        <NumEdit label="Charisma" value={f.cha} min={30} max={100} onChange={(v) => set("cha", v)} />
        <NumEdit label="Stamina" value={f.sta} min={40} max={100} onChange={(v) => set("sta", v)} />
        <NumEdit label="Star Power" value={f.pop} min={30} max={100} onChange={(v) => set("pop", v)} />
        <label className="text-xs" style={{ color: "#9ca3af" }}>
          Salary $M/yr
          <input type="number" step="0.1" min="0.1" value={f.salM} onChange={(e) => set("salM", Math.max(0.1, parseFloat(e.target.value || "0.1")))}
            className="w-20 ml-1 rounded px-1 py-1 text-sm text-center" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22" }} />
        </label>
        <NumEdit label="Years" value={f.yrs} min={1} max={3} onChange={(v) => set("yrs", v)} />
        <label className="text-xs flex items-center gap-1" style={{ color: "#9ca3af" }}>
          <input type="checkbox" checked={!f.deb} onChange={(e) => set("deb", !e.target.checked)} /> Hold for a surprise debut
        </label>
      </div>
      <textarea value={f.bio} onChange={(e) => set("bio", e.target.value.slice(0, 400))} rows={2} placeholder="Character notes for the AI grader (optional)"
        className="w-full rounded p-2 text-xs mt-2" style={{ background: "#101016", color: "#eee", border: "1px solid #ffffff22" }} />
      {overCap && <div className="text-xs mt-1" style={{ color: "#ef4444" }}>That salary blows past the cap.</div>}
      <div className="flex gap-2 mt-2">
        <Btn small theme={theme} disabled={!f.name.trim() || !f.div || overCap}
          onClick={() => {
            const o = { ...f, name: f.name.trim(), sal: sal, _taken: brand.units.map((u) => u.id) };
            mutateG((s) => {
              const nu = makeCustomUnit(o);
              s.brands[bKey].units.push(nu);
              pushNews(s, bKey, `${nu.name} has been signed to ${cfg.name}${nu.deb === false ? " — debut TBD" : ""}.`, "good");
            });
            setOpen(false);
            setF(blank);
          }}>
          Sign to Roster ({money(sal)}/yr × {f.yrs})
        </Btn>
        <Btn small kind="ghost" onClick={() => setOpen(false)}>cancel</Btn>
      </div>
    </div>
  );
}

function TeamMemberAdd({ onAdd, brand }) {
  const [v, setV] = useState("");
  return (
    <span className="inline-flex items-center gap-1">
      <input value={v} onChange={(e) => setV(e.target.value.slice(0, 30))} list="roster-names" placeholder="member name…"
        className="rounded px-2 py-1 text-xs" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22" }} />
      <datalist id="roster-names">{brand.units.map((u) => <option key={u.id} value={u.name} />)}</datalist>
      <button onClick={() => { if (v.trim()) { onAdd(v.trim()); setV(""); } }} className="text-xs underline" style={{ color: "#86efac" }}>+ add</button>
    </span>
  );
}

function RosterTab({ state, mutateG, theme, canAct }) {
  const bKey = state.activeBrand;
  const brand = state.brands[bKey];
  const cfg = BRAND_CONFIG[bKey];
  const used = capUsed(brand);
  const over = used > cfg.cap;
  const divs = [...new Set(brand.units.map((u) => u.div))];
  const [editId, setEditId] = useState(null);
  const [relId, setRelId] = useState(null);
  const [newFacName, setNewFacName] = useState("");
  const [newFacMember, setNewFacMember] = useState("");
  const preSeason = state.week === 1 && brand.showCount === 0;
  const canEditStats = preSeason || state.screen === "rosterSetup";
  const img = brand.images || { units: {}, titles: {} };

  const factions = useMemo(() => {
    const map = {};
    brand.units.forEach((u) => { if (u.fac) (map[u.fac] = map[u.fac] || []).push(u); });
    return map;
  }, [brand.units]);
  const teams = brand.units.filter((u) => u.type === "t");

  return (
    <div className="px-3 pb-24">
      <Section title="Front Office" theme={theme}>
        <div className="flex gap-4 flex-wrap">
          {[["Owner", cfg.owner, img.owner], ...(cfg.owner2 ? [["Owner", cfg.owner2, img.owner2]] : []), ["General Manager", cfg.gm, img.gm]].map(([role, name, src], i) => (
            <div key={role + i} className="flex items-center gap-2">
              <Ava src={src} name={name} size={64} ring={theme.primary} />
              <div>
                <div className="text-xs" style={{ color: "#9ca3af" }}>{role}</div>
                <div className="text-sm font-bold" style={{ color: "#fff" }}>{name}</div>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Championships" theme={theme}>
        {brand.titles.map((t) => {
          const c = t.champ ? unitById(brand, t.champ) : null;
          return (
            <div key={t.id} className="flex justify-between items-center text-sm mb-2 gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <Ava src={img.titles[t.id]} name={"🏆"} size={52} />
                <span className="truncate" style={{ color: "#d1d5db" }}>{t.name}</span>
              </div>
              <div className="flex items-center gap-2">
                {c && <Ava src={img.units[c.id]} name={c.name} size={44} ring={theme.primary} />}
                <span className="font-bold text-right" style={{ color: c ? theme.primary : "#6b7280" }}>{c ? c.name : "VACANT" + (t.note ? " — " + t.note : "")}</span>
              </div>
            </div>
          );
        })}
      </Section>

      <Section title="Salary Cap — $150M league-wide" theme={theme}>
        <div className="flex justify-between text-xs mb-1">
          <span style={{ color: "#9ca3af" }}>Roster payroll {money(used)} of {money(cfg.cap)}</span>
          <span style={{ color: over ? "#ef4444" : "#86efac" }}>{over ? "OVER CAP by " + money(used - cfg.cap) : money(cfg.cap - used) + " in space"}</span>
        </div>
        <Bar pct={(used / cfg.cap) * 100} color={over ? "#ef4444" : theme.primary} />
        {canAct && <div className="mt-2"><AddSuperstar state={state} mutateG={mutateG} theme={theme} bKey={bKey} /></div>}
      </Section>

      {brand.mandates.length > 0 && (
        <Section title="Active Network Mandates" theme={theme}>
          {brand.mandates.map((md, i) => (
            <div key={i} className="text-xs mb-1" style={{ color: "#fca5a5" }}>
              {unitById(brand, md.unitId)?.name} must {md.type.toUpperCase()} next {md.remaining} match(es) — $2M fine per violation.
            </div>
          ))}
        </Section>
      )}

      {brand.pendingScrewjob && (
        <Section title="Backstage Demand" theme={theme}>
          <div className="text-xs" style={{ color: "#fca5a5" }}>
            Screw {unitById(brand, brand.pendingScrewjob.unitId)?.name} in a championship match (Screwjob finish, they lose) THIS month — or pay a $10M settlement at month's end.
          </div>
        </Section>
      )}

      <Section title={"Tag Teams (" + teams.length + ")"} theme={theme}>
        {teams.map((u) => (
          <div key={u.id} className="rounded-lg p-2 mb-2" style={{ background: "#00000033", border: "1px solid #ffffff14" }}>
            <div className="flex justify-between items-center gap-2 flex-wrap">
              <div className="flex items-center gap-2 min-w-0">
                <Ava src={img.units[u.id]} name={u.name} size={44} />
                {canAct ? (
                  <input defaultValue={u.name}
                    onBlur={(e) => { const v = e.target.value.slice(0, 40); if (v.trim() && v !== u.name) mutateG((s) => { const x = unitById(s.brands[bKey], u.id); if (x) x.name = v.trim(); }); }}
                    className="rounded px-2 py-1 text-sm font-bold" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22" }} />
                ) : <span className="truncate font-bold" style={{ color: "#fff" }}>{u.name}</span>}
                <AlPill al={u.al} />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs" style={{ color: "#9ca3af" }}>OVR {u.ovr} · RS {u.rs} · {u.w}–{u.l}</span>
                {canAct && (
                  <select value={u.al} onChange={(e) => mutateG((s) => { const x = unitById(s.brands[bKey], u.id); if (x) x.al = e.target.value; })}
                    className="rounded px-1 py-1 text-xs" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22" }}>
                    <option value="F">Face</option><option value="H">Heel</option><option value="N">Tweener</option>
                  </select>
                )}
              </div>
            </div>
            <div className="flex flex-wrap gap-1 mt-2 items-center">
              <span className="text-xs" style={{ color: "#9ca3af" }}>Members:</span>
              {(u.members || []).map((mName, mi) => (
                <span key={mi} className="text-xs px-2 py-1 rounded inline-flex items-center gap-1" style={{ background: "#ffffff10", color: "#d1d5db" }}>
                  {mName}
                  {canAct && <button onClick={() => mutateG((s) => { const x = unitById(s.brands[bKey], u.id); if (x) x.members = (x.members || []).filter((_, j) => j !== mi); })} style={{ color: "#ef4444" }}>✕</button>}
                </span>
              ))}
              {(u.members || []).length === 0 && <span className="text-xs" style={{ color: "#6b7280" }}>no listed members</span>}
              {canAct && <TeamMemberAdd brand={brand} onAdd={(nm) => mutateG((s) => { const x = unitById(s.brands[bKey], u.id); if (x) x.members = [...(x.members || []), nm]; })} />}
            </div>
          </div>
        ))}
        {teams.length === 0 && <div className="text-xs" style={{ color: "#6b7280" }}>No registered teams.</div>}
      </Section>

      <Section title={"Factions (" + Object.keys(factions).length + ")"} theme={theme}>
        {Object.entries(factions).map(([fac, members]) => (
          <div key={fac} className="rounded-lg p-2 mb-2" style={{ background: "#00000033", border: "1px solid #ffffff14" }}>
            <div className="flex justify-between items-center flex-wrap gap-1">
              <span className="text-sm font-black" style={{ ...display, color: theme.primary }}>{fac}</span>
              {canAct && (
                <Sel value="" onChange={(id) => id && mutateG((s) => { const u = unitById(s.brands[bKey], id); if (u) u.fac = fac; })}>
                  <option value="">+ add member…</option>
                  {brand.units.filter((u) => u.fac !== fac).map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
                </Sel>
              )}
            </div>
            <div className="flex flex-wrap gap-1 mt-1">
              {members.map((u) => (
                <span key={u.id} className="text-xs px-2 py-1 rounded inline-flex items-center gap-1" style={{ background: "#ffffff10", color: "#d1d5db" }}>
                  <Ava src={img.units[u.id]} name={u.name} size={16} /> {u.name}
                  {canAct && <button onClick={() => mutateG((s) => { const x = unitById(s.brands[bKey], u.id); if (x) x.fac = null; })} style={{ color: "#ef4444" }}>✕</button>}
                </span>
              ))}
            </div>
          </div>
        ))}
        {canAct && (
          <div className="flex flex-wrap gap-2 items-end mt-2">
            <input value={newFacName} onChange={(e) => setNewFacName(e.target.value)} placeholder="New faction name"
              className="rounded px-2 py-2 text-sm" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22" }} />
            <Sel value={newFacMember} onChange={setNewFacMember}>
              <option value="">first member…</option>
              {brand.units.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
            </Sel>
            <Btn small theme={theme} disabled={!newFacName.trim() || !newFacMember}
              onClick={() => { const nm = newFacName.trim(); const mb = newFacMember; mutateG((s) => { const u = unitById(s.brands[bKey], mb); if (u) u.fac = nm; }); setNewFacName(""); setNewFacMember(""); }}>
              ⚒ Form Faction
            </Btn>
          </div>
        )}
      </Section>

      <Section title={canEditStats ? "Roster — stat editing OPEN" : "Roster"} theme={theme}>
        {!canEditStats && canAct && <div className="text-xs mb-2" style={{ color: "#9ca3af" }}>Season is live — stats are locked. Alignment, bios, debuts and releases stay open.</div>}
        {canEditStats && <div className="text-xs mb-2" style={{ color: "#86efac" }}>Edit Overall, Work Rate, Promo Skill, Psychology, Charisma, Stamina, and Star Power — click <b>edit</b> on any wrestler.</div>}
        {divs.map((d) => (
          <div key={d} className="mb-3">
            <div className="text-xs font-black mb-1" style={{ ...display, color: "#9ca3af" }}>{d}</div>
            {brand.units.filter((u) => u.div === d).sort((a, b) => b.ovr - a.ovr).map((u) => {
              const [mLab, mCol] = moraleLabel(u.mor ?? 60);
              return (
                <div key={u.id} className="rounded-lg p-2 mb-1" style={{ background: "#00000033", border: "1px solid #ffffff14" }}>
                  <div className="flex justify-between items-center gap-2 flex-wrap">
                    <div className="min-w-0 flex items-center gap-2">
                      <Ava src={img.units[u.id]} name={u.name} size={52} />
                      <div className="min-w-0">
                        <span className="text-sm font-bold" style={{ color: "#fff" }}>{u.name}</span>
                        <span className="ml-2"><AlPill al={u.al} /></span>
                        {u.deb === false && <span className="ml-1"><Pill color="#1e3a8a" text="#bfdbfe">UNDEBUTED</Pill></span>}
                        {u.holdout && <span className="ml-1"><Pill color="#7f1d1d" text="#fecaca">HOLDOUT</Pill></span>}
                        {!u.holdout && u.wants && <span className="ml-1"><Pill color="#7c2d12" text="#fdba74">WANTS {u.wants.toUpperCase()}</Pill></span>}
                        {u.fac && <span className="ml-1 text-xs" style={{ color: "#9ca3af" }}>· {u.fac}</span>}
                        {u.guest && <span className="ml-1"><Pill color="#7c3aed">GUEST</Pill></span>}
                        {u.merchHot > 0 && <span className="ml-1"><Pill color="#f97316">🔥 MERCH</Pill></span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-3 text-xs" style={{ color: "#9ca3af" }}>
                      <span style={{ color: mCol }}>{mLab}</span>
                      <span>OVR <b style={{ color: "#fff" }}>{u.ovr}</b></span>
                      <span>WR <b style={{ color: "#fff" }}>{u.rs || "?"}</b></span>
                      <span>PS <b style={{ color: "#fff" }}>{u.ps || "?"}</b></span>
                      <span>★ <b style={{ color: "#fff" }}>{Math.round(u.pop)}</b></span>
                      <span>{u.w}–{u.l}</span>
                      <span>{money(u.sal)}/yr · {u.yrs || 1}yr{(u.yrs || 1) > 1 ? "s" : ""}</span>
                      {canAct && <button onClick={() => { setEditId(editId === u.id ? null : u.id); setRelId(null); }} className="underline">{editId === u.id ? "close" : "edit"}</button>}
                    </div>
                  </div>
                  <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-7 gap-2 mt-1 items-center">
                    <div><div className="text-xs" style={{ color: "#9ca3af" }}>Work Rate {u.rs || "?"}</div><Bar pct={u.rs || 50} color="#3b82f6" h={5} /></div>
                    <div><div className="text-xs" style={{ color: "#9ca3af" }}>Promo {u.ps || "?"}</div><Bar pct={u.ps || 50} color="#a855f7" h={5} /></div>
                    <div><div className="text-xs" style={{ color: "#9ca3af" }}>Psych {u.psych ?? "?"}</div><Bar pct={u.psych ?? 50} color="#6366f1" h={5} /></div>
                    <div><div className="text-xs" style={{ color: "#9ca3af" }}>Charisma {u.cha ?? "?"}</div><Bar pct={u.cha ?? u.pop} color="#ec4899" h={5} /></div>
                    <div><div className="text-xs" style={{ color: "#9ca3af" }}>Star Power {Math.round(u.pop)}</div><Bar pct={u.pop} color="#22c55e" h={5} /></div>
                    <div><div className="text-xs" style={{ color: "#9ca3af" }}>Stamina {Math.round(u.sta || 80)}</div><Bar pct={u.sta || 80} color="#14b8a6" h={5} /></div>
                    <div><div className="text-xs" style={{ color: "#9ca3af" }}>Morale {Math.round(u.mor ?? 60)}</div><Bar pct={u.mor ?? 60} color={mCol} h={5} /></div>
                  </div>
                  {canAct && editId === u.id && (
                    <div className="rounded p-2 mt-2" style={{ background: "#ffffff08" }}>
                      <div className="flex flex-wrap gap-3 items-center">
                        <label className="text-xs" style={{ color: "#9ca3af" }}>
                          Alignment
                          <select value={u.al} onChange={(e) => mutateG((s) => { const x = unitById(s.brands[bKey], u.id); if (x) x.al = e.target.value; })}
                            className="ml-1 rounded px-1 py-1 text-sm" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22" }}>
                            <option value="F">Face</option><option value="H">Heel</option><option value="N">Tweener</option>
                          </select>
                        </label>
                        {canEditStats ? (<>
                          <NumEdit label="Overall" value={u.ovr} min={40} max={99} onChange={(v) => mutateG((s) => { const x = unitById(s.brands[bKey], u.id); if (x) x.ovr = v; })} />
                          <NumEdit label="Work Rate" value={u.rs || u.ovr} min={40} max={99} onChange={(v) => mutateG((s) => { const x = unitById(s.brands[bKey], u.id); if (x) x.rs = v; })} />
                          <NumEdit label="Promo Skill" value={u.ps || u.ovr} min={35} max={99} onChange={(v) => mutateG((s) => { const x = unitById(s.brands[bKey], u.id); if (x) x.ps = v; })} />
                          <NumEdit label="Psychology" value={u.psych ?? u.ovr - 3} min={40} max={99} onChange={(v) => mutateG((s) => { const x = unitById(s.brands[bKey], u.id); if (x) x.psych = v; })} />
                          <NumEdit label="Charisma" value={u.cha ?? u.pop} min={30} max={100} onChange={(v) => mutateG((s) => { const x = unitById(s.brands[bKey], u.id); if (x) x.cha = v; })} />
                          <NumEdit label="Stamina" value={u.sta || 80} min={40} max={100} onChange={(v) => mutateG((s) => { const x = unitById(s.brands[bKey], u.id); if (x) x.sta = v; })} />
                          <NumEdit label="Star Power" value={Math.round(u.pop)} min={30} max={100} onChange={(v) => mutateG((s) => { const x = unitById(s.brands[bKey], u.id); if (x) x.pop = v; })} />
                          <label className="text-xs flex items-center gap-1" style={{ color: "#9ca3af" }}>
                            <input type="checkbox" checked={u.deb === false} onChange={(e) => mutateG((s) => { const x = unitById(s.brands[bKey], u.id); if (x) x.deb = !e.target.checked; })} /> hold for surprise debut
                          </label>
                        </>) : <span className="text-xs" style={{ color: "#6b7280" }}>Stats locked in-season.</span>}
                      </div>
                      <textarea
                        defaultValue={u.bio || ""}
                        onBlur={(e) => { const v = e.target.value.slice(0, 400); mutateG((s) => { const x = unitById(s.brands[bKey], u.id); if (x) x.bio = v; }); }}
                        rows={2} placeholder={"Character notes for the AI grader (optional) — who is " + u.name + " right now?"}
                        className="w-full rounded p-2 text-xs mt-2" style={{ background: "#101016", color: "#eee", border: "1px solid #ffffff22" }} />
                      <div className="flex flex-wrap gap-2 mt-2 items-center">
                        {u.deb === false && <Btn small theme={theme} onClick={() => mutateG((s) => {
                          const x = unitById(s.brands[bKey], u.id); if (!x) return;
                          x.deb = true; x.mom = clamp(x.mom + 15, 0, 100); x.lastBooked = s.week;
                          pushNews(s, bKey, `🚨 DEBUT: ${x.name} has arrived on ${BRAND_CONFIG[bKey].show}!`, "good");
                          addPost(s, bKey, { kind: "pundit", name: "Squared Circle SZN", handle: "@SquaredCircleSZN", text: `🚨 DEBUT ALERT: ${x.name} just showed up on ${BRAND_CONFIG[bKey].show}. Nobody saw this coming.`, viral: true });
                        })}>🚨 Debut Now</Btn>}
                        {((u.mor ?? 60) < 40) && <Btn small kind="ghost" disabled={brand.cash < 500000} onClick={() => mutateG((s) => clearTheAir(s, bKey, u.id))}>🤝 Clear the air ($500K)</Btn>}
                        {!u.guest && (relId === u.id
                          ? <Btn small kind="danger" onClick={() => { setRelId(null); setEditId(null); mutateG((s) => releaseUnit(s, bKey, u.id)); }}>CONFIRM release ({money(Math.round(u.sal * 0.5))} buyout)</Btn>
                          : <button className="text-xs underline" style={{ color: "#ef4444" }} onClick={() => setRelId(u.id)}>release…</button>)}
                      </div>
                    </div>
                  )}
                  {u.status && (
                    <div className="flex justify-between items-center mt-1">
                      <span className="text-xs font-bold" style={{ color: "#fca5a5" }}>🚑 {u.status.kind} — {u.status.weeks} wk{u.status.weeks !== 1 ? "s" : ""} left</span>
                      {canAct && u.status.reducible && (
                        <Btn small kind="ghost" disabled={brand.cash < REDUCE_COST}
                          onClick={() => mutateG((s) => reduceStatus(s, bKey, u.id))}>
                          −4 wks ({money(REDUCE_COST)})
                        </Btn>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </Section>
    </div>
  );
}

/* ================================================================
   FEUDS TAB
   ================================================================ */
function FeudsTab({ state, mutateG, theme, canAct }) {
  const bKey = state.activeBrand;
  const brand = state.brands[bKey];
  const [a, setA] = useState(""); const [b, setB] = useState("");
  const [alFilter, setAlFilter] = useState(DEFAULT_AL_FILTER);
  const pool = filterUnitsByAl(brand.units, alFilter);
  const start = () => {
    if (!a || !b || a === b) return;
    const aId = a, bId = b;
    mutateG((s) => {
      const br = s.brands[bKey];
      const ua = unitById(br, aId), ub = unitById(br, bId);
      if (!ua || !ub) return;
      br.feuds.push({ id: "f" + Date.now(), aId, bId, label: ua.name + " vs " + ub.name, heat: 25, lastTouched: s.week, done: false });
      pushNews(s, bKey, "New program: " + ua.name + " vs " + ub.name + ".", "info");
    });
    setA(""); setB("");
  };
  const live = brand.feuds.filter((f) => !f.done);
  return (
    <div className="px-3 pb-24">
      {canAct && (
        <Section title="Start a Program" theme={theme}>
          <div className="mb-2">
            <div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Filter roster</div>
            <AlFilterToggles filter={alFilter} onChange={setAlFilter} />
          </div>
          <div className="flex gap-2 flex-wrap items-end">
            <div><div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Side A</div>
              <Sel value={a} onChange={setA}><option value="">— pick —</option>{pool.map((u) => <option key={u.id} value={u.id}>{u.name} ({u.al === "F" ? "Face" : u.al === "H" ? "Heel" : "Tweener"})</option>)}</Sel></div>
            <div><div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Side B</div>
              <Sel value={b} onChange={setB}><option value="">— pick —</option>{pool.filter((u) => u.id !== a).map((u) => <option key={u.id} value={u.id}>{u.name} ({u.al === "F" ? "Face" : u.al === "H" ? "Heel" : "Tweener"})</option>)}</Sel></div>
            <Btn theme={theme} onClick={start} disabled={!a || !b}>🔥 Light It</Btn>
          </div>
          <div className="text-xs mt-2" style={{ color: "#9ca3af" }}>
            Feuds gain heat from their matches and promos. Ignore one for 2+ weeks and it cools; 5 weeks idle and it fizzles (story score hit). Blow it off at a PLE for the payoff.
          </div>
        </Section>
      )}
      <Section title={"Active Programs (" + live.length + ")"} theme={theme}>
        {live.length === 0 && <div className="text-xs" style={{ color: "#6b7280" }}>Cold roster. Start a program — stories sell tickets.</div>}
        {live.map((f) => {
          const idle = state.week - f.lastTouched;
          return (
            <div key={f.id} className="rounded-lg p-2 mb-2" style={{ background: "#00000033", border: "1px solid #ffffff14" }}>
              <div className="flex justify-between items-center gap-2 flex-wrap">
                <span className="text-sm font-bold" style={{ color: "#fff" }}>{f.label}</span>
                <div className="flex items-center gap-2">
                  {idle >= 2 && <Pill color="#7f1d1d">cooling — {idle} wks idle</Pill>}
                  {canAct && (
                    <button className="text-xs" style={{ color: "#ef4444" }}
                      onClick={() => mutateG((s) => {
                        const br = s.brands[bKey]; const ff = br.feuds.find((x) => x.id === f.id);
                        if (ff) { ff.done = true; br.storyScore = clamp(br.storyScore - 3, 0, 100); }
                      })}>drop (−story)</button>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <div className="flex-1"><Bar pct={f.heat} color="#f97316" /></div>
                <span className="text-xs font-bold" style={{ color: "#fdba74" }}>{Math.round(f.heat)} heat</span>
              </div>
            </div>
          );
        })}
      </Section>
    </div>
  );
}

/* ================================================================
   SPONSORS TAB
   ================================================================ */
function OppCard({ state, mutateG, theme, bKey, opp, canAct }) {
  const brand = state.brands[bKey];
  const champIds = brand.titles.filter((t) => t.champ).map((t) => t.champ);
  const eligible = activeUnits(brand).filter((u) => !opp.champOnly || champIds.includes(u.id));
  const [sel, setSel] = useState("");
  const cd = (brand.oppCd[opp.id] || 0) - state.week;
  return (
    <div className="rounded-lg p-2 mb-2" style={{ background: "#00000044", border: "1px solid " + theme.primary + "33" }}>
      <div className="flex justify-between items-start gap-2 flex-wrap">
        <div className="min-w-0">
          <div className="text-xs font-black" style={{ ...display, color: theme.primary }}>{opp.lane}</div>
          <div className="text-sm font-bold" style={{ color: "#fff" }}>{opp.name}{opp.viral ? " 🌟" : ""}{opp.champOnly ? " (champions only)" : ""}</div>
          <div className="text-xs" style={{ color: "#9ca3af" }}>+{money(opp.rev)} · pop +{opp.pop} · mom +{opp.mom} · morale +{opp.mor} · viewers +{fmtNum(opp.view)}</div>
        </div>
        <Pill color="#1f2937">{opp.cd}wk cooldown</Pill>
      </div>
      {canAct && (
        <div className="flex gap-2 mt-2 items-end flex-wrap">
          <Sel value={sel} onChange={setSel}>
            <option value="">{opp.champOnly ? "pick a champion…" : "pick a wrestler…"}</option>
            {eligible.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
          </Sel>
          {cd > 0
            ? <Pill color="#7f1d1d" text="#fecaca">on cooldown — {cd}wk left</Pill>
            : <Btn small theme={theme} disabled={!sel} onClick={() => { const id = sel; setSel(""); mutateG((s) => useOpportunity(s, bKey, opp.id, id)); }}>Send them</Btn>}
        </div>
      )}
    </div>
  );
}

function SponsorsTab({ state, mutateG, theme, canAct }) {
  const bKey = state.activeBrand;
  const brand = state.brands[bKey];
  const L = brand.monthLog;
  return (
    <div className="px-3 pb-24">
      <Section title="🌟 Exclusive Brand Opportunities" theme={theme}>
        <div className="text-xs mb-2" style={{ color: "#9ca3af" }}>
          Lanes only {BRAND_CONFIG[bKey].name} can run — earn money, popularity, momentum, and sponsor goodwill.
        </div>
        {OPPORTUNITIES[bKey].map((opp) => <OppCard key={opp.id} state={state} mutateG={mutateG} theme={theme} bKey={bKey} opp={opp} canAct={canAct} />)}
      </Section>

      <Section title="This Month's Sponsor Objectives" theme={theme}>
        {brand.objectives.length === 0 && <div className="text-xs" style={{ color: "#6b7280" }}>No objectives issued yet.</div>}
        {brand.objectives.map((o) => {
          const tpl = OBJ_TEMPLATES.find((t) => t.t === o.t);
          const onPace = tpl ? !!tpl.check(L, o) : false;
          return (
            <div key={o.id} className="rounded-lg p-2 mb-2 flex justify-between items-center gap-2" style={{ background: "#00000033", border: "1px solid #ffffff14" }}>
              <div>
                <div className="text-sm" style={{ color: "#fff" }}>{o.text}</div>
                <div className="text-xs" style={{ color: "#9ca3af" }}>Bonus: {money(o.payout)}</div>
              </div>
              <Pill color={onPace ? "#14532d" : "#374151"} text={onPace ? "#86efac" : "#d1d5db"}>{onPace ? "ON PACE ✓" : "not yet"}</Pill>
            </div>
          );
        })}
        <div className="text-xs mt-2" style={{ color: "#9ca3af" }}>
          Product sponsors pay monthly, scaled by relationship. Hit objectives: +5 rel and a cash bonus. Miss: −12 rel. Below 30 rel they pause the contract.
        </div>
      </Section>

      <Section title="Contracts" theme={theme}>
        {brand.sponsors.map((sp) => (
          <div key={sp.id} className="rounded-lg p-2 mb-1" style={{ background: "#00000033", border: "1px solid #ffffff14", opacity: sp.paused ? 0.55 : 1 }}>
            <div className="flex justify-between items-center gap-2 flex-wrap">
              <span className="text-sm font-bold" style={{ color: "#fff" }}>
                {sp.n} {sp.media && <Pill color="#1f2937">MEDIA</Pill>} {sp.perk && <Pill color="#14532d" text="#86efac">{sp.perk.toUpperCase()} PERK</Pill>} {sp.paused && <Pill color="#7f1d1d" text="#fecaca">PAUSED</Pill>}
              </span>
              <span className="text-xs" style={{ color: sp.v < 0 ? "#fca5a5" : "#9ca3af" }}>{sp.v < 0 ? money(sp.v * 1e6) + "/yr (you pay)" : money(sp.v * 1e6) + "/yr"}</span>
            </div>
            {!sp.media && sp.v > 0 && (
              <div className="flex items-center gap-2 mt-1">
                <div className="flex-1"><Bar pct={sp.rel} color={sp.rel < 30 ? "#ef4444" : sp.rel < 55 ? "#f59e0b" : "#22c55e"} h={5} /></div>
                <span className="text-xs" style={{ color: "#9ca3af" }}>rel {Math.round(sp.rel)}</span>
              </div>
            )}
          </div>
        ))}
      </Section>
    </div>
  );
}

/* ================================================================
   FINANCE TAB
   ================================================================ */
function FinanceTab({ state, theme }) {
  const bKey = state.activeBrand;
  const brand = state.brands[bKey];
  const margin = brand.revenueTotal > 0 ? ((brand.revenueTotal - brand.costTotal) / brand.revenueTotal) * 100 : 0;
  return (
    <div className="px-3 pb-24">
      <div className="rounded-2xl p-4 mb-3 text-center" style={{ background: theme.grad, border: "1px solid " + theme.primary + "66" }}>
        <div className="text-xs tracking-widest" style={{ color: "#9ca3af" }}>WAR CHEST</div>
        <div className="text-4xl font-black" style={{ ...display, color: brand.cash < 0 ? "#ef4444" : theme.primary }}>{money(brand.cash)}</div>
        <div className="flex justify-center gap-4 mt-2 text-xs" style={{ color: "#d1d5db" }}>
          <span>Season revenue {money(brand.revenueTotal)}</span>
          <span>Costs {money(brand.costTotal)}</span>
          <span style={{ color: margin >= 0 ? "#86efac" : "#fca5a5" }}>Margin {margin.toFixed(1)}%</span>
        </div>
        {brand.cash < 0 && <div className="text-xs mt-2 font-bold" style={{ color: "#fca5a5" }}>You're in the red. The board is watching.</div>}
      </div>
      <Section title="Ledger" theme={theme}>
        <div className="max-h-96 overflow-y-auto pr-1">
          {[...brand.ledger].reverse().slice(0, 40).map((l, i) => (
            <div key={i} className="flex justify-between gap-2 text-xs mb-1">
              <span style={{ color: "#9ca3af" }}>W{l.week} · {l.label}</span>
              <span className="font-bold whitespace-nowrap" style={{ color: l.amt >= 0 ? "#86efac" : "#fca5a5" }}>{l.amt >= 0 ? "+" : ""}{money(l.amt)}</span>
            </div>
          ))}
          {brand.ledger.length === 0 && <div className="text-xs" style={{ color: "#6b7280" }}>No transactions yet.</div>}
        </div>
      </Section>
    </div>
  );
}

/* ================================================================
   EVENT MODAL
   ================================================================ */
function EventModal({ state, mutateG, theme, canAct }) {
  const bKey = state.activeBrand;
  const brand = state.brands[bKey];
  const ae = brand.activeEvent;
  if (!ae) return null;
  const ev = EVENTS.find((e) => e.id === ae.evId);
  const u = unitById(brand, ae.unitId);
  if (!ev || !u) return null;
  const choose = (c) => mutateG((s) => { applyEventChoice(s, bKey, c); });
  const canAfford = (amt) => brand.cash >= amt;
  const img = (brand.images && brand.images.units[u.id]) || "";
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "#000000bb" }}>
      <div className="w-full max-w-md rounded-2xl p-4" style={{ background: theme.grad, border: "2px solid " + theme.primary }}>
        <div className="text-xs tracking-widest font-bold" style={{ color: ev.positive ? "#86efac" : "#fca5a5", textTransform: "uppercase" }}>{ev.cat} · INCIDENT REPORT</div>
        <div className="flex items-center gap-3 mt-2">
          <Ava src={img} name={u.name} size={56} ring={theme.primary} />
          <div>
            <div className="text-2xl font-black" style={{ ...display, color: "#fff" }}>{ev.name}</div>
            <div className="text-sm font-bold" style={{ color: theme.primary }}>{u.name}</div>
          </div>
        </div>
        <div className="text-sm mt-2" style={{ color: "#d1d5db" }}>{ev.desc}</div>
        {!ev.noBuyout && !ev.positive && (
          <div className="text-xs mt-1" style={{ color: "#9ca3af" }}>💸 Pay-to-avoid available: {money(ev.buyout)}.</div>
        )}
        {canAct ? (
          <div className="flex flex-col gap-2 mt-4">
            {ev.positive && <Btn theme={theme} onClick={() => choose("accept")}>🔥 Ride the Wave</Btn>}
            {ev.special === "renewal" && (<>
              <Btn theme={theme} onClick={() => choose("double")}>💰 Double their money ({money(u.sal * 2)}/yr)</Btn>
              <Btn kind="ghost" disabled={!canAfford(ev.buyout)} onClick={() => choose("buyout")}>🤝 One-time signing bonus ({money(ev.buyout)})</Btn>
              <Btn kind="danger" onClick={() => choose("walk")}>👋 Let them walk (released)</Btn>
            </>)}
            {!ev.positive && ev.special !== "renewal" && (<>
              <Btn theme={theme} onClick={() => choose("accept")}>
                {ev.special === "montreal" ? "😈 Fine. We'll do the screwjob." : ev.special === "turn" ? "🔄 Turn them tonight." : "Accept the consequences."}
              </Btn>
              {!ev.noBuyout && <Btn kind="ghost" disabled={!canAfford(ev.buyout)} onClick={() => choose("buyout")}>💸 Make it go away ({money(ev.buyout)})</Btn>}
            </>)}
            {!ev.noBuyout && !ev.positive && !canAfford(ev.buyout) && <div className="text-xs text-center" style={{ color: "#fca5a5" }}>Not enough cash for the buyout.</div>}
          </div>
        ) : (
          <div className="text-sm mt-4 font-bold text-center" style={{ color: "#9ca3af" }}>Waiting on {state.players[bKey]} to handle this…</div>
        )}
      </div>
    </div>
  );
}

/* ================================================================
   SEASON END
   ================================================================ */
function SeasonEnd({ state, onContinue, onRestart }) {
  const champ = state.champion; const t = THEME[champ.k];
  return (
    <div className="min-h-screen p-4" style={{ background: "radial-gradient(circle at 50% 0%, #1c1c26, #0b0b0f)" }}>
      <div className="max-w-lg mx-auto">
        <div className="text-center rounded-2xl p-6 mb-4" style={{ background: t.grad, border: "2px solid " + t.primary }}>
          <div className="text-xs tracking-widest font-bold" style={{ color: "#9ca3af" }}>SEASON {state.season} CHAMPION BRAND</div>
          <div className="text-4xl font-black mt-2" style={{ ...display, color: t.primary, textShadow: "0 0 30px " + t.glow + "88" }}>{champ.name}</div>
          <div className="text-lg font-bold mt-1" style={{ color: "#fff" }}>{champ.player}</div>
          <div className="text-sm mt-1" style={{ color: "#d1d5db" }}>Brand Power {champ.p.power.toFixed(1)}</div>
        </div>

        <Section title="Final Standings" theme={t}>
          {state.standings.map((r, i) => (
            <div key={r.k} className="rounded-lg p-2 mb-2" style={{ background: THEME[r.k].deep, border: "1px solid " + THEME[r.k].primary + "44" }}>
              <div className="flex justify-between items-center">
                <span className="font-black" style={{ ...display, color: THEME[r.k].primary }}>#{i + 1} {r.name} — {r.player}</span>
                <span className="font-black text-xl" style={{ ...display, color: "#fff" }}>{Math.round(r.p.power)}</span>
              </div>
              <div className="grid grid-cols-5 gap-1 mt-1 text-center text-xs">
                {[["Story", r.p.story], ["Spons", r.p.sponsor], ["PLE", r.p.ple], ["Grow", r.p.growth], ["Profit", r.p.profit]].map(([l, v]) => (
                  <div key={l} className="rounded p-1" style={{ background: "#ffffff0a" }}>
                    <div style={{ color: "#9ca3af" }}>{l}</div>
                    <div className="font-bold" style={{ color: "#fff" }}>{letter(v)}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </Section>

        <Section title="Season Awards" theme={t}>
          {state.awards.map((a, i) => (
            <div key={i} className="flex justify-between text-sm mb-1">
              <span style={{ color: "#d1d5db" }}>🏆 {a.label}</span>
              <span className="font-bold" style={{ color: "#fff" }}>{a.who}</span>
            </div>
          ))}
        </Section>

        {state.history && state.history.length > 0 && (
          <Section title="Past Champions" theme={t}>
            {state.history.slice().reverse().map((h, i) => (
              <div key={i} className="flex justify-between text-sm mb-1">
                <span style={{ color: "#9ca3af" }}>Season {h.season}</span>
                <span className="font-bold" style={{ color: "#fff" }}>{h.champion ? h.champion.name + " (" + h.champion.brand + ")" : "—"}</span>
              </div>
            ))}
          </Section>
        )}

        {onContinue && <Btn theme={t} onClick={onContinue}>▶ Continue — Season {state.season + 1}</Btn>}
        <div className="text-center mt-2">
          <button onClick={onRestart} className="text-xs underline" style={{ color: "#9ca3af" }}>burn it down and start fresh</button>
        </div>
      </div>
    </div>
  );
}

/* ================================================================
   SOCIAL TAB
   ================================================================ */
function TweetCard({ post, state }) {
  const brand = state.brands[post.brand];
  const img = post.unitId ? (brand.images && brand.images.units[post.unitId]) : post.kind === "brand" ? brand.images && brand.images.logo : "";
  const u = post.unitId ? unitById(brand, post.unitId) : null;
  const verified = post.kind === "brand" || (u && (u.pop >= 88 || titleHeldBy(brand, u.id).length > 0));
  return (
    <div className="rounded-xl p-2 mb-2" style={{ background: "#00000044", border: "1px solid #ffffff14" }}>
      <div className="flex gap-2">
        <Ava src={img} name={post.name} size={38} ring={THEME[post.brand].primary} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1 flex-wrap text-xs">
            <span className="font-bold text-sm" style={{ color: "#fff" }}>{post.name}</span>
            {verified && <span style={{ color: "#3b82f6" }}>✓</span>}
            <span style={{ color: "#6b7280" }}>{post.handle} · W{post.week}</span>
            <Pill color={THEME[post.brand].primary} text="#0b0b0f">{BRAND_CONFIG[post.brand].name}</Pill>
            {post.mega && <Pill color="#d4af37" text="#0b0b0f">🌐 BILLIONS+</Pill>}
            {!post.mega && post.viral && <Pill color="#7c2d12" text="#fdba74">🔥 VIRAL</Pill>}
            <Pill color="#1f2937">{post.ai ? "AI" : post.kind === "player" ? "GM" : "Auto"}</Pill>
          </div>
          <div className="text-sm mt-1" style={{ color: "#e5e7eb", lineHeight: 1.4 }}>{post.text}</div>
          <div className="text-xs mt-1" style={{ color: "#6b7280" }}>
            👁 {fmtSoc(post.views)} · ♡ {fmtSoc(post.likes)} · ↻ {fmtSoc(post.rts)} · 💬 {fmtSoc(post.replies || 0)}
          </div>
        </div>
      </div>
    </div>
  );
}

function SocialTab({ state, mutateG, theme, canAct }) {
  const bKey = state.activeBrand;
  const brand = state.brands[bKey];
  const [filter, setFilter] = useState(bKey);
  const [posterId, setPosterId] = useState("brand");
  const [text, setText] = useState("");
  const [aiBusy, setAiBusy] = useState(false);
  const [aiErr, setAiErr] = useState(null);

  const feed = useMemo(() => {
    const all = filter === "all" ? BRAND_KEYS.flatMap((k) => state.brands[k].social) : state.brands[filter].social;
    return [...all].sort((x, y) => y.week - x.week || (y.id > x.id ? 1 : -1)).slice(0, 60);
  }, [state, filter]);

  const stats = useMemo(() => {
    const s = brand.social;
    return {
      total: s.length,
      week: s.filter((p) => p.week === state.week).length,
      viral: s.filter((p) => p.viral || p.mega).length,
      reach: s.reduce((a, p) => a + p.views, 0),
    };
  }, [brand.social, state.week]);

  const estimate = engagement(brand, {});

  const postNow = () => {
    if (!text.trim()) return;
    const isBrand = posterId === "brand";
    const u = isBrand ? null : unitById(brand, posterId);
    const body = text.trim().slice(0, 280);
    mutateG((s) => {
      addPost(s, bKey, {
        kind: isBrand ? "brand" : "player",
        name: isBrand ? BRAND_CONFIG[bKey].name + " (Official)" : u.name,
        handle: isBrand ? handleOf(BRAND_CONFIG[bKey].name) : handleOf(u.name),
        unitId: isBrand ? null : u.id,
        text: body,
        viral: Math.random() < 0.12,
      });
    });
    setText("");
  };

  const aiTakes = async () => {
    setAiBusy(true); setAiErr(null);
    try {
      const takes = await aiSocialTakes(state, bKey);
      mutateG((s) => {
        takes.forEach((t) => {
          const u = s.brands[bKey].units.find((x) => x.name === t.name);
          addPost(s, bKey, { kind: u ? "wrestler" : "pundit", name: t.name, handle: t.handle || handleOf(t.name || "fan"), unitId: u ? u.id : null, text: t.text, ai: true, viral: Math.random() < 0.15 });
        });
      });
    } catch (e) { setAiErr("AI takes failed — try again in a moment."); }
    setAiBusy(false);
  };

  return (
    <div className="px-3 pb-24">
      <div className="grid grid-cols-4 gap-2 mb-3">
        {[["Posts", stats.total], ["This Wk", stats.week], ["Viral", stats.viral], ["Reach", fmtSoc(stats.reach)]].map(([l, v]) => (
          <div key={l} className="rounded-lg p-2 text-center" style={{ background: "#ffffff08", border: "1px solid #ffffff14" }}>
            <div className="text-xs" style={{ color: "#9ca3af" }}>{l}</div>
            <div className="text-base font-black" style={{ ...display, color: theme.primary }}>{v}</div>
          </div>
        ))}
      </div>

      {canAct && (
        <Section title="Create Post" theme={theme} right={<Btn small kind="ghost" disabled={aiBusy} onClick={aiTakes}>{aiBusy ? "🤖 thinking…" : "🤖 AI Takes"}</Btn>}>
          <div className="flex gap-2 flex-wrap items-end mb-2">
            <div className="min-w-0">
              <div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Post as</div>
              <Sel value={posterId} onChange={setPosterId}>
                <option value="brand">{BRAND_CONFIG[bKey].name} (Official)</option>
                {activeUnits(brand).map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
              </Sel>
            </div>
            <div className="text-xs" style={{ color: "#6b7280" }}>Est. reach: {fmtSoc(estimate.views)}</div>
          </div>
          <textarea value={text} onChange={(e) => setText(e.target.value.slice(0, 280))} rows={2}
            placeholder="Speak it into the timeline… (in character pays off)"
            className="w-full rounded p-2 text-sm" style={{ background: "#101016", color: "#eee", border: "1px solid #ffffff22" }} />
          <div className="flex justify-between items-center mt-1">
            <span className="text-xs" style={{ color: "#6b7280" }}>{text.length}/280</span>
            <Btn theme={theme} small disabled={!text.trim()} onClick={postNow}>📣 Post</Btn>
          </div>
          {aiErr && <div className="text-xs mt-1" style={{ color: "#f59e0b" }}>{aiErr}</div>}
        </Section>
      )}

      <div className="flex gap-1 mb-2 overflow-x-auto">
        {[["all", "ALL"], ...BRAND_KEYS.map((k) => [k, BRAND_CONFIG[k].name])].map(([id, label]) => (
          <button key={id} onClick={() => setFilter(id)}
            className="px-3 py-1 rounded-full text-xs font-black whitespace-nowrap"
            style={{ ...display, background: filter === id ? theme.primary : "#ffffff10", color: filter === id ? "#0b0b0f" : "#9ca3af" }}>
            {label}
          </button>
        ))}
      </div>
      {feed.length === 0 && <div className="text-xs" style={{ color: "#6b7280" }}>The timeline is quiet. Run a show.</div>}
      {feed.map((p) => <TweetCard key={p.id} post={p} state={state} />)}
    </div>
  );
}

/* ================================================================
   IMAGES TAB
   ================================================================ */
function ImgSlot({ label, value, onSet, theme, size = 80 }) {
  const [url, setUrl] = useState("");
  return (
    <div className="rounded-lg p-2 mb-2 flex items-center gap-2 flex-wrap" style={{ background: "#00000033", border: "1px solid #ffffff14" }}>
      <Ava src={value} name={label} size={size} ring={theme.primary} />
      <div className="flex-1 min-w-0">
        <div className="text-xs font-bold mb-1" style={{ color: "#d1d5db" }}>{label}</div>
        <div className="flex gap-1 flex-wrap items-center">
          <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="paste image URL…"
            className="rounded px-2 py-1 text-xs flex-1" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22", minWidth: 140 }} />
          <Btn small kind="ghost" disabled={!url.trim()} onClick={() => { onSet(url.trim()); setUrl(""); }}>set</Btn>
          <label className="text-xs px-2 py-1 rounded cursor-pointer font-bold" style={{ background: "#ffffff14", color: "#d1d5db" }}>
            upload
            <input type="file" accept="image/*" className="hidden" style={{ display: "none" }}
              onChange={async (e) => { const f = e.target.files && e.target.files[0]; if (!f) return; try { const d = await fileToThumb(f); onSet(d); } catch {} e.target.value = ""; }} />
          </label>
          {value && <button className="text-xs" style={{ color: "#ef4444" }} onClick={() => onSet("")}>clear</button>}
        </div>
      </div>
    </div>
  );
}

function ImagesTab({ state, mutateG, theme, canAct }) {
  const bKey = state.activeBrand;
  const brand = state.brands[bKey];
  const cfg = BRAND_CONFIG[bKey];
  const img = brand.images || { logo: "", owner: "", owner2: "", gm: "", titles: {}, units: {}, staff: {} };
  const [unitSel, setUnitSel] = useState(brand.units[0]?.id || "");
  const setImg = (path, val) => mutateG((s) => {
    const im = s.brands[bKey].images;
    if (path[0] === "root") im[path[1]] = val;
    else { if (!im[path[0]]) im[path[0]] = {}; im[path[0]][path[1]] = val; }
  });
  const staffPhotoList = (brand.staff || []).filter((st) => st.role !== "Owner" && st.role !== "General Manager");

  if (!canAct) {
    const setOnes = [
      ...(img.logo ? [["Show Logo", img.logo]] : []),
      ...(img.owner ? [[cfg.owner + " (Owner)", img.owner]] : []),
      ...(img.gm ? [[cfg.gm + " (GM)", img.gm]] : []),
      ...brand.titles.filter((t) => img.titles[t.id]).map((t) => [t.name, img.titles[t.id]]),
      ...brand.units.filter((u) => img.units[u.id]).map((u) => [u.name, img.units[u.id]]),
    ];
    return (
      <div className="px-3 pb-24">
        <Section title={cfg.name + " Gallery"} theme={theme}>
          {setOnes.length === 0 && <div className="text-xs" style={{ color: "#6b7280" }}>No images set yet.</div>}
          <div className="flex flex-wrap gap-3">
            {setOnes.map(([n, src], i) => (
              <div key={i} className="text-center">
                <Ava src={src} name={n} size={88} ring={theme.primary} />
                <div className="text-xs mt-1 max-w-24 truncate" style={{ color: "#9ca3af" }}>{n}</div>
              </div>
            ))}
          </div>
        </Section>
      </div>
    );
  }

  const selUnit = unitById(brand, unitSel);
  return (
    <div className="px-3 pb-24">
      <div className="text-xs mb-2 rounded-lg p-2" style={{ color: "#9ca3af", background: "#ffffff08", border: "1px solid #ffffff14" }}>
        Paste image URLs when you can — they cost nothing. Uploads are auto-shrunk to small thumbnails so the save stays light.
      </div>
      <Section title="Brand Identity" theme={theme}>
        <ImgSlot label={"Show Logo — " + cfg.show} value={img.logo} onSet={(v) => setImg(["root", "logo"], v)} theme={theme} />
        <ImgSlot label={"Owner — " + cfg.owner} value={img.owner} onSet={(v) => setImg(["root", "owner"], v)} theme={theme} />
        {cfg.owner2 && <ImgSlot label={"Owner — " + cfg.owner2} value={img.owner2 || ""} onSet={(v) => setImg(["root", "owner2"], v)} theme={theme} />}
        <ImgSlot label={"General Manager — " + cfg.gm} value={img.gm} onSet={(v) => setImg(["root", "gm"], v)} theme={theme} />
      </Section>

      <Section title="Championship Belts" theme={theme}>
        {brand.titles.map((t) => (
          <ImgSlot key={t.id} label={t.name} value={img.titles[t.id] || ""} onSet={(v) => setImg(["titles", t.id], v)} theme={theme} />
        ))}
      </Section>

      <Section title="Wrestlers" theme={theme}>
        <div className="mb-2">
          <Sel value={unitSel} onChange={setUnitSel} w="100%">
            {brand.units.map((u) => <option key={u.id} value={u.id}>{u.name}{img.units[u.id] ? " ✓" : ""}</option>)}
          </Sel>
        </div>
        {selUnit && <ImgSlot label={selUnit.name} value={img.units[selUnit.id] || ""} onSet={(v) => setImg(["units", selUnit.id], v)} theme={theme} />}
        <div className="text-xs" style={{ color: "#6b7280" }}>{Object.values(img.units).filter(Boolean).length} of {brand.units.length} wrestlers have photos.</div>
      </Section>

      <Section title="Staff & Podcast Hosts" theme={theme}>
        {staffPhotoList.length === 0 && <div className="text-xs" style={{ color: "#6b7280" }}>No hireable staff yet — add some on the Staff tab.</div>}
        {staffPhotoList.map((st) => (
          <ImgSlot key={st.id} label={st.name + " — " + st.role} value={(img.staff && img.staff[st.id]) || ""} onSet={(v) => setImg(["staff", st.id], v)} theme={theme} />
        ))}
      </Section>
    </div>
  );
}

/* ================================================================
   POWER RANKINGS TAB
   ================================================================ */
function RanksTab({ state, theme }) {
  const bKey = state.activeBrand;
  const brand = state.brands[bKey];
  const ranked = brandRankings(brand);
  const img = brand.images || { units: {} };
  const universe = BRAND_KEYS.flatMap((k) => brandRankings(state.brands[k]).slice(0, 8).map((u) => ({ u, k }))).sort((a, b) => powerScore(b.u) - powerScore(a.u)).slice(0, 10);
  return (
    <div className="px-3 pb-24">
      <Section title="🌍 Universe Top 10" theme={theme}>
        {universe.map(({ u, k }, i) => (
          <div key={u.id} className="flex items-center gap-2 text-sm mb-1">
            <span className="w-6 text-right font-black" style={{ ...display, color: i < 3 ? "#d4af37" : "#9ca3af" }}>{i + 1}</span>
            <Ava src={state.brands[k].images?.units[u.id]} name={u.name} size={24} ring={THEME[k].primary} />
            <span className="font-bold flex-1 truncate" style={{ color: "#fff" }}>{u.name}</span>
            <Pill color={THEME[k].primary} text="#0b0b0f">{BRAND_CONFIG[k].name}</Pill>
            <span className="text-xs" style={{ color: "#9ca3af" }}>{Math.round(powerScore(u))}</span>
          </div>
        ))}
      </Section>

      <Section title={BRAND_CONFIG[bKey].name + " Power Rankings"} theme={theme}>
        <div className="text-xs mb-2" style={{ color: "#9ca3af" }}>
          Driven by momentum, popularity, recent match quality, wins/losses, win streaks, and main-event exposure.
        </div>
        {ranked.slice(0, 25).map((u, i) => {
          const rank = i + 1;
          const prev = brand.prevRanks ? brand.prevRanks[u.id] : null;
          const mv = prev ? prev - rank : null;
          const last5 = (u.form || []).slice(-5);
          return (
            <div key={u.id} className="rounded-lg p-2 mb-1 flex items-center gap-2" style={{ background: "#00000033", border: "1px solid #ffffff14" }}>
              <span className="w-6 text-right text-lg font-black" style={{ ...display, color: rank <= 3 ? theme.primary : "#9ca3af" }}>{rank}</span>
              <span className="w-8 text-xs font-bold" style={{ color: mv === null ? "#6b7280" : mv > 0 ? "#22c55e" : mv < 0 ? "#ef4444" : "#6b7280" }}>
                {mv === null ? "NEW" : mv > 0 ? "▲" + mv : mv < 0 ? "▼" + Math.abs(mv) : "—"}
              </span>
              <Ava src={img.units[u.id]} name={u.name} size={28} />
              <div className="flex-1 min-w-0">
                <span className="text-sm font-bold" style={{ color: "#fff" }}>{u.name}</span>
                <span className="ml-1"><AlPill al={u.al} /></span>
                {(() => { const ht = titleHeldBy(brand, u.id); if (!ht.length) return null; return <span className="ml-1"><Pill color="#d4af37" text="#0b0b0f">🏆 CHAMP</Pill></span>; })()}
              </div>
              <div className="flex gap-1">
                {last5.length === 0 && <span className="text-xs" style={{ color: "#6b7280" }}>unbooked</span>}
                {last5.map((f, j) => (
                  <span key={j} className="w-4 h-4 rounded-full text-center font-black" style={{ background: f.win ? "#14532d" : "#7f1d1d", color: f.win ? "#86efac" : "#fca5a5", fontSize: 9, lineHeight: "1rem" }}>{f.win ? "W" : "L"}</span>
                ))}
              </div>
              <span className="text-xs w-8 text-right" style={{ color: "#9ca3af" }}>{u.w}–{u.l}</span>
            </div>
          );
        })}
      </Section>
    </div>
  );
}

/* ================================================================
   TRADE CENTER TAB
   ================================================================ */
function TradesTab({ state, mutateG, theme, canAct }) {
  const bKey = state.activeBrand;
  const brand = state.brands[bKey];
  const others = BRAND_KEYS.filter((k) => k !== bKey);
  const [partner, setPartner] = useState(others[0]);
  const [give, setGive] = useState([]);
  const [get, setGet] = useState([]);
  const [giveCashM, setGiveCashM] = useState(0);
  const [getCashM, setGetCashM] = useState(0);

  const pBrand = state.brands[partner];
  const toggle = (list, setList, id) => setList(list.includes(id) ? list.filter((x) => x !== id) : list.length >= 3 ? list : [...list, id]);
  const draft = { from: bKey, to: partner, fromUnits: give, toUnits: get, fromCash: Math.round(giveCashM * 1e6), toCash: Math.round(getCashM * 1e6) };
  const capErr = tradePayrollCheck(state, draft);
  const empty = !give.length && !get.length && !draft.fromCash && !draft.toCash;
  const pending = state.trades.filter((t) => t.status === "pending" && (t.from === bKey || t.to === bKey));
  const history = state.trades.filter((t) => t.status !== "pending").slice(-8).reverse();
  const nameList = (k, ids) => ids.map((id) => unitById(state.brands[k], id)?.name || "?").join(", ");

  return (
    <div className="px-3 pb-24">
      <Section title="Pending Offers" theme={theme}>
        {pending.length === 0 && <div className="text-xs" style={{ color: "#6b7280" }}>No live offers on the table.</div>}
        {pending.map((t) => {
          const incoming = t.to === bKey;
          const err = tradePayrollCheck(state, t);
          return (
            <div key={t.id} className="rounded-lg p-2 mb-2" style={{ background: "#00000044", border: "1px solid " + (incoming ? "#16a34a55" : "#ffffff22") }}>
              <div className="text-xs font-bold mb-1" style={{ color: incoming ? "#86efac" : "#9ca3af" }}>
                {incoming ? "📥 INCOMING from " + BRAND_CONFIG[t.from].name : "📤 SENT to " + BRAND_CONFIG[t.to].name}
              </div>
              <div className="text-sm" style={{ color: "#d1d5db" }}>
                <b style={{ color: THEME[t.from].primary }}>{BRAND_CONFIG[t.from].name}</b> sends: {nameList(t.from, t.fromUnits) || "—"}{t.fromCash ? " + " + money(t.fromCash) : ""}
              </div>
              <div className="text-sm" style={{ color: "#d1d5db" }}>
                <b style={{ color: THEME[t.to].primary }}>{BRAND_CONFIG[t.to].name}</b> sends: {nameList(t.to, t.toUnits) || "—"}{t.toCash ? " + " + money(t.toCash) : ""}
              </div>
              {err && <div className="text-xs mt-1" style={{ color: "#f59e0b" }}>⚠ {err}</div>}
              {canAct && incoming && (
                <div className="flex gap-2 mt-2">
                  <Btn small theme={theme} disabled={!!err} onClick={() => mutateG((s) => acceptTrade(s, t.id))}>✓ Accept</Btn>
                  <Btn small kind="danger" onClick={() => mutateG((s) => rejectTrade(s, t.id))}>✕ Reject</Btn>
                </div>
              )}
              {canAct && !incoming && (
                <div className="mt-2"><Btn small kind="ghost" onClick={() => mutateG((s) => { s.trades = s.trades.filter((x) => x.id !== t.id); })}>withdraw offer</Btn></div>
              )}
              {!canAct && incoming && <div className="text-xs mt-1" style={{ color: "#9ca3af" }}>Waiting on {state.players[bKey]} to respond.</div>}
            </div>
          );
        })}
      </Section>

      {canAct && (
        <Section title="Build a Trade — up to 3 superstars + cash each way" theme={theme}>
          <div className="mb-2">
            <Sel value={partner} onChange={(v) => { setPartner(v); setGet([]); }}>
              {others.map((k) => <option key={k} value={k}>{BRAND_CONFIG[k].name}</option>)}
            </Sel>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div className="rounded-lg p-2" style={{ background: "#00000033", border: "1px solid #ffffff14" }}>
              <div className="text-xs font-black mb-1" style={{ ...display, color: theme.primary }}>YOU SEND ({give.length}/3)</div>
              <div className="flex flex-wrap gap-1 mb-2" style={{ maxHeight: 160, overflowY: "auto" }}>
                {brand.units.filter((u) => !u.guest).sort((a, b) => b.ovr - a.ovr).map((u) => (
                  <button key={u.id} onClick={() => toggle(give, setGive, u.id)}
                    className="text-xs px-2 py-1 rounded-full"
                    style={{ background: give.includes(u.id) ? theme.primary : "#ffffff10", color: give.includes(u.id) ? "#0b0b0f" : "#d1d5db" }}>
                    {u.name} {u.ovr}{u.wants === "trade" ? " 📤" : ""}
                  </button>
                ))}
              </div>
              <label className="text-xs" style={{ color: "#9ca3af" }}>+ cash $M
                <input type="number" min="0" step="0.5" value={giveCashM} onChange={(e) => setGiveCashM(Math.max(0, parseFloat(e.target.value || "0")))}
                  className="w-20 ml-1 rounded px-1 py-1 text-sm text-center" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22" }} />
              </label>
            </div>
            <div className="rounded-lg p-2" style={{ background: "#00000033", border: "1px solid #ffffff14" }}>
              <div className="text-xs font-black mb-1" style={{ ...display, color: THEME[partner].primary }}>YOU GET ({get.length}/3)</div>
              <div className="flex flex-wrap gap-1 mb-2" style={{ maxHeight: 160, overflowY: "auto" }}>
                {pBrand.units.filter((u) => !u.guest).sort((a, b) => b.ovr - a.ovr).map((u) => (
                  <button key={u.id} onClick={() => toggle(get, setGet, u.id)}
                    className="text-xs px-2 py-1 rounded-full"
                    style={{ background: get.includes(u.id) ? THEME[partner].primary : "#ffffff10", color: get.includes(u.id) ? "#0b0b0f" : "#d1d5db" }}>
                    {u.name} {u.ovr}{u.wants === "trade" ? " 📤" : ""}
                  </button>
                ))}
              </div>
              <label className="text-xs" style={{ color: "#9ca3af" }}>+ cash $M
                <input type="number" min="0" step="0.5" value={getCashM} onChange={(e) => setGetCashM(Math.max(0, parseFloat(e.target.value || "0")))}
                  className="w-20 ml-1 rounded px-1 py-1 text-sm text-center" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22" }} />
              </label>
            </div>
          </div>
          {capErr && !empty && <div className="text-xs mt-2" style={{ color: "#f59e0b" }}>⚠ {capErr}</div>}
          {draft.fromCash > brand.cash && <div className="text-xs mt-1" style={{ color: "#ef4444" }}>You don't have that much cash.</div>}
          <div className="mt-2">
            <Btn theme={theme} small disabled={empty || !!capErr || draft.fromCash > brand.cash}
              onClick={() => {
                const t = { ...draft, id: "t" + Date.now(), status: "pending", week: state.week };
                mutateG((s) => { s.trades.push(t); pushNews(s, t.to, `📨 Trade offer from ${BRAND_CONFIG[bKey].name} — check the Trade Center.`, "info"); });
                setGive([]); setGet([]); setGiveCashM(0); setGetCashM(0);
              }}>
              Propose Trade to {BRAND_CONFIG[partner].name}
            </Btn>
          </div>
          <div className="text-xs mt-2" style={{ color: "#6b7280" }}>The other GM accepts or rejects from their side. Titles are vacated on departure.</div>
        </Section>
      )}

      <Section title="Trade History" theme={theme}>
        {history.length === 0 && <div className="text-xs" style={{ color: "#6b7280" }}>No completed trades.</div>}
        {history.map((t) => (
          <div key={t.id} className="text-xs mb-1" style={{ color: t.status === "accepted" ? "#86efac" : "#9ca3af" }}>
            W{t.week}: {BRAND_CONFIG[t.from].name} ⇄ {BRAND_CONFIG[t.to].name} — {t.status.toUpperCase()}{t.reason ? " (" + t.reason + ")" : ""}
          </div>
        ))}
      </Section>
    </div>
  );
}

/* ================================================================
   FREE AGENCY TAB
   ================================================================ */
function FATab({ state, mutateG, theme, canAct }) {
  const bKey = state.activeBrand;
  const brand = state.brands[bKey];
  const cfg = BRAND_CONFIG[bKey];
  const [offers, setOffers] = useState({}); // faId -> {m, yrs}
  const [toast, setToast] = useState(null);
  const space = cfg.cap - capUsed(brand);
  const setOff = (id, k, v) => setOffers((p) => ({ ...p, [id]: { m: 0, yrs: 2, ...(p[id] || {}), [k]: v } }));
  return (
    <div className="px-3 pb-24">
      <Section title="Free Agent Market" theme={theme} right={<Pill color={theme.primary} text="#0b0b0f">{money(space)} cap space</Pill>}>
        <div className="text-xs mb-2" style={{ color: "#9ca3af" }}>
          The pool starts empty by design — released superstars, expired contracts, and contract-dispute walkouts land here.
        </div>
        {toast && <div className="rounded-lg p-2 mb-2 text-xs font-bold" style={{ background: toast.ok ? "#14532d55" : "#7f1d1d55", color: toast.ok ? "#86efac" : "#fca5a5" }}>{toast.msg}</div>}
        {state.freeAgents.length === 0 && <div className="text-sm" style={{ color: "#6b7280" }}>Nobody on the open market right now.</div>}
        {state.freeAgents.map((u) => {
          const off = offers[u.id] || {};
          const yrs = off.yrs || 2;
          const ask = Math.round(faAsk(u) * (yrs >= 3 ? 0.92 : yrs === 2 ? 1 : 1.08));
          const offerM = off.m || ask / 1e6;
          const offer = Math.round(offerM * 1e6);
          const cool = (u.cool && u.cool[bKey]) || 0;
          const coolLeft = cool - state.week;
          const chance = offer >= ask ? 1 : clamp((offer / ask - 0.78) * 4.2, 0, 0.95);
          const overSpace = offer > space;
          return (
            <div key={u.id} className="rounded-lg p-2 mb-2" style={{ background: "#00000033", border: "1px solid #ffffff14" }}>
              <div className="flex justify-between items-center gap-2 flex-wrap">
                <div className="flex items-center gap-2 min-w-0">
                  <Ava name={u.name} size={34} />
                  <div className="min-w-0">
                    <span className="text-sm font-bold" style={{ color: "#fff" }}>{u.name}</span>
                    <span className="ml-2"><AlPill al={u.al} /></span>
                    <div className="text-xs" style={{ color: "#9ca3af" }}>{u.div} · OVR {u.ovr} · RS {u.rs || "?"} · PS {u.ps || "?"} · pop {Math.round(u.pop)}</div>
                  </div>
                </div>
                <div className="text-xs text-right" style={{ color: "#d1d5db" }}>
                  Asking <b style={{ color: theme.primary }}>{money(ask)}/yr</b>
                </div>
              </div>
              {canAct && (
                <div className="flex flex-wrap gap-2 mt-2 items-end">
                  <label className="text-xs" style={{ color: "#9ca3af" }}>Offer $M/yr
                    <input type="number" step="0.1" min="0.1" value={Number(offerM.toFixed(2))}
                      onChange={(e) => setOff(u.id, "m", Math.max(0.1, parseFloat(e.target.value || "0.1")))}
                      className="w-24 ml-1 rounded px-1 py-1 text-sm text-center" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22" }} />
                  </label>
                  <label className="text-xs" style={{ color: "#9ca3af" }}>Years
                    <select value={yrs} onChange={(e) => setOff(u.id, "yrs", parseInt(e.target.value, 10))}
                      className="ml-1 rounded px-1 py-1 text-sm" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22" }}>
                      <option value={1}>1</option><option value={2}>2</option><option value={3}>3</option>
                    </select>
                  </label>
                  <div className="text-xs" style={{ color: chance >= 0.9 ? "#86efac" : chance >= 0.5 ? "#fde68a" : "#fca5a5" }}>
                    {coolLeft > 0 ? "❄ Camp won't talk to you for " + coolLeft + " wk" : Math.round(chance * 100) + "% chance to accept"}
                  </div>
                  <Btn small theme={theme} disabled={coolLeft > 0 || overSpace}
                    onClick={() => {
                      const success = Math.random() < chance;
                      mutateG((s) => signFreeAgent(s, bKey, u.id, offer, yrs, success));
                      setToast(success ? { ok: true, msg: `✍️ ${u.name} SIGNED — ${money(offer)}/yr × ${yrs}.` } : { ok: false, msg: `${u.name} turned you down. Their ask just went up.` });
                    }}>
                    Offer {money(offer)} × {yrs}yr
                  </Btn>
                  {overSpace && <span className="text-xs" style={{ color: "#ef4444" }}>over cap space</span>}
                </div>
              )}
            </div>
          );
        })}
      </Section>
    </div>
  );
}

/* ================================================================
   STAFF + PODCAST TAB
   ================================================================ */
function StaffTab({ state, mutateG, theme, canAct }) {
  const bKey = state.activeBrand;
  const brand = state.brands[bKey];
  const cfg = BRAND_CONFIG[bKey];
  const [nm, setNm] = useState("");
  const [role, setRole] = useState(STAFF_ROLES[0]);
  const [podText, setPodText] = useState("");
  const [podTarget, setPodTarget] = useState("show");
  const [podBusy, setPodBusy] = useState(false);
  const [podErr, setPodErr] = useState(null);
  const [podName, setPodName] = useState("");
  const [podTone, setPodTone] = useState(PODCAST_TONES[0]);
  const [podLength, setPodLength] = useState("Full Episode (~10 min)");
  const [podNotes, setPodNotes] = useState("");
  const [podGenBusy, setPodGenBusy] = useState(false);
  const { speak: speakPodcast, stop: stopPodcast, speaking: podSpeaking, status: podSpeakStatus } = usePodcastSpeech();
  const staff = brand.staff || [];
  const hosts = staff.filter((s) => s.role === "Podcast Host");
  const imgs = (brand.images && brand.images.staff) || {};
  const groups = ["Owner", "General Manager", "Commentator", "Producer", "Ring Announcer", "Referee", "Podcast Host"];
  const aired = brand.podWeek === state.week;
  const liveFeuds = brand.feuds.filter((f) => !f.done);
  const aiReady = hasAnthropicKey();

  const airPodcast = async () => {
    if (podText.trim().length < 120) { setPodErr("Paste a real segment — at least a couple paragraphs."); return; }
    setPodBusy(true); setPodErr(null);
    try {
      const g = await gradePodcastAI(brand, { podName: (brand.podcast && brand.podcast.name) || "The Podcast", brandName: cfg.name }, podText);
      mutateG((s) => applyPodcast(s, bKey, podTarget, g, podText));
      setPodText("");
    } catch (e) { setPodErr("Grading failed (network or parse error) — try again."); }
    setPodBusy(false);
  };

  const generateEpisode = async () => {
    setPodGenBusy(true); setPodErr(null);
    try {
      const script = await generatePodcastEpisodeAI(state, brand, hosts, {
        episodeTitle: `${cfg.name} Week ${state.week}`,
        tone: podTone,
        length: podLength,
        userNotes: podNotes,
        targetFeudId: podTarget,
        mainStory: podTarget !== "show" ? liveFeuds.find((f) => f.id === podTarget)?.label : "",
      });
      setPodText(script);
    } catch (e) {
      setPodErr(e.message || "Episode generation failed — check your API key and try again.");
    }
    setPodGenBusy(false);
  };

  return (
    <div className="px-3 pb-24">
      <Section title={"🎙 " + ((brand.podcast && brand.podcast.name) || "Podcast — locked")} theme={theme}>
        {!brand.podcast && hosts.length === 0 && (
          <div className="text-xs" style={{ color: "#9ca3af" }}>Hire a <b>Podcast Host</b> below to unlock the brand podcast.</div>
        )}
        {!brand.podcast && hosts.length > 0 && canAct && (
          <div className="flex gap-2 items-end flex-wrap">
            <input value={podName} onChange={(e) => setPodName(e.target.value)} placeholder="Podcast name…"
              className="rounded px-2 py-2 text-sm" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22" }} />
            <Btn small theme={theme} disabled={!podName.trim()} onClick={() => { const n = podName.trim(); mutateG((s) => { s.brands[bKey].podcast = { name: n }; pushNews(s, bKey, `🎙 ${n} is LIVE — the ${cfg.name} podcast launches.`, "good"); }); setPodName(""); }}>Launch Podcast</Btn>
          </div>
        )}
        {brand.podcast && (<>
          <div className="text-xs mb-2" style={{ color: "#9ca3af" }}>
            Deep-dive episode — emotion, psychology, locker room & business reads. Hosts: <b style={{ color: "#fff" }}>{hosts.map((h) => h.name).join(" & ") || "none"}</b>.
            Generate or paste a script, then <b style={{ color: "#fff" }}>▶ Play</b> for smooth neural voices (same Edge TTS as the main game). Air once per week for <b style={{ color: "#22c55e" }}>+$200K</b>.
          </div>
          {canAct ? (<>
            {!aiReady && (
              <div className="rounded-lg p-2 mb-2 text-xs" style={{ background: "#1a1020", border: "1px solid #b026ff44", color: "#d8b4fe" }}>
                <b>AI episode generation needs an Anthropic API key.</b>
                <ol className="mt-1 ml-4 list-decimal space-y-0.5" style={{ color: "#c4b5fd" }}>
                  <li><code className="text-white">cd brand-wars-gm &amp;&amp; cp .env.example .env</code></li>
                  <li>Edit <code className="text-white">.env</code> — set <code className="text-white">VITE_ANTHROPIC_API_KEY=sk-ant-…</code></li>
                  <li>Restart the dev server: <code className="text-white">npm run dev</code></li>
                </ol>
              </div>
            )}
            <div className="flex flex-wrap gap-2 mb-2 items-end">
              <div>
                <div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Tone</div>
                <Sel value={podTone} onChange={setPodTone}>
                  {PODCAST_TONES.map((t) => <option key={t} value={t}>{t}</option>)}
                </Sel>
              </div>
              <div>
                <div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Length</div>
                <Sel value={podLength} onChange={setPodLength}>
                  {PODCAST_LENGTHS.map((t) => <option key={t} value={t}>{t}</option>)}
                </Sel>
              </div>
              <Btn theme={theme} small disabled={!aiReady || podGenBusy || podSpeaking || hosts.length === 0} onClick={generateEpisode}>
                {podGenBusy ? "✨ Writing episode…" : "✨ Generate Unfiltered Episode"}
              </Btn>
            </div>
            <input value={podNotes} onChange={(e) => setPodNotes(e.target.value)} placeholder="Optional notes — tweets, morale, characters to focus on…"
              className="w-full rounded px-2 py-2 text-sm mb-2" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22" }} />
            <textarea value={podText} onChange={(e) => setPodText(e.target.value)} rows={8}
              placeholder={(hosts[0] ? `${hosts[0].name}:\n"Welcome back to ${brand.podcast.name}…"` : "Generate an episode or paste a transcript…")}
              className="w-full rounded p-3 text-sm" style={{ background: "#101016", color: "#eee", border: "1px solid " + theme.primary + "44" }} />
            <div className="flex flex-wrap gap-2 mt-2 items-end">
              <div>
                <div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Episode hypes…</div>
                <Sel value={podTarget} onChange={setPodTarget}>
                  <option value="show">📺 The next {cfg.show}</option>
                  {liveFeuds.map((f) => <option key={f.id} value={f.id}>🔥 {f.label}</option>)}
                </Sel>
              </div>
              <Btn theme={theme} small disabled={podSpeaking || !podText.trim()} onClick={() => speakPodcast(podText, hosts)}>
                {podSpeaking ? "▶ Playing…" : "▶ Play Episode"}
              </Btn>
              {podSpeaking && <Btn theme={theme} small onClick={stopPodcast}>⏹ Stop</Btn>}
              <Btn theme={theme} small disabled={podBusy || aired || hosts.length === 0 || podSpeaking} onClick={airPodcast}>
                {aired ? "✓ Aired this week" : podBusy ? "⏳ Critics listening…" : "🎙 Air the Episode"}
              </Btn>
            </div>
            {podSpeakStatus && <div className="text-xs mt-1" style={{ color: podSpeaking ? theme.primary : "#9ca3af" }}>{podSpeakStatus}</div>}
            {podErr && <div className="text-xs mt-1" style={{ color: "#f59e0b" }}>{podErr}</div>}
          </>) : <div className="text-xs" style={{ color: "#9ca3af" }}>Only {state.players[bKey]} can air episodes.</div>}
          {brand.lastPod && (
            <div className="rounded-lg p-2 mt-2" style={{ background: "#00000044", border: "1px solid #ffffff14" }}>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-2xl font-black" style={{ ...display, color: brand.lastPod.score >= 75 ? "#22c55e" : brand.lastPod.score >= 55 ? "#d4af37" : "#ef4444" }}>{brand.lastPod.score}</span>
                <span className="text-xs italic" style={{ color: "#d1d5db" }}>"{brand.lastPod.verdict}"</span>
                {brand.lastPod.transcript && (
                  <Btn theme={theme} small disabled={podSpeaking} onClick={() => speakPodcast(brand.lastPod.transcript, hosts)}>
                    ▶ Replay
                  </Btn>
                )}
              </div>
              {(brand.lastPod.highlights || []).map((h, i) => <div key={i} className="text-xs" style={{ color: "#86efac" }}>+ {h}</div>)}
            </div>
          )}
        </>)}
      </Section>

      <Section title="Staff Directory" theme={theme}>
        {groups.map((g) => {
          const members = staff.filter((s) => s.role === g);
          if (!members.length) return null;
          return (
            <div key={g} className="mb-2">
              <div className="text-xs font-black mb-1" style={{ ...display, color: "#9ca3af" }}>{g}</div>
              {members.map((s) => (
                <div key={s.id} className="flex items-center gap-2 mb-1">
                  <Ava src={imgs[s.id]} name={s.name} size={48} ring={s.locked ? theme.primary : undefined} />
                  {canAct && !s.locked ? (
                    <input defaultValue={s.name}
                      onBlur={(e) => { const v = e.target.value.trim(); if (v && v !== s.name) mutateG((st) => { const x = (st.brands[bKey].staff || []).find((y) => y.id === s.id); if (x) x.name = v; }); }}
                      className="rounded px-2 py-1 text-sm flex-1" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22" }} />
                  ) : <span className="text-sm font-bold flex-1" style={{ color: "#fff" }}>{s.name}{s.locked ? " 🔒" : ""}</span>}
                  {canAct && !s.locked && (
                    <button className="text-xs" style={{ color: "#ef4444" }}
                      onClick={() => mutateG((st) => { st.brands[bKey].staff = (st.brands[bKey].staff || []).filter((y) => y.id !== s.id); })}>release</button>
                  )}
                </div>
              ))}
            </div>
          );
        })}
        {canAct && (
          <div className="flex flex-wrap gap-2 items-end mt-2 pt-2" style={{ borderTop: "1px solid #ffffff14" }}>
            <input value={nm} onChange={(e) => setNm(e.target.value)} placeholder="New staff name…"
              className="rounded px-2 py-2 text-sm" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22" }} />
            <Sel value={role} onChange={setRole}>{STAFF_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}</Sel>
            <Btn small theme={theme} disabled={!nm.trim()}
              onClick={() => { const n = nm.trim(); const r = role; mutateG((s) => { (s.brands[bKey].staff = s.brands[bKey].staff || []).push({ id: "st" + Date.now(), name: n, role: r }); }); setNm(""); }}>
              Hire Staff
            </Btn>
          </div>
        )}
        <div className="text-xs mt-2" style={{ color: "#6b7280" }}>Owners and GMs are permanent fixtures — everyone else is yours to shape.</div>
      </Section>
    </div>
  );
}

/* ================================================================
   TRAINING TAB
   ================================================================ */
function TrainTab({ state, mutateG, theme, canAct }) {
  const bKey = state.activeBrand;
  const brand = state.brands[bKey];
  const [unitId, setUnitId] = useState("");
  const [skill, setSkill] = useState("rs");
  const [toast, setToast] = useState(null);
  const u = unitId ? unitById(brand, unitId) : null;
  const onCd = u && (u.trainCd || 0) > state.week;
  const trainable = brand.units.filter((x) => !x.status && !x.guest && x.deb !== false);
  return (
    <div className="px-3 pb-24">
      <Section title="🏋️ Performance Training" theme={theme}>
        <div className="text-xs mb-2" style={{ color: "#9ca3af" }}>
          Pay for camps that raise <b style={{ color: "#fff" }}>Ring Skill</b> or <b style={{ color: "#fff" }}>Promo Skill</b>. Higher tiers risk backfiring. 3-week cooldown per wrestler, and camp adds fatigue.
        </div>
        {toast && <div className="rounded-lg p-2 mb-2 text-xs font-bold" style={{ background: toast.ok ? "#14532d55" : "#7f1d1d55", color: toast.ok ? "#86efac" : "#fca5a5" }}>{toast.msg}</div>}
        {canAct ? (<>
          <div className="flex flex-wrap gap-2 items-end mb-2">
            <div className="min-w-0">
              <div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Wrestler</div>
              <Sel value={unitId} onChange={setUnitId}>
                <option value="">— pick —</option>
                {trainable.map((x) => <option key={x.id} value={x.id}>{x.name} (RS {x.rs || "?"} · PS {x.ps || "?"})</option>)}
              </Sel>
            </div>
            <div>
              <div className="text-xs mb-1" style={{ color: "#9ca3af" }}>Skill</div>
              <Sel value={skill} onChange={setSkill}>
                <option value="rs">🤼 Ring Skill</option>
                <option value="ps">🎤 Promo Skill</option>
              </Sel>
            </div>
            {u && <div className="text-xs" style={{ color: "#d1d5db" }}>Current: <b style={{ color: "#fff" }}>{skill === "rs" ? (u.rs || "?") : (u.ps || "?")}</b>{onCd ? " · on cooldown until W" + u.trainCd : ""}</div>}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {TRAIN_TIERS.map((t) => (
              <div key={t.id} className="rounded-lg p-2" style={{ background: "#00000044", border: "1px solid #ffffff14" }}>
                <div className="text-sm font-black" style={{ ...display, color: theme.primary }}>{t.n}</div>
                <div className="text-xs" style={{ color: "#9ca3af" }}>{t.desc}</div>
                <div className="text-xs mt-1" style={{ color: "#d1d5db" }}>
                  {money(t.cost)} · success +{t.min}–{t.max} · <span style={{ color: "#fca5a5" }}>{Math.round(t.fail * 100)}% backfire −{t.failMin}–{t.failMax}</span>
                </div>
                <div className="mt-2">
                  <Btn small theme={theme} disabled={!u || onCd || brand.cash < t.cost}
                    onClick={() => {
                      const fail = Math.random() < t.fail;
                      const delta = fail ? -(t.failMin + Math.floor(Math.random() * (t.failMax - t.failMin + 1))) : t.min + Math.floor(Math.random() * (t.max - t.min + 1));
                      const nm = u.name;
                      mutateG((s) => trainUnit(s, bKey, u.id, skill, delta, t.cost, t.n));
                      setToast(fail
                        ? { ok: false, msg: `📉 ${t.n} BACKFIRED — ${nm} picked up bad habits (${delta}).` }
                        : { ok: true, msg: `📈 ${nm} gained +${delta} ${skill === "rs" ? "Ring Skill" : "Promo Skill"}.` });
                    }}>
                    Enroll
                  </Btn>
                </div>
              </div>
            ))}
          </div>
          {u && brand.cash < TRAIN_TIERS[0].cost && <div className="text-xs mt-2" style={{ color: "#fca5a5" }}>Not enough cash for even a basic camp.</div>}
        </>) : <div className="text-xs" style={{ color: "#9ca3af" }}>Only {state.players[bKey]} can run training camps.</div>}
      </Section>

      <Section title="Roster Skills" theme={theme}>
        {[...trainable].sort((a, b) => (b.rs || 0) - (a.rs || 0)).slice(0, 30).map((x) => (
          <div key={x.id} className="flex items-center gap-2 text-xs mb-1">
            <span className="flex-1 truncate font-bold" style={{ color: "#fff" }}>{x.name}</span>
            <span style={{ color: "#9ca3af" }}>RS</span><div className="w-20"><Bar pct={x.rs || 50} color="#3b82f6" h={5} /></div><span style={{ color: "#d1d5db", width: 20 }}>{x.rs || "?"}</span>
            <span style={{ color: "#9ca3af" }}>PS</span><div className="w-20"><Bar pct={x.ps || 50} color="#a855f7" h={5} /></div><span style={{ color: "#d1d5db", width: 20 }}>{x.ps || "?"}</span>
          </div>
        ))}
      </Section>
    </div>
  );
}

/* ================================================================
   CALENDAR TAB
   ================================================================ */
function CalendarTab({ state, mutateL, mutateG, theme, canAct, mode, me }) {
  const cal = state.calendar || [];
  const dayOf = { wcw: "MON", nxt: "THU", sd: "FRI" };
  const order = ["wcw", "nxt", "sd"];
  const curM = monthIdxOf(state.week);
  const canTouchBrand = (k) => canAct !== false && (mode !== "online" || !me || me.brand === k);
  const evOf = (c, k) => (c.events ? c.events[k] : null) || { on: c.host === k || !!c.all, ple: c.ple, arena: "", location: "", theme: "", stadium: !!c.stadium };
  const setEv = (mi, k, patch, global_) => {
    const fn = (s) => { migrateCalEvents(s.calendar[mi]); Object.assign(s.calendar[mi].events[k], patch); };
    global_ ? mutateG(fn) : mutateL(fn);
  };
  return (
    <div className="px-3 pb-24">
      <div className="text-xs mb-2 rounded-lg p-2" style={{ color: "#9ca3af", background: "#ffffff08", border: "1px solid #ffffff14" }}>
        May → April. Nitro <b style={{ color: THEME.wcw.primary }}>Mondays</b>, NXT <b style={{ color: THEME.nxt.primary }}>Thursdays</b>, SmackDown <b style={{ color: THEME.sd.primary }}>Fridays</b>. Week 4 of each month is PLE week.
      </div>

      <Section title="📅 Show Cadence — per brand" theme={theme}>
        <div className="text-xs mb-2" style={{ color: "#9ca3af" }}>On a month where you run a PLE: 5 shows means you also run TV that week; 4 means the PLE replaces TV.</div>
        {BRAND_KEYS.map((k) => {
          const five = state.brands[k].fiveShow ?? !!BRAND_CONFIG[k].extraPLE;
          const mine = canTouchBrand(k);
          return (
            <div key={k} className="flex justify-between items-center gap-2 mb-1 rounded-lg p-2" style={{ background: "#00000033", border: "1px solid #ffffff14" }}>
              <span className="text-sm font-black" style={{ ...display, color: THEME[k].primary }}>{BRAND_CONFIG[k].name}</span>
              {mine ? (
                <div className="flex gap-1">
                  {[[true, "5 shows (4 TV + PLE)"], [false, "4 shows (3 TV + PLE)"]].map(([v, label]) => (
                    <button key={String(v)} onClick={() => mutateG((s) => { s.brands[k].fiveShow = v; })}
                      className="px-2 py-1 rounded-full text-xs font-black"
                      style={{ ...display, background: five === v ? THEME[k].primary : "#ffffff10", color: five === v ? "#0b0b0f" : "#9ca3af" }}>
                      {label}
                    </button>
                  ))}
                </div>
              ) : <span className="text-xs" style={{ color: "#9ca3af" }}>{five ? "5 shows (4 TV + PLE)" : "4 shows (3 TV + PLE)"}</span>}
            </div>
          );
        })}
      </Section>

      {cal.map((c, mi) => {
        const monthDone = mi < curM;
        return (
          <div key={mi} className="rounded-xl p-2 mb-2" style={{ background: mi === curM ? "#ffffff10" : "#ffffff06", border: "1px solid " + (mi === curM ? theme.primary + "66" : "#ffffff14") }}>
            <div className="flex justify-between items-center flex-wrap gap-1">
              <span className="text-sm font-black" style={{ ...display, color: "#fff" }}>{c.month}{mi === curM ? " — NOW" : monthDone ? " ✓" : ""}</span>
              <div className="flex gap-1 flex-wrap">
                {order.map((k) => evOf(c, k).on && <Pill key={k} color={THEME[k].primary} text="#0b0b0f">{evOf(c, k).ple || BRAND_CONFIG[k].name + " PLE"}</Pill>)}
                {!order.some((k) => evOf(c, k).on) && <Pill color="#374151">no PLEs scheduled</Pill>}
              </div>
            </div>
            <div className="grid grid-cols-3 gap-1 mt-1">
              {order.map((k) => (
                <div key={k} className="rounded p-1 flex items-center gap-1" style={{ background: "#00000033" }}>
                  <Ava src={state.brands[k].images?.logo} name={BRAND_CONFIG[k].name} size={18} />
                  <div className="text-xs min-w-0">
                    <div style={{ color: THEME[k].primary, fontWeight: 900 }}>{dayOf[k]}{evOf(c, k).on ? " + PLE" : ""}</div>
                    <div className="truncate" style={{ color: "#9ca3af" }}>{BRAND_CONFIG[k].show}</div>
                  </div>
                </div>
              ))}
            </div>
            {order.map((k) => {
              const e = evOf(c, k);
              const t = THEME[k];
              const aired = monthDone || (mi === curM && (state.brands[k].results || []).some((r) => r.isPLE && monthIdxOf(r.week) === mi && (r.season || 1) === (state.season || 1)));
              const mine = canTouchBrand(k) && !aired;
              if (!e.on && !mine) return null;
              return (
                <div key={k} className="rounded p-2 mt-1" style={{ background: "#00000044", border: "1px solid " + (e.on ? t.primary + "44" : "#ffffff14") }}>
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Ava src={state.brands[k].images?.logo} name={BRAND_CONFIG[k].name} size={20} />
                      {e.on ? (
                        <span className="text-sm font-black" style={{ ...display, color: t.primary }}>{e.ple || BRAND_CONFIG[k].name + " PLE"}</span>
                      ) : (
                        <span className="text-sm" style={{ color: "#6b7280" }}>{BRAND_CONFIG[k].name} — no PLE this month</span>
                      )}
                      {e.on && e.stadium && <Pill color="#b91c1c">STADIUM</Pill>}
                      {e.on && e.theme === "mitb" && <Pill color="#d4af37" text="#0b0b0f">💼 MITB</Pill>}
                      {e.on && e.theme === "rumble" && <Pill color="#d4af37" text="#0b0b0f">🏆 RUMBLE</Pill>}
                      {aired && e.on && <Pill color="#14532d" text="#86efac">✓ AIRED</Pill>}
                    </div>
                    {mine && (
                      <button className="text-xs underline" style={{ color: e.on ? "#ef4444" : "#86efac" }}
                        onClick={() => setEv(mi, k, e.on ? { on: false } : { on: true, ple: e.ple || BRAND_CONFIG[k].name + " Special" }, true)}>
                        {e.on ? "✕ cancel this PLE" : "➕ add a PLE this month"}
                      </button>
                    )}
                  </div>
                  {e.on && (e.arena || e.location) && <div className="text-xs mt-1" style={{ color: "#9ca3af" }}>📍 {[e.arena, e.location].filter(Boolean).join(" · ")}</div>}
                  {mine && e.on && (
                    <div className="flex flex-wrap gap-2 mt-2 items-end">
                      {[["ple", "Event name", e.ple], ["arena", "Arena", e.arena], ["location", "Location", e.location]].map(([field, label, val]) => (
                        <label key={field} className="text-xs" style={{ color: "#9ca3af" }}>
                          {label}
                          <input defaultValue={val || ""}
                            onBlur={(ein) => { const v = ein.target.value; setEv(mi, k, { [field]: v }, true); }}
                            className="block rounded px-2 py-1 text-sm mt-1" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22" }} />
                        </label>
                      ))}
                      <label className="text-xs" style={{ color: "#9ca3af" }}>
                        Theme
                        <select value={e.theme || ""} onChange={(ein) => setEv(mi, k, { theme: ein.target.value }, true)}
                          className="block rounded px-2 py-1 text-sm mt-1" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22" }}>
                          <option value="">— none —</option>
                          <option value="mitb">💼 MITB — ladder match winner gets a briefcase</option>
                          <option value="rumble">🏆 Rumble — match winner gets a main-event push</option>
                        </select>
                      </label>
                      <label className="text-xs flex items-center gap-1 pb-1" style={{ color: "#9ca3af" }}>
                        <input type="checkbox" checked={!!e.stadium} onChange={(ein) => setEv(mi, k, { stadium: ein.target.checked }, true)} /> stadium show (65,000 seats)
                      </label>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}

/* ================================================================
   HISTORY TAB
   ================================================================ */
function HistoryTab({ state, theme }) {
  const bKey = state.activeBrand;
  const brand = state.brands[bKey];
  const [open, setOpen] = useState(null);
  const results = [...(brand.results || [])].reverse();
  return (
    <div className="px-3 pb-24">
      <Section title={BRAND_CONFIG[bKey].name + " — Show Archive"} theme={theme}>
        {results.length === 0 && <div className="text-xs" style={{ color: "#6b7280" }}>No shows in the books yet.</div>}
        {results.map((r, i) => {
          const key = r.season + "-" + r.week + "-" + i;
          const isOpen = open === key;
          return (
            <div key={key} className="rounded-lg mb-2" style={{ background: "#00000033", border: "1px solid #ffffff14" }}>
              <button className="w-full p-2 flex justify-between items-center text-left" onClick={() => setOpen(isOpen ? null : key)}>
                <div className="text-sm font-bold" style={{ color: "#fff" }}>
                  S{r.season} · W{r.week} — {r.eventName} {r.isPLE && "🏟"}
                </div>
                <div className="flex items-center gap-2">
                  <GradeBadge score={r.rating * 10} size="sm" />
                  <span className="text-sm font-black" style={{ ...display, color: r.rating >= 8 ? "#22c55e" : r.rating >= 6.5 ? "#d4af37" : "#ef4444" }}>{r.rating.toFixed(1)}</span>
                  <span className="text-xs" style={{ color: "#9ca3af" }}>{isOpen ? "▲" : "▼"}</span>
                </div>
              </button>
              {isOpen && (
                <div className="px-2 pb-2">
                  <div className="text-xs mb-1" style={{ color: "#9ca3af" }}>{fmtNum(r.viewership)} viewers · {fmtNum(r.att)} att · {r.selloutTag} · net {money(r.net)}</div>
                  {r.script && <div className="text-xs mb-1 italic" style={{ color: "#d1d5db" }}>Creative {r.script.score}/100 — "{r.script.verdict}"</div>}
                  {r.matches.map((m, j) => (
                    <div key={j} className="rounded p-1 mb-1 text-xs" style={{ background: "#ffffff08" }}>
                      <div className="flex justify-between gap-2">
                        <span style={{ color: "#fff" }}>{m.isMain && "★ "}{m.names} <span style={{ color: "#9ca3af" }}>({m.stip})</span></span>
                        <span className="font-bold" style={{ color: m.q >= 85 ? "#22c55e" : m.q >= 70 ? "#d4af37" : "#9ca3af" }}>{m.q}</span>
                      </div>
                      <div style={{ color: "#9ca3af" }}>Winner: {m.winner} ({m.finish}){m.titleNote ? " · " + m.titleNote : ""}</div>
                      {m.notes && <div className="italic" style={{ color: "#6b7280" }}>📝 {m.notes}</div>}
                    </div>
                  ))}
                  {r.segments && r.segments.length > 0 && r.segments.map((sg, j) => (
                    <div key={"s" + j} className="text-xs mb-1" style={{ color: "#9ca3af" }}>{sg.kind}: {sg.who}{sg.target ? " → " + sg.target : ""} ({sg.q})</div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </Section>
    </div>
  );
}

/* ================================================================
   CHAMPIONSHIPS TAB
   ================================================================ */
function ChampsTab({ state, mutateG, theme, canAct }) {
  const bKey = state.activeBrand;
  const brand = state.brands[bKey];
  const img = brand.images || { titles: {}, units: {} };
  const [caseName, setCaseName] = useState("");
  const [caseTitle, setCaseTitle] = useState(brand.titles[0]?.id || "");
  const [caseHolder, setCaseHolder] = useState("");
  const myCases = (state.cases || []).filter((c) => c.brandKey === bKey);
  const eligibleFor = (t) => {
    const nm = t.name.toLowerCase();
    return brandRankings(brand).filter((u) => {
      if (nm.includes("women")) return u.sex === "F" && u.type === "s";
      if (nm.includes("tag")) return u.type === "t";
      return u.type === "s";
    }).filter((u) => u.id !== t.champ);
  };
  return (
    <div className="px-3 pb-24">
      {brand.titles.map((t) => {
        const champ = t.champ ? unitById(brand, t.champ) : null;
        const hist = [...(t.history || [])];
        const openReignE = hist.length && !hist[hist.length - 1].end ? hist[hist.length - 1] : null;
        const reignWeeks = openReignE ? Math.max(1, state.week - openReignE.start) : 0;
        const contenders = eligibleFor(t).slice(0, 8);
        return (
          <Section key={t.id} title={t.name} theme={theme}
            right={<Ava src={img.titles[t.id]} name={"🏆"} size={56} ring={theme.primary} />}>
            <div className="flex items-center gap-2 mb-2">
              {champ ? (<>
                <Ava src={img.units[champ.id]} name={champ.name} size={64} ring={theme.primary} />
                <div>
                  <div className="text-sm font-black" style={{ ...display, color: theme.primary }}>{champ.name}</div>
                  <div className="text-xs" style={{ color: "#9ca3af" }}>Reign: {reignWeeks} wk{reignWeeks !== 1 ? "s" : ""} · {t.defs || 0} defense{(t.defs || 0) !== 1 ? "s" : ""}</div>
                </div>
              </>) : <div className="text-sm font-bold" style={{ color: "#6b7280" }}>VACANT{t.note ? " — " + t.note : ""}</div>}
            </div>
            <div className="text-xs font-black mb-1" style={{ ...display, color: "#9ca3af" }}>TOP CONTENDERS</div>
            {contenders.map((u, i) => (
              <div key={u.id} className="flex items-center gap-2 text-xs mb-1">
                <span className="w-5 text-right font-black" style={{ ...display, color: i === 0 ? theme.primary : "#9ca3af" }}>{i + 1}</span>
                <Ava src={img.units[u.id]} name={u.name} size={30} />
                <span className="flex-1 truncate font-bold" style={{ color: "#fff" }}>{u.name}</span>
                <AlPill al={u.al} />
                <span style={{ color: "#9ca3af" }}>{u.w}–{u.l} · pwr {Math.round(powerScore(u))}</span>
              </div>
            ))}
            {hist.length > 0 && (<>
              <div className="text-xs font-black mt-2 mb-1" style={{ ...display, color: "#9ca3af" }}>LINEAGE</div>
              {[...hist].reverse().slice(0, 6).map((h, i) => (
                <div key={i} className="flex justify-between text-xs mb-1">
                  <span style={{ color: h.end ? "#9ca3af" : "#fff", fontWeight: h.end ? 400 : 700 }}>{h.name}{h.d ? " · " + h.d + " def" : ""}</span>
                  <span style={{ color: "#6b7280" }}>W{h.start}{h.end ? "–W" + h.end : "–now"}</span>
                </div>
              ))}
            </>)}
          </Section>
        );
      })}

      <Section title="💼 Money in the Bank Briefcases" theme={theme}>
        {myCases.length === 0 && <div className="text-xs mb-2" style={{ color: "#6b7280" }}>No briefcases in play. Win one at a MITB-themed PLE, or create one manually.</div>}
        {myCases.map((c) => {
          const holder = unitById(brand, c.holderId);
          const t = brand.titles.find((x) => x.id === c.titleId);
          return (
            <div key={c.id} className="rounded-lg p-2 mb-2 flex justify-between items-center gap-2" style={{ background: "#00000044", border: "1px solid #d4af3744" }}>
              <div className="flex items-center gap-2 min-w-0">
                <Ava src={holder ? img.units[holder.id] : ""} name={holder?.name || "?"} size={44} />
                <div className="min-w-0">
                  <div className="text-sm font-bold truncate" style={{ color: "#d4af37" }}>{c.name}</div>
                  <div className="text-xs" style={{ color: "#9ca3af" }}>{holder?.name || "—"} → shot at the {t?.name || "?"}</div>
                </div>
              </div>
              {canAct && <button className="text-xs underline" style={{ color: "#ef4444" }} onClick={() => mutateG((s) => { s.cases = (s.cases || []).filter((x) => x.id !== c.id); })}>void</button>}
            </div>
          );
        })}
        {canAct && (
          <div className="flex flex-wrap gap-2 items-end pt-2" style={{ borderTop: "1px solid #ffffff14" }}>
            <input value={caseName} onChange={(e) => setCaseName(e.target.value.slice(0, 50))} placeholder="Briefcase name…"
              className="rounded px-2 py-2 text-sm" style={{ background: "#15151c", color: "#fff", border: "1px solid #ffffff22" }} />
            <Sel value={caseTitle} onChange={setCaseTitle}>{brand.titles.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</Sel>
            <Sel value={caseHolder} onChange={setCaseHolder}>
              <option value="">holder…</option>
              {activeUnits(brand).map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
            </Sel>
            <Btn small theme={theme} disabled={!caseName.trim() || !caseTitle || !caseHolder}
              onClick={() => {
                const payload = { id: "c" + Date.now(), name: caseName.trim(), titleId: caseTitle, holderId: caseHolder, brandKey: bKey };
                mutateG((s) => {
                  (s.cases = s.cases || []).push(payload);
                  const h = unitById(s.brands[bKey], caseHolder);
                  pushNews(s, bKey, `💼 ${h?.name} now holds the ${payload.name} — a contract for a title shot, any time.`, "info");
                });
                setCaseName(""); setCaseHolder("");
              }}>
              Create Briefcase
            </Btn>
            <div className="text-xs w-full" style={{ color: "#6b7280" }}>Cash-ins happen from the Booking tab on show night.</div>
          </div>
        )}
      </Section>
    </div>
  );
}

/* ================================================================
   MODE SELECT + ONLINE LOBBY
   ================================================================ */
function ModeScreen({ onPick, cloudEnabled }) {
  return (
    <div className="bfg-page min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-lg bfg-shell">
        <div className="text-center mb-8">
          <div className="text-4xl bfg-display" style={{ color: "#fff" }}>
            Bound For <span style={{ color: "#d4af37" }}>Glory</span>
          </div>
          <div className="text-sm mt-2 font-medium tracking-widest uppercase" style={{ color: "#71717a" }}>GM Mod</div>
          <div className="text-xs mt-3" style={{ color: "#a1a1aa" }}>How are you playing tonight?</div>
        </div>
        <button onClick={() => onPick("hotseat")} className="bfg-mode-card mb-3 block" style={{ borderColor: "#d4af3744" }}>
          <div className="text-lg bfg-display" style={{ color: "#d4af37" }}>Hot-Seat</div>
          <div className="text-xs mt-1.5 leading-relaxed" style={{ color: "#a1a1aa" }}>
            Pass the phone or laptop around. One save on this device — all three GMs share it.
          </div>
        </button>
        <button onClick={() => onPick("online")} className="bfg-mode-card block" style={{ borderColor: "#b026ff44" }}>
          <div className="text-lg bfg-display" style={{ color: "#b026ff" }}>Online (Shared Save)</div>
          <div className="text-xs mt-1.5 leading-relaxed" style={{ color: "#a1a1aa" }}>
            One shared season. Each GM claims a brand with a name and PIN from their own device.
          </div>
          {cloudEnabled ? (
            <div className="bfg-alert mt-3" style={{ borderColor: "#16a34a44", background: "rgba(22,163,74,0.12)", color: "#86efac" }}>
              Cloud saves enabled — friends anywhere can join with your game link + room code.
            </div>
          ) : (
            <div className="bfg-alert bfg-alert-warn mt-3">
              Remote friends need the game deployed online (e.g. Vercel) plus Supabase in <code style={{ fontSize: "10px" }}>.env</code> — see README.
            </div>
          )}
        </button>
      </div>
    </div>
  );
}

function CopyChip({ label, value }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };
  return (
    <div className="rounded-lg p-3 mb-2 text-left" style={{ background: "rgba(0,0,0,0.35)", border: "1px solid rgba(255,255,255,0.08)" }}>
      <div className="text-[10px] uppercase tracking-widest mb-1" style={{ color: "#71717a" }}>{label}</div>
      <div className="flex items-center justify-between gap-2">
        <div className="text-sm font-mono break-all" style={{ color: "#f4f4f5" }}>{value}</div>
        <button type="button" onClick={copy} className="shrink-0 text-xs px-2 py-1 rounded-md font-semibold"
          style={{ background: "rgba(212,175,55,0.15)", color: "#d4af37", border: "1px solid rgba(212,175,55,0.35)" }}>
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
    </div>
  );
}

function OnlineLobby({ shared, roomCode, cloudEnabled, onCreate, onJoin, onClaim, onBack, err, busy }) {
  const [sel, setSel] = useState(null);
  const [name, setName] = useState("");
  const [pin, setPin] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const claims = (shared && shared.claims) || {};
  const normalizedJoin = joinCode.trim().toUpperCase().replace(/\s+/g, "");
  return (
    <div className="bfg-page min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-lg bfg-shell">
        <div className="text-center mb-6">
          <div className="text-2xl bfg-display" style={{ color: "#fff" }}>Online Lobby</div>
          <button onClick={onBack} className="bfg-link mt-2">← Back to mode select</button>
        </div>
        {cloudEnabled && roomCode && (
          <div className="bfg-card p-4 mb-4">
            <div className="text-xs uppercase tracking-widest mb-3 text-center" style={{ color: "#71717a" }}>
              Invite remote friends
            </div>
            <CopyChip label="1 — Send them this link" value={typeof window !== "undefined" ? window.location.origin : ""} />
            <CopyChip label="2 — They join with this room code" value={roomCode} />
            <div className="text-xs text-center mt-2 leading-relaxed" style={{ color: "#a1a1aa" }}>
              Online → Join Room → enter code → claim a brand with a PIN.
            </div>
          </div>
        )}
        {!shared ? (
          <div className="bfg-card p-6">
            {cloudEnabled ? (
              <>
                <div className="text-sm mb-4 text-center" style={{ color: "#d4d4d8" }}>Create a new season or join an existing room.</div>
                <div className="flex flex-col gap-2 mb-4">
                  <Btn onClick={onCreate} disabled={busy}>{busy ? "Creating…" : "Create Online Season"}</Btn>
                </div>
                <div className="text-xs text-center mb-2" style={{ color: "#71717a" }}>— or join with a code —</div>
                <input value={joinCode} onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                  placeholder="BWG-1234" className="bfg-input mb-2 text-center tracking-widest" />
                <Btn kind="secondary" disabled={busy || normalizedJoin.length < 4}
                  onClick={() => onJoin(normalizedJoin)}>
                  {busy ? "Joining…" : "Join Room"}
                </Btn>
              </>
            ) : (
              <div className="text-center">
                <div className="text-sm mb-4" style={{ color: "#d4d4d8" }}>No online season on this device yet.</div>
                <Btn onClick={onCreate} disabled={busy}>{busy ? "Creating…" : "Create Online Season"}</Btn>
              </div>
            )}
          </div>
        ) : (
          <div className="bfg-card p-4">
            <div className="text-xs mb-4" style={{ color: "#71717a" }}>
              Week {shared.week} of {TOTAL_WEEKS} · Season {shared.season || 1}. Claim a brand or log back in.
            </div>
            {BRAND_KEYS.map((k) => {
              const t = THEME[k]; const c = claims[k];
              return (
                <button key={k} onClick={() => { setSel(k); setName(""); setPin(""); }}
                  className="w-full rounded-xl p-3 mb-2 text-left transition-all"
                  style={{
                    background: sel === k ? t.deep : "rgba(0,0,0,0.25)",
                    border: `1px solid ${sel === k ? t.primary + "66" : "rgba(255,255,255,0.08)"}`,
                  }}>
                  <div className="flex justify-between items-center gap-2">
                    <span className="bfg-display text-sm" style={{ color: t.primary }}>{BRAND_CONFIG[k].name}</span>
                    <span className="text-xs font-medium" style={{ color: c ? "#86efac" : "#71717a" }}>
                      {c ? "Claimed by " + c.name : "Unclaimed"}
                    </span>
                  </div>
                </button>
              );
            })}
            {sel && (
              <div className="bfg-card-inner p-3 mt-2">
                {!claims[sel] && (
                  <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your GM name"
                    className="bfg-input mb-2" />
                )}
                <input value={pin} onChange={(e) => setPin(e.target.value)}
                  placeholder={claims[sel] ? "Enter your PIN" : "Create a PIN (4+ characters)"} type="password"
                  className="bfg-input mb-3" />
                <Btn disabled={busy} onClick={() => onClaim(sel, name, pin)}>
                  {busy ? "…" : claims[sel] ? "Log in as " + claims[sel].name : "Claim " + BRAND_CONFIG[sel].name}
                </Btn>
              </div>
            )}
            {err && <div className="bfg-alert bfg-alert-warn mt-3">{err}</div>}
          </div>
        )}
      </div>
    </div>
  );
}

/* ================================================================
   APP SHELL
   ================================================================ */
const PERSONAL_KEY = "brand-wars-gm-v4";
const SHARED_KEY = "brand-wars-online-v4";
const ID_KEY = "brand-wars-id-v4";
const LOCAL_KEY = "brand-wars-local-v4";
const MODE_KEY = "brand-wars-mode-v2";

const TABS = [
  ["dash", "📊 Dash"], ["book", "📋 Book"], ["roster", "👥 Roster"], ["ranks", "📈 Ranks"],
  ["champs", "🏆 Titles"], ["feuds", "🔥 Feuds"], ["trades", "🔁 Trades"], ["fa", "✍️ Free Agents"],
  ["train", "🏋️ Train"], ["staff", "🎙 Staff"], ["social", "💬 Social"], ["sponsors", "🤝 Sponsors"],
  ["cal", "📅 Calendar"], ["money", "💰 Finance"], ["history", "📼 History"], ["images", "🖼 Images"],
];

/* storage shim: uses window.storage when hosted in an environment that provides it,
   otherwise falls back to localStorage (shared keys get a prefix). */
const sGet = async (k, sh) => {
  try {
    if (typeof window !== "undefined" && window.storage) {
      const r = await window.storage.get(k, sh);
      return r == null ? null : (typeof r === "string" ? r : (r.value ?? null));
    }
    return localStorage.getItem((sh ? "shared::" : "") + k);
  } catch { return null; }
};
const sSet = async (k, v, sh) => {
  try {
    if (typeof window !== "undefined" && window.storage) { await window.storage.set(k, v, sh); return; }
    localStorage.setItem((sh ? "shared::" : "") + k, v);
  } catch {}
};
const sDel = async (k, sh) => {
  try {
    if (typeof window !== "undefined" && window.storage) { await window.storage.delete(k, sh); return; }
    localStorage.removeItem((sh ? "shared::" : "") + k);
  } catch {}
};

export default function App() {
  const [phase, setPhase] = useState("boot"); // boot | mode | setup | lobby | game
  const [mode, setMode] = useState(null); // hotseat | online
  const [me, setMe] = useState(null); // { brand, pin } in online mode
  const [state, setState] = useState(null);
  const [tab, setTab] = useState("dash");
  const [syncing, setSyncing] = useState(false);
  const [syncErr, setSyncErr] = useState(null);
  const [lobbyShared, setLobbyShared] = useState(null);
  const [lobbyErr, setLobbyErr] = useState(null);
  const [lobbyBusy, setLobbyBusy] = useState(false);
  const [roomCode, setRoomCode] = useState(() => getStoredRoom()?.roomCode || null);
  const cloudEnabled = isCloudStorageEnabled();
  const stateRef = useRef(null);
  const pushingRef = useRef(false);
  const saveTimer = useRef(null);
  useEffect(() => { stateRef.current = state; }, [state]);

  /* ---- boot ---- */
  useEffect(() => {
    (async () => {
      const m = await sGet(MODE_KEY, false);
      if (m === "hotseat") {
        setMode("hotseat");
        const raw = await sGet(PERSONAL_KEY, false);
        if (raw) { try { const p = JSON.parse(raw); if (p && p.ver === 4) { setState(applyViewershipRules(p)); setPhase(p.screen === "setup" ? "setup" : "game"); return; } } catch {} }
        setState(buildInitialState()); setPhase("setup"); return;
      }
      if (m === "online") {
        setMode("online");
        const storedRoom = getStoredRoom();
        if (storedRoom?.roomCode) setRoomCode(storedRoom.roomCode);
        let id = null; try { const r = await sGet(ID_KEY, false); id = r ? JSON.parse(r) : null; } catch {}
        let game = null; try { const r = await sGet(SHARED_KEY, true); game = r ? JSON.parse(r) : null; } catch {}
        if (game && game.ver === 4 && id && game.claims && game.claims[id.brand] && game.claims[id.brand].pinH === hashPin(id.pin)) {
          let loc = null; try { const r = await sGet(LOCAL_KEY, false); loc = r ? JSON.parse(r) : null; } catch {}
          const merged = applyViewershipRules({ ...game, activeBrand: id.brand });
          if (loc && loc.week === game.week && loc.booking) merged.booking = loc.booking;
          setMe(id); setState(merged); setPhase("game"); return;
        }
        setLobbyShared(game && game.ver === 4 ? game : null); setPhase("lobby"); return;
      }
      setPhase("mode");
    })();
  }, []);

  /* ---- autosave: hotseat = full state; online = local snapshot so booking survives refresh ---- */
  useEffect(() => {
    if (!state || phase === "boot") return;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      if (mode === "hotseat") sSet(PERSONAL_KEY, JSON.stringify(state), false);
      else if (mode === "online" && phase === "game") sSet(LOCAL_KEY, JSON.stringify({ week: state.week, booking: state.booking }), false);
    }, 800);
    return () => saveTimer.current && clearTimeout(saveTimer.current);
  }, [state, mode, phase]);

  /* ---- online polling ---- */
  useEffect(() => {
    if (mode !== "online" || phase !== "game") return;
    const t = setInterval(async () => {
      if (pushingRef.current) return;
      const raw = await sGet(SHARED_KEY, true);
      if (!raw) return;
      try {
        const p = JSON.parse(raw);
        if (p && p.ver === 4) {
          setState((prev) => {
            if (!prev) return p;
            const keepBooking = p.week === prev.week ? prev.booking : p.booking;
            return { ...p, booking: keepBooking, activeBrand: prev.activeBrand };
          });
        }
      } catch {}
    }, 5000);
    return () => clearInterval(t);
  }, [mode, phase]);

  /* ---- mutators ---- */
  const mutateL = (fn) => setState((prev) => { const s = clone(prev); fn(s); return s; });
  const mutateG = (fn) => {
    if (mode !== "online") { mutateL(fn); return; }
    (async () => {
      pushingRef.current = true; setSyncing(true); setSyncErr(null);
      try {
        let base = stateRef.current;
        const raw = await sGet(SHARED_KEY, true);
        if (raw) {
          try {
            const p = JSON.parse(raw);
            if (p && p.ver === 4) base = { ...p, booking: p.week === stateRef.current.week ? stateRef.current.booking : p.booking, activeBrand: stateRef.current.activeBrand };
          } catch {}
        }
        const s = clone(base); fn(s);
        await sSet(SHARED_KEY, JSON.stringify(s), true);
        setState(s);
      } catch (e) { setSyncErr("Sync failed — couldn't reach the shared save. Try that again."); }
      pushingRef.current = false; setSyncing(false);
    })();
  };

  /* ---- lobby actions ---- */
  const createOnline = async () => {
    setLobbyBusy(true); setLobbyErr(null);
    try {
      const s = buildInitialState();
      s.screen = "rosterSetup"; s.claims = { wcw: null, sd: null, nxt: null };
      if (cloudEnabled) {
        const room = await createRoomSession(s);
        setRoomCode(room.roomCode);
      } else {
        await sSet(SHARED_KEY, JSON.stringify(s), true);
      }
      setLobbyShared(s);
    } catch (e) {
      setLobbyErr(cloudEnabled ? "Couldn't create the online room — check Supabase setup." : "Couldn't create season.");
    }
    setLobbyBusy(false);
  };

  const joinRoom = async (code) => {
    setLobbyBusy(true); setLobbyErr(null);
    try {
      let g = null;
      if (cloudEnabled) {
        g = await joinRoomByCode(code);
        if (!g || g.ver !== 4) { setLobbyErr("Room not found — double-check the code."); setLobbyBusy(false); return; }
        setRoomCode(code.toUpperCase());
      } else {
        const r = await sGet(SHARED_KEY, true);
        g = r ? JSON.parse(r) : null;
        if (!g || g.ver !== 4) { setLobbyErr("No season on this device — create one or enable cloud saves."); setLobbyBusy(false); return; }
      }
      setLobbyShared(g);
    } catch {
      setLobbyErr("Couldn't join that room — try again.");
    }
    setLobbyBusy(false);
  };

  const claimBrand = async (bKey, name, pin) => {
    setLobbyBusy(true); setLobbyErr(null);
    let g = null; try { const r = await sGet(SHARED_KEY, true); g = r ? JSON.parse(r) : null; } catch {}
    if (!g || g.ver !== 4) { setLobbyErr("No online season found — create one first."); setLobbyBusy(false); return; }
    const existing = g.claims && g.claims[bKey];
    if (existing) {
      if (existing.pinH !== hashPin(pin)) { setLobbyErr("Wrong PIN for " + BRAND_CONFIG[bKey].name + "."); setLobbyBusy(false); return; }
    } else {
      if (!name.trim() || pin.length < 4) { setLobbyErr("Need a GM name and a PIN of 4+ characters."); setLobbyBusy(false); return; }
      g.claims = g.claims || {}; g.claims[bKey] = { name: name.trim(), pinH: hashPin(pin) };
      g.players[bKey] = name.trim();
      pushNews(g, bKey, name.trim() + " has taken over as " + BRAND_CONFIG[bKey].name + " GM.", "info");
      await sSet(SHARED_KEY, JSON.stringify(g), true);
    }
    const id = { brand: bKey, pin };
    await sSet(ID_KEY, JSON.stringify(id), false);
    let loc = null; try { const r = await sGet(LOCAL_KEY, false); loc = r ? JSON.parse(r) : null; } catch {}
    const merged = applyViewershipRules({ ...g, activeBrand: bKey });
    if (loc && loc.week === g.week && loc.booking) merged.booking = loc.booking;
    setMe(id); setState(merged); setPhase("game"); setLobbyBusy(false);
  };

  /* ---- reset / mode switch ---- */
  const reset = async () => {
    if (mode === "online") {
      if (!window.confirm("Reset the ONLINE season for EVERYONE? Claims and logins are kept.")) return;
      mutateG((s) => {
        const f = buildInitialState();
        f.screen = "game"; f.claims = s.claims || { wcw: null, sd: null, nxt: null }; f.players = s.players;
        f.activeBrand = me ? me.brand : "wcw";
        BRAND_KEYS.forEach((k) => issueObjectives(f, k, 0));
        Object.keys(s).forEach((k) => delete s[k]);
        Object.assign(s, f);
      });
      setTab("dash");
    } else {
      if (!window.confirm("Burn the whole season down and start over?")) return;
      await sDel(PERSONAL_KEY, false);
      setState(buildInitialState()); setPhase("setup"); setTab("dash");
    }
  };

  const switchMode = async () => {
    await sDel(MODE_KEY, false);
    clearStoredRoom();
    setRoomCode(null);
    setMode(null); setMe(null); setPhase("mode"); setTab("dash");
  };

  /* ---- screens ---- */
  if (phase === "boot" || (phase === "game" && !state)) return (
    <div className="bfg-page min-h-screen flex items-center justify-center">
      <div className="text-base bfg-display animate-pulse" style={{ color: "#d4af37" }}>Loading the universe…</div>
    </div>
  );

  if (phase === "mode") return <ModeScreen cloudEnabled={cloudEnabled} onPick={async (m) => {
    setMode(m); await sSet(MODE_KEY, m, false);
    if (m === "hotseat") {
      const raw = await sGet(PERSONAL_KEY, false);
      if (raw) { try { const p = JSON.parse(raw); if (p && p.ver === 4) { setState(applyViewershipRules(p)); setPhase(p.screen === "setup" ? "setup" : "game"); return; } } catch {} }
      setState(buildInitialState()); setPhase("setup");
    } else {
      setRoomCode(getStoredRoom()?.roomCode || null);
      let game = null; try { const r = await sGet(SHARED_KEY, true); game = r ? JSON.parse(r) : null; } catch {}
      setLobbyShared(game && game.ver === 4 ? game : null); setPhase("lobby");
    }
  }} />;

  if (phase === "setup") return <SetupScreen onStart={(names) => {
    setState((prev) => { const s = clone(prev); s.players = names; s.screen = "rosterSetup"; return s; });
    setPhase("game");
    setTab("roster");
  }} />;

  if (phase === "lobby") return <OnlineLobby shared={lobbyShared} roomCode={roomCode} cloudEnabled={cloudEnabled}
    onCreate={createOnline} onJoin={joinRoom} onClaim={claimBrand} onBack={switchMode} err={lobbyErr} busy={lobbyBusy} />;

  if (state.screen === "seasonEnd") return <SeasonEnd state={state} onContinue={() => { mutateG((s) => startNextSeason(s)); setTab("dash"); }} onRestart={reset} />;

  const theme = THEME[state.activeBrand];
  const canAct = mode !== "online" || (me && me.brand === state.activeBrand);
  const allLocked = BRAND_KEYS.every((k) => state.locked[k]);
  const lockedCount = BRAND_KEYS.filter((k) => state.locked[k]).length;
  const unclaimed = mode === "online" ? BRAND_KEYS.filter((k) => !(state.claims && state.claims[k])) : [];

  return (
    <div className="bfg-page min-h-screen pb-20" style={{ color: theme.text }}>
      <TopBar state={state} theme={theme} onReset={reset} onMode={switchMode}
        logo={state.brands[state.activeBrand].images && state.brands[state.activeBrand].images.logo}
        onlineTag={mode === "online" ? (syncing ? "⟳ syncing" : "● online" + (roomCode ? " · " + roomCode : "") + " · you run " + (me ? BRAND_CONFIG[me.brand].name : "?")) : null} />
      <BrandSwitch state={state} onPick={(k) => { setState((prev) => ({ ...prev, activeBrand: k })); }} />

      {state.screen === "rosterSetup" && (
        <div className="mx-4 mt-3 bfg-alert bfg-alert-info bfg-shell">
          <b>Roster setup</b> — tune stats on the Roster tab, then kick off from Dash.
        </div>
      )}

      {unclaimed.length > 0 && (
        <div className="mx-4 mt-3 bfg-alert bfg-alert-warn bfg-shell">
          Waiting on {unclaimed.map((k) => BRAND_CONFIG[k].name).join(" + ")} to be claimed in the lobby.
        </div>
      )}

      <div className="px-4 pt-4 pb-2 bfg-shell">
        <div className="bfg-tabs">
          {TABS.map(([id, label]) => (
            <button key={id} onClick={() => setTab(id)}
              className={"bfg-tab " + (tab === id ? "bfg-tab-active" : "")}
              style={tab === id ? { background: theme.primary, color: "#0a0a0c" } : undefined}>
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-4 pb-4 bfg-shell">
      {tab === "dash" && (
        <Dashboard state={state} theme={theme}
          onGoRoster={() => setTab("roster")}
          onKickOffSeason={() => mutateL((s) => { s.screen = "game"; BRAND_KEYS.forEach((k) => issueObjectives(s, k, 0)); setTab("book"); })} />
      )}
      {tab === "book" && <BookingTab state={state} mutateL={mutateL} mutateG={mutateG} theme={theme} canAct={canAct} />}
      {tab === "roster" && <RosterTab state={state} mutateG={mutateG} theme={theme} canAct={canAct} />}
      {tab === "ranks" && <RanksTab state={state} theme={theme} />}
      {tab === "champs" && <ChampsTab state={state} mutateG={mutateG} theme={theme} canAct={canAct} />}
      {tab === "feuds" && <FeudsTab state={state} mutateG={mutateG} theme={theme} canAct={canAct} />}
      {tab === "trades" && <TradesTab state={state} mutateG={mutateG} theme={theme} canAct={canAct} />}
      {tab === "fa" && <FATab state={state} mutateG={mutateG} theme={theme} canAct={canAct} />}
      {tab === "train" && <TrainTab state={state} mutateG={mutateG} theme={theme} canAct={canAct} />}
      {tab === "staff" && <StaffTab state={state} mutateG={mutateG} theme={theme} canAct={canAct} />}
      {tab === "social" && <SocialTab state={state} mutateG={mutateG} theme={theme} canAct={canAct} />}
      {tab === "sponsors" && <SponsorsTab state={state} mutateG={mutateG} theme={theme} canAct={canAct} />}
      {tab === "cal" && <CalendarTab state={state} mutateL={mutateL} mutateG={mutateG} theme={theme} canAct={canAct} mode={mode} me={me} />}
      {tab === "money" && <FinanceTab state={state} theme={theme} />}
      {tab === "history" && <HistoryTab state={state} theme={theme} />}
      {tab === "images" && <ImagesTab state={state} mutateG={mutateG} theme={theme} canAct={canAct} />}
      </div>

      <EventModal state={state} mutateG={mutateG} theme={theme} canAct={canAct} />

      {syncErr && (
        <div className="fixed bottom-20 left-4 right-4 z-50 bfg-alert bfg-shell text-center" style={{ background: "rgba(127,29,29,0.95)", color: "#fecaca", border: "1px solid rgba(239,68,68,0.35)" }}>{syncErr}</div>
      )}

      <div className="bfg-dock fixed bottom-0 left-0 right-0 z-40 px-4 py-3">
        <div className="flex items-center justify-between gap-3 bfg-shell">
          <div className="text-xs font-medium" style={{ color: "#71717a" }}>
            {BRAND_KEYS.map((k) => (
              <span key={k} className="mr-2" style={{ color: state.locked[k] ? "#86efac" : "#52525b" }}>
                {BRAND_CONFIG[k].name} {state.locked[k] ? "✓" : "…"}
              </span>
            ))}
          </div>
          <Btn theme={theme} disabled={!allLocked}
            onClick={() => mutateG((s) => { advanceWeek(s); })}>
            {allLocked
              ? (state.week + 1 > TOTAL_WEEKS ? "Season Finale" : "Advance to Week " + (state.week + 1))
              : lockedCount + "/3 shows locked"}
          </Btn>
        </div>
      </div>
    </div>
  );
}
