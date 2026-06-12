/* ================================================================
   Bound For Glory GM — 3-Player Universe Mode (engine + data)
   WCW · SmackDown · NXT — built from the Universe Draft sheet.
   Winning is not just money: Story & Continuity, Sponsor Execution,
   PLE Payoffs & Fan Investment, Audience Growth, Profit.
   ================================================================ */

/* ---------------- helpers ---------------- */
export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
export const rnd = (a, b) => a + Math.random() * (b - a);
export const ri = (a, b) => Math.floor(rnd(a, b + 1));
export const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
export const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
export const clone = (o) => (typeof structuredClone === "function" ? structuredClone(o) : JSON.parse(JSON.stringify(o)));
export const money = (n) => {
  const neg = n < 0; const v = Math.abs(Math.round(n));
  let s;
  if (v >= 1e9) s = "$" + (v / 1e9).toFixed(2) + "B";
  else if (v >= 1e6) s = "$" + (v / 1e6).toFixed(2) + "M";
  else if (v >= 1e3) s = "$" + (v / 1e3).toFixed(0) + "K";
  else s = "$" + v;
  return neg ? "-" + s : s;
};
export const fmtNum = (n) => n.toLocaleString();
export const letter = (x100) => { // 0-100 scale
  const r = x100 / 10;
  if (r >= 9.3) return "A+"; if (r >= 8.5) return "A"; if (r >= 8.0) return "A-";
  if (r >= 7.5) return "B+"; if (r >= 7.0) return "B"; if (r >= 6.5) return "B-";
  if (r >= 6.0) return "C+"; if (r >= 5.5) return "C"; if (r >= 5.0) return "C-";
  if (r >= 4.0) return "D"; return "F";
};

/* ---------------- calendar (from the sheet's PPV schedule) ---------------- */
export const SEASON = [
  { month: "May", ple: "Bound For Glory", host: "nxt" },
  { month: "June", ple: "Heatwave", host: "sd" },
  { month: "July", ple: "American Bash", host: "wcw" },
  { month: "August", ple: "NXT Redemption", host: "nxt" },
  { month: "September", ple: "No Mercy", host: "sd" },
  { month: "October", ple: "Halloween Havoc", host: "wcw" },
  { month: "November", ple: "Worlds Collide & War Games", host: "nxt", all: true },
  { month: "December", ple: "Bad Blood", host: "sd" },
  { month: "January", ple: "World War 3", host: "wcw" },
  { month: "February", ple: "NXT Sacrifice", host: "nxt" },
  { month: "March", ple: "WrestleMania", host: "sd", all: true, stadium: true },
  { month: "April", ple: "Starrcade", host: "wcw" },
];
export const TOTAL_WEEKS = SEASON.length * 4;
export const calOf = (state, mIdx) => (((state && state.calendar) || SEASON)[mIdx]);

/* per-brand monthly event. New model: cal.events = { wcw: {on, ple, arena, location, theme, stadium}, ... }
   Legacy single-host calendars (older online saves) fall back to host/all fields. */
export function brandEvent(state, mIdx, bKey) {
  const c = calOf(state, mIdx);
  if (!c) return null;
  if (c.events) {
    const e = c.events[bKey];
    return e && e.on ? e : null;
  }
  return (c.host === bKey || c.all)
    ? { on: true, ple: c.ple, arena: c.arena || "", location: c.location || "", theme: c.theme || "", stadium: !!c.stadium }
    : null;
}
export function migrateCalEvents(c) {
  if (c.events) return c;
  c.events = {};
  BRAND_KEYS.forEach((k) => {
    const on = c.host === k || !!c.all;
    c.events[k] = { on, ple: on ? c.ple : "", arena: c.arena || "", location: c.location || "", theme: c.theme || "", stadium: on ? !!c.stadium : false };
  });
  return c;
}
export const monthIdxOf = (week) => Math.floor((week - 1) / 4);
export const weekOfMonth = (week) => ((week - 1) % 4) + 1;
export const isPLEWeek = (week) => weekOfMonth(week) === 4;

/* ---------------- show economics ---------------- */
export const VIEW_FLOOR = 700000;   // viewership can never drop below 700K
export const VIEW_CEIL = 5000000;   // or climb above 5M
export const LOCAL_TRAVEL = 75000;  // domestic tour — same bill for every brand at the same stop
export const DEFAULT_MARKET = "pitt"; // everyone starts neutral; you pick the market each week
export const VENUE = { tv: 15000, ple: 19000, stadium: 65000 }; // same building potential for all brands
export const TICKET = { tv: 65, ple: 120, stadium: 140 };
export const PRODUCTION = { tv: 900000, ple: 2400000, stadium: 5000000 };

export const MARKETS = [
  /* big — huge buildings, premium prices */
  { id: "nyc", n: "New York, NY", flag: "🇺🇸", tier: "big", att: 1.3, price: 1.3, travel: 180000 },
  { id: "msg", n: "Madison Square Garden, New York", flag: "🇺🇸", tier: "big", att: 1.35, price: 1.35, travel: 75000, nxtHome: true },
  { id: "la", n: "Los Angeles, CA", flag: "🇺🇸", tier: "big", att: 1.3, price: 1.25, travel: 170000 },
  { id: "chi", n: "Chicago, IL", flag: "🇺🇸", tier: "big", att: 1.25, price: 1.2, travel: 150000 },
  { id: "philly", n: "Philadelphia, PA", flag: "🇺🇸", tier: "big", att: 1.2, price: 1.15, travel: 140000 },
  { id: "dal", n: "Dallas, TX", flag: "🇺🇸", tier: "big", att: 1.2, price: 1.15, travel: 140000 },
  { id: "atl", n: "Atlanta, GA", flag: "🇺🇸", tier: "big", att: 1.2, price: 1.15, travel: 130000 },
  { id: "mia", n: "Miami, FL", flag: "🇺🇸", tier: "big", att: 1.15, price: 1.2, travel: 140000 },
  { id: "lv", n: "Las Vegas, NV", flag: "🇺🇸", tier: "big", att: 1.15, price: 1.3, travel: 150000 },
  { id: "bos", n: "Boston, MA", flag: "🇺🇸", tier: "big", att: 1.15, price: 1.18, travel: 130000 },
  { id: "tor", n: "Toronto, Canada", flag: "🇨🇦", tier: "big", att: 1.18, price: 1.12, travel: 200000 },
  /* mid — the bread-and-butter loop */
  { id: "orl", n: "Orlando, FL", flag: "🇺🇸", tier: "mid", att: 1.0, price: 1.0, travel: 75000 },
  { id: "pitt", n: "Pittsburgh, PA", flag: "🇺🇸", tier: "mid", att: 1.0, price: 1.0, travel: 75000 },
  { id: "cle", n: "Cleveland, OH", flag: "🇺🇸", tier: "mid", att: 1.0, price: 0.98, travel: 75000 },
  { id: "stl", n: "St. Louis, MO", flag: "🇺🇸", tier: "mid", att: 1.0, price: 0.98, travel: 75000 },
  { id: "kc", n: "Kansas City, MO", flag: "🇺🇸", tier: "mid", att: 0.98, price: 0.98, travel: 75000 },
  { id: "den", n: "Denver, CO", flag: "🇺🇸", tier: "mid", att: 1.02, price: 1.02, travel: 85000 },
  { id: "phx", n: "Phoenix, AZ", flag: "🇺🇸", tier: "mid", att: 1.02, price: 1.0, travel: 85000 },
  { id: "clt", n: "Charlotte, NC", flag: "🇺🇸", tier: "mid", att: 1.0, price: 1.0, travel: 70000 },
  { id: "rdu", n: "Raleigh, NC", flag: "🇺🇸", tier: "mid", att: 0.98, price: 1.0, travel: 70000 },
  { id: "msp", n: "Minneapolis, MN", flag: "🇺🇸", tier: "mid", att: 1.0, price: 1.0, travel: 80000 },
  { id: "nash", n: "Nashville, TN", flag: "🇺🇸", tier: "mid", att: 1.05, price: 1.05, travel: 70000 },
  { id: "sa", n: "San Antonio, TX", flag: "🇺🇸", tier: "mid", att: 1.0, price: 0.98, travel: 80000 },
  /* small — cheap nights, loyal crowds, small gates */
  { id: "dsm", n: "Des Moines, IA", flag: "🇺🇸", tier: "small", att: 0.78, price: 0.85, travel: 30000 },
  { id: "tul", n: "Tulsa, OK", flag: "🇺🇸", tier: "small", att: 0.78, price: 0.85, travel: 30000 },
  { id: "alb", n: "Albany, NY", flag: "🇺🇸", tier: "small", att: 0.76, price: 0.85, travel: 30000 },
  { id: "chat", n: "Chattanooga, TN", flag: "🇺🇸", tier: "small", att: 0.76, price: 0.82, travel: 30000 },
  { id: "spo", n: "Spokane, WA", flag: "🇺🇸", tier: "small", att: 0.75, price: 0.82, travel: 35000 },
  { id: "oma", n: "Omaha, NE", flag: "🇺🇸", tier: "small", att: 0.78, price: 0.85, travel: 30000 },
  { id: "boise", n: "Boise, ID", flag: "🇺🇸", tier: "small", att: 0.74, price: 0.82, travel: 35000 },
  /* international — massive paydays, massive travel bills */
  { id: "london", n: "London, UK", flag: "🇬🇧", tier: "intl", att: 1.35, price: 1.45, travel: 1100000 },
  { id: "paris", n: "Paris, France", flag: "🇫🇷", tier: "intl", att: 1.3, price: 1.4, travel: 1100000 },
  { id: "berlin", n: "Berlin, Germany", flag: "🇩🇪", tier: "intl", att: 1.25, price: 1.35, travel: 1000000 },
  { id: "rome", n: "Rome, Italy", flag: "🇮🇹", tier: "intl", att: 1.25, price: 1.35, travel: 900000 },
  { id: "madrid", n: "Madrid, Spain", flag: "🇪🇸", tier: "intl", att: 1.25, price: 1.32, travel: 950000 },
  { id: "tokyo", n: "Tokyo, Japan", flag: "🇯🇵", tier: "intl", att: 1.35, price: 1.42, travel: 1400000 },
  { id: "mexcity", n: "Mexico City, Mexico", flag: "🇲🇽", tier: "intl", att: 1.3, price: 1.15, travel: 500000 },
  { id: "melb", n: "Melbourne, Australia", flag: "🇦🇺", tier: "intl", att: 1.3, price: 1.4, travel: 1600000 },
  { id: "mumbai", n: "Mumbai, India", flag: "🇮🇳", tier: "intl", att: 1.35, price: 1.1, travel: 1300000 },
  { id: "dublin", n: "Dublin, Ireland", flag: "🇮🇪", tier: "intl", att: 1.2, price: 1.35, travel: 1000000 },
];

export const LOGISTICS = {
  hotel: 420000, transport: 300000, medical: 100000, catering: 120000, insurance: 150000,
  adsTV: 250000, adsPLE: 600000, activationTV: 150000, activationPLE: 400000, media: 80000,
};

const RATING_VIEW_PCT = { 10: 0.06, 9: 0.04, 8: 0.02, 7: 0.004, 6: -0.014, 5: -0.032, 4: -0.05, 3: -0.07, 2: -0.09, 1: -0.11 };
export const viewPct = (r) => {
  const lo = clamp(Math.floor(r), 1, 10), hi = clamp(lo + 1, 1, 10), t = clamp(r - lo, 0, 1);
  return RATING_VIEW_PCT[lo] * (1 - t) + RATING_VIEW_PCT[hi] * t;
};

export const STIPS = [
  { id: "std", n: "Standard", b: 0, fat: 1 },
  { id: "nodq", n: "No DQ", b: 2, fat: 1 },
  { id: "falls", n: "Falls Count Anywhere", b: 2, fat: 2 },
  { id: "tables", n: "Tables Match", b: 2, fat: 2 },
  { id: "street", n: "Street Fight", b: 2, fat: 2 },
  { id: "dumpster", n: "Dumpster Match", b: 2, fat: 2 },
  { id: "extreme", n: "Extreme Rules", b: 3, fat: 2 },
  { id: "cage", n: "Steel Cage", b: 3, fat: 2 },
  { id: "ladder", n: "Ladder", b: 3, fat: 2 },
  { id: "submission", n: "Submission Match", b: 3, fat: 2 },
  { id: "iron", n: "Iron Man", b: 4, fat: 3 },
  { id: "battleroyal", n: "Battle Royal", b: 3, fat: 2, br: true },
  { id: "tlc", n: "TLC", b: 4, fat: 3 },
  { id: "lms", n: "Last Man Standing", b: 5, fat: 3 },
  { id: "inferno", n: "Inferno Match", b: 5, fat: 3 },
  { id: "hiac", n: "Hell in a Cell", b: 6, fat: 3, ple: true },
  { id: "chamber", n: "Elimination Chamber", b: 7, fat: 4, ple: true, multi: true },
  { id: "wargames", n: "War Games", b: 7, fat: 4, ple: true, multi: true },
];
export const FINISHES = ["Clean", "DQ", "Screwjob", "No Contest"];
export const PROMO_TONES = ["Call-out", "Hype / Momentum", "Heel Heat", "Emotional"];
export const SEG_KINDS = ["In-ring Promo", "Backstage Segment", "Contract Signing", "Sit-down Interview", "Talk Show Segment"];

/* ---------------- THE EVENT GENERATOR (sheet page: Possible Events) ---------------- */
export const EVENTS = [
  { id: "dui", cat: "Legal/PR", name: "DUI Arrest", desc: "Suspended 2 months. Any championship held is vacated immediately.", buyout: 2500000, w: 2, eff: { kind: "Suspended — DUI", weeks: 8, reducible: true, vacate: true } },
  { id: "assault", cat: "Legal/PR", name: "Public Assault", desc: "Suspended 2 months. Any championship held is vacated immediately.", buyout: 3000000, w: 2, eff: { kind: "Suspended — assault", weeks: 8, reducible: true, vacate: true } },
  { id: "noshow", cat: "Legal/PR", name: "No Call, No Show", desc: "Will miss your next 4 shows. The office is furious.", buyout: 1000000, w: 2, eff: { kind: "AWOL — sent home", weeks: 4, reducible: true } },
  { id: "majinj", cat: "Injury/Absence", name: "Major Injury", desc: "Injured 4+ months.", buyout: 4000000, w: 2, eff: { kind: "Major Injury", weeks: 18, reducible: true, vacate: true } },
  { id: "mininj", cat: "Injury/Absence", name: "Minor Injury", desc: "Injured 2 months.", buyout: 2000000, w: 3, eff: { kind: "Minor Injury", weeks: 8, reducible: true } },
  { id: "leave", cat: "Injury/Absence", name: "Personal Leave", desc: "1 month absence.", buyout: 600000, w: 3, eff: { kind: "Personal Leave", weeks: 4, reducible: false } },
  { id: "wellness", cat: "Injury/Absence", name: "Wellness Policy Violation", desc: "2 month suspension. Any championship held is vacated.", buyout: 2000000, w: 2, eff: { kind: "Wellness Suspension", weeks: 8, reducible: false, vacate: true } },
  { id: "movie", cat: "Injury/Absence", name: "Movie Role", desc: "Hollywood calls — gone 2 months filming.", buyout: 2500000, w: 2, eff: { kind: "Filming a Movie", weeks: 8, reducible: false } },
  { id: "pregnancy", cat: "Injury/Absence", name: "Pregnancy", desc: "Out roughly 6 months. Cannot be reduced or bought out. Congratulations!", noBuyout: true, womenOnly: true, w: 1, eff: { kind: "Maternity Leave", weeks: 24, reducible: false, vacate: true } },
  { id: "renewal", cat: "Roster/Contract", name: "Contract Renewal Dispute", desc: "Wants the bag. Double their salary, pay a one-time signing bonus to smooth it over, or let them walk into free agency.", buyout: 2000000, w: 2, special: "renewal" },
  { id: "walkout", cat: "Roster/Contract", name: "Creative Walkout", desc: "Unhappy with creative — they're walking out for a month unless you pay them off.", buyout: 1200000, w: 2, eff: { kind: "Creative Walkout", weeks: 4, reducible: false } },
  { id: "hot", cat: "Creative/Feud", name: "Hot Crowd Reaction", desc: "They are OVER. Popularity spikes and merch flies off the shelves.", noBuyout: true, positive: true, w: 4 },
  { id: "turn", cat: "Creative/Feud", name: "Unexpected Turn", desc: "Creative shake-up — the fans demand they flip alignment tonight.", buyout: 750000, w: 3, special: "turn" },
  { id: "brother", cat: "Backstage Politics", name: "That Doesn't Work For Me, Brother", desc: "Backstage politics: they're refusing to do the job. They must WIN their next 4 matches — book around it or pay the fine.", buyout: 1500000, w: 1, special: "mandate-win" },
  { id: "montreal", cat: "Backstage Politics", name: "Montreal Screwjob", desc: "You must screw this wrestler out of a championship match THIS month — or management settles their contract for $10M.", buyout: 5000000, w: 1, special: "montreal" },
  { id: "favor", cat: "Business/Financial", name: "Network Favoritism", desc: "TV demands a push: they must WIN their next 4 matches.", buyout: 1500000, w: 2, special: "mandate-win" },
  { id: "interfere", cat: "Business/Financial", name: "Network Interference", desc: "TV demands you cool them off: they must LOSE their next 4 matches.", buyout: 1500000, w: 2, special: "mandate-lose" },
];
export const REDUCE_COST = 500000; // per month, per the sheet — pregnancy cannot be reduced

/* ---------------- sponsor objective templates ---------------- */
export const OBJ_TEMPLATES = [
  { t: "rating", text: (s) => `${s} wants a show rated 8.0+ this month`, check: (L) => L.ratings.some((r) => r >= 8) },
  { t: "banger", text: (s) => `${s} demands a 9.0+ rated match this month`, check: (L) => L.bestMatch >= 90 },
  { t: "defense", text: (s) => `${s} wants championship gold defended on TV`, check: (L) => L.titleDefenses >= 1 },
  { t: "face", text: (s) => `${s} wants a babyface standing tall in a main event`, check: (L) => L.faceMainWins >= 1 },
  { t: "heel", text: (s) => `${s} wants a dominant heel main-event win`, check: (L) => L.heelMainWins >= 1 },
  { t: "clean", text: (s) => `${s} insists every main event ends clean this month`, check: (L) => L.shows > 0 && L.dirtyMains === 0 },
  { t: "sellout", text: (s) => `${s} wants a 90%+ sellout crowd at least once`, check: (L) => L.selloutHit },
  { t: "star", text: (s, x) => `${s} wants ${x} featured in a match this month`, needsStar: true, check: (L, o) => (L.featured[o.star] || 0) >= 1 },
  { t: "contender", text: (s) => `${s} wants a #1 Contender match booked`, check: (L) => L.contenderMatches >= 1 },
  { t: "grow", text: (s) => `${s} wants brand popularity trending UP this month`, check: (L) => L.popEnd > L.popStart },
  { t: "blowoff", text: (s, x, e) => `${s} wants a feud PAID OFF at ${e}`, pleOnly: true, check: (L) => L.blowoffs >= 1 },
];

/* ---------------- brand themes (carried over from the BFG color language) ---------------- */
export const THEME = {
  /* WCW — black · dark red · gold · steel grey */
  wcw: { primary: "#d4af37", accent: "#8b0000", glow: "#8b0000", deep: "#170608", grad: "linear-gradient(135deg,#1c0608 0%,#000000 70%)", text: "#b8bec8" },
  /* SmackDown — black · electric blue · red accent · silver */
  sd: { primary: "#00a3ff", accent: "#e11d2e", glow: "#00a3ff", deep: "#04101f", grad: "linear-gradient(135deg,#051226 0%,#000000 70%)", text: "#d3d8de" },
  /* NXT — black · electric purple · silver · gold accent */
  nxt: { primary: "#b026ff", accent: "#d4af37", glow: "#b026ff", deep: "#140521", grad: "linear-gradient(135deg,#180626 0%,#000000 70%)", text: "#d3d8de" },
};

/* ================================================================
   ROSTERS — straight from the Universe Draft sheet.
   [name, division, alignment, OVR, salary($K), opts]
   ================================================================ */
const W = (n, div, al, ovr, salK, o = {}) => ({
  id: slug(n), name: n, div, al, ovr, sal: salK * 1000,
  sex: o.sex || "M", type: o.team ? "t" : "s", fac: o.fac || null, guest: !!o.guest,
  pop: clamp(ovr, 40, 100), mom: 50, sta: o.sta || 80, fat: 0, w: 0, l: 0, status: null, merchHot: 0,
  mor: 60, yrs: o.yrs || 2, bio: "", deb: true, lastBooked: 0, angryWks: 0, wants: null, holdout: false, form: [], cool: {},
  rs: o.rs || 0, ps: o.ps || 0, psych: o.psych || 0, cha: o.cha || 0, members: o.members || [],
});

const WCW_ROSTER = [
  // World division
  W("Triple H", "World", "H", 94, 5000, { fac: "The Kliq" }),
  W("The Rock", "World", "F", 95, 5000),
  W("Cody Rhodes", "World", "F", 92, 5000),
  W("Bray Wyatt", "World", "N", 91, 900, { fac: "Wyatt 6" }),
  W("Drew McIntyre", "World", "F", 91, 1500, { fac: "Combat Club" }),
  W("Bret Hart", "World", "F", 93, 1000, { fac: "Hart Foundation" }),
  W("Goldberg", "World", "F", 92, 1000),
  W("Finn Balor", "World", "H", 89, 800, { fac: "Judgement Day" }),
  W("Jey Uso", "World", "F", 88, 600),
  W("Bronson Reed", "World", "H", 86, 700, { fac: "Bloodline" }),
  W("Mark Henry", "World", "H", 85, 750),
  W("Jordan Burroughs", "World", "F", 84, 500),
  W("Jordan Walker", "World", "F", 87, 2000, { fac: "Team Jordan" }),
  W("Omos", "World", "H", 82, 700, { fac: "New Era" }),
  W("Baron Corbin", "World", "H", 83, 400),
  W("Ridge Holland", "World", "F", 80, 250, { fac: "British Strong Style" }),
  // United States division
  W("Solo Sikoa", "United States", "H", 87, 800, { fac: "Bloodline" }),
  W("Bron Breakker", "United States", "N", 90, 900),
  W("Carmelo Hayes", "United States", "N", 88, 700),
  W("Rob Van Dam", "United States", "F", 88, 750),
  W("Mick Foley", "United States", "F", 88, 800),
  W("Bam Bam Bigelow", "United States", "F", 86, 450),
  W("Brian Pillman", "United States", "H", 85, 550),
  W("Sid Justice", "United States", "H", 84, 350),
  W("Faarooq", "United States", "N", 83, 500, { fac: "WCW Originals" }),
  W("Carlito", "United States", "H", 82, 500, { fac: "Judgement Day" }),
  W("Shawn Spears", "United States", "H", 80, 250, { fac: "Kings of Wrestling" }),
  W("Giovanni Vinci", "United States", "H", 79, 200),
  W("Paragon Jay Pierce", "United States", "H", 78, 250),
  W("El Ordinario", "United States", "F", 77, 300),
  // Television division
  W("Shawn Michaels", "Television", "H", 93, 1500, { fac: "The Kliq" }),
  W("Ilja Dragunov", "Television", "F", 89, 800, { fac: "British Strong Style" }),
  W("Andrade", "Television", "F", 87, 700),
  W("Lex Luger", "Television", "N", 86, 500, { fac: "WCW Originals" }),
  W("Andre Walker", "Television", "H", 85, 800, { fac: "New Era" }),
  W("Ken Shamrock", "Television", "F", 84, 650),
  W("Karrion Kross", "Television", "H", 84, 600),
  W("Ludwig Kaiser", "Television", "H", 84, 400),
  W("Wes Lee", "Television", "H", 84, 500),
  W("Bo Dallas", "Television", "N", 83, 500, { fac: "Wyatt 6" }),
  W("Ethan Page", "Television", "H", 83, 500, { fac: "Kings of Wrestling" }),
  W("Matt Cardona", "Television", "F", 82, 400),
  W("Apollo Crews", "Television", "F", 82, 300),
  W("Lexis King", "Television", "H", 81, 400, { fac: "Kings of Wrestling" }),
  W("Royce Keys", "Television", "H", 80, 500),
  W("D'Lo Brown", "Television", "F", 80, 500),
  // Cruiserweight division
  W("Eddie Guerrero", "Cruiserweight", "H", 92, 1500, { fac: "LWO" }),
  W("Rey Mysterio", "Cruiserweight", "F", 91, 2500, { fac: "LWO" }),
  W("Penta", "Cruiserweight", "H", 88, 700),
  W("El Hijo de Vikingo", "Cruiserweight", "H", 88, 700),
  W("Dragon Lee", "Cruiserweight", "F", 86, 500, { fac: "LWO" }),
  W("Pete Dunne", "Cruiserweight", "F", 86, 500, { fac: "British Strong Style" }),
  W("Tyler Bate", "Cruiserweight", "F", 86, 400, { fac: "British Strong Style" }),
  W("Dom Mysterio", "Cruiserweight", "H", 85, 750, { fac: "Judgement Day" }),
  W("Octagon Jr", "Cruiserweight", "F", 84, 450),
  W("X-Pac", "Cruiserweight", "H", 82, 500, { fac: "The Kliq" }),
  W("JD McDonagh", "Cruiserweight", "H", 81, 500, { fac: "Judgement Day" }),
  W("Hector Flores", "Cruiserweight", "F", 76, 200),
  W("Cole Quinn", "Cruiserweight", "F", 76, 100),
  W("Chosen", "Cruiserweight", "H", 75, 100),
  // Tag division (units)
  W("The Outsiders", "Tag Team", "H", 90, 1600, { team: true, fac: "The Kliq" }),
  W("War Raiders", "Tag Team", "F", 86, 1000, { team: true }),
  W("New Day", "Tag Team", "H", 85, 950, { team: true, fac: "New Era" }),
  W("Hart Foundation", "Tag Team", "F", 85, 800, { team: true, fac: "Hart Foundation" }),
  W("The Dudley Boyz", "Tag Team", "F", 85, 1000, { team: true }),
  W("The Bloodline", "Tag Team", "H", 86, 500, { team: true, fac: "Bloodline" }),
  W("Wyatt 6", "Tag Team", "N", 84, 1150, { team: true, fac: "Wyatt 6" }),
  W("WCW Originals", "Tag Team", "N", 84, 1300, { team: true, fac: "WCW Originals" }),
  W("Kings of Wrestling", "Tag Team", "H", 83, 750, { team: true, fac: "Kings of Wrestling" }),
  W("Combat Club", "Tag Team", "F", 83, 700, { team: true, fac: "Combat Club" }),
  W("Billy Gunn & Road Dogg", "Tag Team", "H", 83, 1000, { team: true }),
  W("Psycho Clown & Pagano", "Tag Team", "H", 83, 600, { team: true }),
  W("Haku & Tama", "Tag Team", "F", 82, 1000, { team: true }),
  W("Team Jordan", "Tag Team", "F", 81, 900, { team: true, fac: "Team Jordan" }),
  W("LWO (Cruz & Wilde)", "Tag Team", "F", 82, 500, { team: true, fac: "LWO" }),
  W("No Quarter Catch Crew", "Tag Team", "H", 80, 400, { team: true }),
  W("Briggs & Jensen", "Tag Team", "H", 78, 500, { team: true }),
  // Women
  W("Scarlett", "Women", "H", 82, 100, { sex: "F" }),
  W("Zelina Vega", "Women", "F", 81, 250, { sex: "F" }),
  W("Nikki Cross", "Women", "N", 80, 100, { sex: "F" }),
  W("Stacy Keibler", "Women", "F", 79, 250, { sex: "F" }),
  W("Valhalla", "Women", "H", 78, 100, { sex: "F" }),
  // Special attraction
  W("Shaq", "Special", "F", 80, 1000, { guest: true }),
];

const SD_ROSTER = [
  // Undisputed division
  W("Undertaker", "Undisputed", "F", 97, 10000),
  W("Stone Cold Steve Austin 01'", "Undisputed", "N", 97, 10000),
  W("La'Quarius Jones", "Undisputed", "F", 95, 3000),
  W("Hollywood Hulk Hogan", "Undisputed", "N", 93, 7000),
  W("Randy Orton", "Undisputed", "N", 92, 7000),
  W("Logan Paul", "Undisputed", "H", 90, 5000),
  W("Booker T", "Undisputed", "F", 90, 5500),
  W("Boogeyman", "Undisputed", "H", 89, 4000),
  W("Kurt Angle", "Undisputed", "H", 89, 5000),
  W("Tony D'Angelo", "Undisputed", "H", 84, 1000),
  // North American division
  W("Batista 08'", "North American", "F", 91, 6500),
  W("DDP", "North American", "H", 91, 5500),
  W("Macho Man", "North American", "H", 89, 3000),
  W("Sheamus", "North American", "F", 88, 2700),
  W("Yokozuna", "North American", "H", 87, 2500),
  W("Kane", "North American", "N", 87, 4000),
  W("Trick Williams", "North American", "F", 84, 1000),
  W("Je'Von Evans", "North American", "F", 83, 1000),
  W("Andre Chase", "North American", "F", 80, 400),
  W("The Hurricane", "North American", "N", 80, 500),
  // Tag division
  W("Steiner Brothers", "Tag Team", "H", 85, 1000, { team: true }),
  W("La Parka & Mr. Iguana", "Tag Team", "N", 84, 400, { team: true }),
  W("Fraxiom", "Tag Team", "F", 83, 700, { team: true }),
  W("Hank & Tank", "Tag Team", "F", 83, 300, { team: true }),
  W("Noam Dar & Rey Fenix", "Tag Team", "N", 82, 350, { team: true }),
  W("Hurricane Chase", "Tag Team", "F", 80, 400, { team: true }),
  W("Street Profits", "Tag Team", "F", 79, 800, { team: true }),
  W("Noam Dar & Oro Mensah", "Tag Team", "N", 78, 300, { team: true }),
  W("The Family", "Tag Team", "H", 78, 300, { team: true }),
  W("Cedric & Ashante", "Tag Team", "F", 77, 300, { team: true }),
  // Women's World division
  W("Becky Lynch", "Women's World", "F", 94, 7500, { sex: "F" }),
  W("Liv Morgan", "Women's World", "H", 92, 5500, { sex: "F" }),
  W("Giulia", "Women's World", "F", 90, 3000, { sex: "F" }),
  W("Bayley", "Women's World", "N", 90, 3500, { sex: "F" }),
  W("Ava Moreno", "Women's World", "F", 90, 2000, { sex: "F" }),
  W("Alexa Bliss", "Women's World", "F", 89, 3500, { sex: "F" }),
  W("Zaria", "Women's World", "N", 89, 600, { sex: "F" }),
  W("Natalya", "Women's World", "H", 85, 1500, { sex: "F" }),
  W("Piper Niven", "Women's World", "H", 82, 400, { sex: "F" }),
  W("Maxxine Dupri", "Women's World", "F", 82, 500, { sex: "F" }),
  W("Jacy Jayne", "Women's World", "H", 82, 500, { sex: "F" }),
  // Women's U.S. division
  W("Lash Legend", "Women's U.S.", "N", 88, 2500, { sex: "F" }),
  W("Raquel", "Women's U.S.", "N", 88, 2500, { sex: "F" }),
  W("Chelsea Green", "Women's U.S.", "H", 87, 3500, { sex: "F" }),
  W("Eve Torres", "Women's U.S.", "H", 87, 3800, { sex: "F" }),
  W("Diana Vegas", "Women's U.S.", "F", 87, 500, { sex: "F" }),
  W("Kelani Jordan", "Women's U.S.", "F", 86, 2000, { sex: "F" }),
  W("Lyra Valkyria", "Women's U.S.", "F", 86, 2700, { sex: "F" }),
  W("Lola Vice", "Women's U.S.", "F", 84, 1500, { sex: "F" }),
  W("Tatum Paxley", "Women's U.S.", "F", 84, 2000, { sex: "F" }),
  W("Tegan Nox", "Women's U.S.", "H", 83, 600, { sex: "F" }),
  W("Wendy Choo", "Women's U.S.", "H", 81, 400, { sex: "F" }),
  W("Jazmyn Nyx", "Women's U.S.", "H", 80, 300, { sex: "F" }),
  // Guest stars
  W("KSI", "Guest", "N", 85, 900, { guest: true }),
  W("Glorilla", "Guest", "F", 85, 600, { sex: "F", guest: true }),
  W("Bad Bunny", "Guest", "F", 82, 1000, { guest: true }),
];

const NXT_ROSTER = [
  // Crown Jewel division
  W("Raven", "Crown Jewel", "N", 97, 3000),
  W("Roman Reigns", "Crown Jewel", "N", 96, 5000, { fac: "De Bloodline" }),
  W("Christian Rose", "Crown Jewel", "N", 96, 7000, { fac: "The Disciples" }),
  W("Seth Rollins", "Crown Jewel", "N", 95, 5000, { fac: "SHIELD" }),
  W("Brock Lesnar", "Crown Jewel", "H", 95, 3000),
  W("CM Punk", "Crown Jewel", "N", 94, 3000),
  W("Shinsuke Nakamura", "Crown Jewel", "F", 94, 2000),
  W("Gunther", "Crown Jewel", "H", 94, 2000),
  W("AJ Styles", "Crown Jewel", "F", 94, 2000, { fac: "Bullet Club" }),
  W("John Cena", "Crown Jewel", "F", 94, 5000),
  W("Bobby Roode", "Crown Jewel", "H", 94, 2000),
  W("Kevin Owens", "Crown Jewel", "N", 93, 2000),
  W("Sami Zayn", "Crown Jewel", "F", 92, 2000),
  W("Jacob Fatu", "Crown Jewel", "N", 92, 950, { fac: "De Bloodline" }),
  // Intercontinental division
  W("Abyss", "Intercontinental", "H", 93, 1000),
  W("Jeff Hardy", "Intercontinental", "F", 93, 1000),
  W("Chad Gable", "Intercontinental", "F", 92, 3000, { fac: "American MADE" }),
  W("LA Knight", "Intercontinental", "N", 92, 950),
  W("Oba Femi", "Intercontinental", "N", 92, 850, { fac: "The Disciples" }),
  W("Miro", "Intercontinental", "N", 92, 1000),
  W("Malakai Black", "Intercontinental", "H", 91, 900),
  W("Austin Theory", "Intercontinental", "N", 90, 800, { fac: "The MIZFITS" }),
  W("Damian Priest", "Intercontinental", "H", 90, 800),
  W("Ricky Saints", "Intercontinental", "F", 89, 500),
  W("The Miz", "Intercontinental", "H", 88, 800, { fac: "The MIZFITS" }),
  W("Tyler Breeze", "Intercontinental", "N", 88, 750, { fac: "Fashion Police" }),
  W("Santos Escobar", "Intercontinental", "H", 87, 400, { fac: "Fantasma" }),
  // Tag division
  W("The Hardys", "Tag Team", "F", 93, 1500, { team: true }),
  W("Domlishes", "Tag Team", "H", 92, 800, { team: true }),
  W("DIY", "Tag Team", "F", 91, 1500, { team: true }),
  W("American Made", "Tag Team", "F", 90, 800, { team: true, fac: "American MADE" }),
  W("A Town Under", "Tag Team", "N", 89, 1200, { team: true, fac: "The MIZFITS" }),
  W("De Bloodline", "Tag Team", "N", 89, 1200, { team: true, fac: "De Bloodline" }),
  W("MCMG", "Tag Team", "F", 89, 1000, { team: true }),
  W("Pretty Deadly", "Tag Team", "H", 88, 600, { team: true, fac: "Fashion Police" }),
  W("Los Lotharios", "Tag Team", "H", 86, 600, { team: true, fac: "Fantasma" }),
  W("Alpha Academy", "Tag Team", "F", 86, 700, { team: true, fac: "American MADE" }),
  // Women's division
  W("Asuka", "Women's", "N", 92, 800, { sex: "F" }),
  W("Rhea Ripley", "Women's", "F", 92, 1000, { sex: "F" }),
  W("Lani Rose", "Women's", "N", 90, 3500, { sex: "F" }),
  W("Charlotte Flair", "Women's", "N", 90, 1000, { sex: "F" }),
  W("Bianca Belair", "Women's", "H", 90, 3000, { sex: "F" }),
  W("Trish Stratus", "Women's", "F", 89, 800, { sex: "F" }),
  W("IYO SKY", "Women's", "F", 88, 900, { sex: "F" }),
  W("Tiffany Stratton", "Women's", "H", 88, 2000, { sex: "F" }),
  W("Nikki Bella", "Women's", "H", 88, 400, { sex: "F" }),
  W("Brie Bella", "Women's", "F", 88, 400, { sex: "F" }),
  W("Stephanie Vaquer", "Women's", "F", 87, 800, { sex: "F" }),
  W("Jaida Parker", "Women's", "F", 86, 500, { sex: "F" }),
  W("Alba Fyre", "Women's", "H", 86, 400, { sex: "F" }),
  W("Zoey Stark", "Women's", "H", 84, 400, { sex: "F" }),
  W("Nikkita Lyons", "Women's", "N", 83, 400, { sex: "F" }),
  // Women's N.A. division
  W("Mariah May", "Women's N.A.", "N", 91, 800, { sex: "F" }),
  W("Jordan Grace", "Women's N.A.", "F", 90, 800, { sex: "F" }),
  W("Nia Jax", "Women's N.A.", "H", 89, 650, { sex: "F" }),
  W("Roxanne Perez", "Women's N.A.", "H", 89, 900, { sex: "F" }),
  W("Lita", "Women's N.A.", "N", 88, 800, { sex: "F" }),
  W("Kairi Sane", "Women's N.A.", "F", 87, 850, { sex: "F" }),
  W("Jade Cargill", "Women's N.A.", "H", 86, 2000, { sex: "F" }),
  W("Kelly Kelly", "Women's N.A.", "F", 86, 300, { sex: "F" }),
  W("Naomi", "Women's N.A.", "F", 85, 850, { sex: "F" }),
  W("Candice LeRae", "Women's N.A.", "F", 85, 300, { sex: "F" }),
  W("Fallon", "Women's N.A.", "F", 85, 200, { sex: "F" }),
  W("Sol Ruca", "Women's N.A.", "F", 84, 750, { sex: "F" }),
  W("Thea Hail", "Women's N.A.", "F", 82, 200, { sex: "F" }),
];

/* ---------------- brand configs (sponsors + caps from the sheet) ---------------- */
export const BRAND_CONFIG = {
  wcw: {
    key: "wcw", name: "WCW", show: "Monday Night Nitro", owner: "Stephanie McMahon", owner2: "Shane McMahon", gm: "Teddy Long", homeMarket: "atl", tourMarket: "clt",
    commentary: "Michael Cole · Corey Graves · Jim Ross", announcer: "Michael Buffer",
    cap: 150000000, startCash: 20000000, baseline: 3000000, arena: 15000, pleArena: 19000,
    matchFormat: "5–8 matches · 3 promos · 2 backstage",
    minTV: 5,
    roster: WCW_ROSTER,
    titles: [
      { id: "wcw-world", name: "World Heavyweight Championship", champ: "triple-h" },
      { id: "wcw-us", name: "United States Title", champ: "solo-sikoa" },
      { id: "wcw-tag", name: "World Tag Team Championship", champ: "the-outsiders" },
      { id: "wcw-tv", name: "WCW Television Title", champ: "shawn-michaels" },
      { id: "wcw-cw", name: "Cruiserweight Title", champ: "eddie-guerrero" },
    ],
    sponsors: [
      { n: "CBS", v: 130, media: true }, { n: "ESPN 2 / Deportes", v: 65, media: true },
      { n: "ESPN+", v: 120, media: true }, { n: "Amazon Prime", v: 200, media: true },
      { n: "Adidas", v: 50 }, { n: "Pepsi / Gatorade", v: 55 }, { n: "EA Sports", v: 48 },
      { n: "McDonald's", v: 25 }, { n: "Microsoft", v: 40 }, { n: "Mercedes / Tesla", v: 45, perk: "transport" },
      { n: "Funko / Topps / Panini", v: 68 },
    ],
    perkNote: "Mercedes/Tesla cover all transportation costs.",
  },
  sd: {
    key: "sd", name: "SmackDown", show: "Friday Night SmackDown", owner: "Ric Flair", gm: "Ava", homeMarket: "stl", tourMarket: "pitt",
    commentary: "Eric Collins · Ernie Johnson · Dick Vitale", announcer: "Mike Walczewski",
    cap: 150000000, startCash: 20000000, baseline: 3000000, arena: 15000, pleArena: 19000,
    matchFormat: "5 matches (Season 1 format)",
    minTV: 5,
    roster: SD_ROSTER,
    titles: [
      { id: "sd-world", name: "Undisputed WWE Championship", champ: "undertaker" },
      { id: "sd-na", name: "N.A. Championship", champ: null, note: "TBD — Tournament" },
      { id: "sd-tag", name: "World Tag Team Championship", champ: null, note: "TBD — Tournament" },
      { id: "sd-ww", name: "Women's World Championship", champ: null, note: "TBD — Tournament" },
      { id: "sd-wus", name: "Women's U.S. Championship", champ: null, note: "TBD — Title Match" },
    ],
    sponsors: [
      { n: "USA Network", v: 50, media: true }, { n: "TNT", v: 85, media: true }, { n: "Paramount+", v: 150, media: true },
      { n: "PRIME", v: 45 }, { n: "New Balance", v: 100 }, { n: "Snickers", v: 65 }, { n: "Pringles", v: 40 },
      { n: "CHASE", v: 110 }, { n: "Samsung", v: 200 }, { n: "Hasbro / Bandai Namco", v: 60 },
      { n: "Marriott", v: 185, perk: "hotel" }, { n: "Sony", v: 350 },
    ],
    perkNote: "Marriott covers all hotel costs.",
  },
  nxt: {
    key: "nxt", name: "NXT", show: "NXT", owner: "Eric Bischoff", gm: "Eric Bischoff", homeMarket: "msg", tourMarket: "msg",
    commentary: "Mauro Ranallo · Pat McAfee · Jerry Lawler / R-Truth", announcer: "Samantha Irvin",
    cap: 150000000, startCash: 20000000, baseline: 3000000, arena: 15000, pleArena: 19000,
    matchFormat: "5–6 matches · panel-driven build",
    minTV: 5,
    roster: NXT_ROSTER,
    titles: [
      { id: "nxt-cj", name: "NXT Crown Jewels Title", champ: null, note: "Place Holder — crown a champion" },
      { id: "nxt-ic", name: "I.C. Title", champ: null, note: "Place Holder — crown a champion" },
      { id: "nxt-tag", name: "World Tag Team Championship", champ: null, note: "Place Holder — crown champions" },
      { id: "nxt-w", name: "Women's Title", champ: null, note: "Place Holder — crown a champion" },
      { id: "nxt-wna", name: "Women's N.A. Title", champ: null, note: "Place Holder — crown a champion" },
    ],
    sponsors: [
      { n: "Netflix", v: 250, media: true }, { n: "FOX FS1/FS2", v: 40, media: true },
      { n: "Rockstar", v: 500 }, { n: "Hasbro / Bandai (Toys)", v: 350 }, { n: "Coca-Cola", v: 120 },
      { n: "Monster", v: 50 }, { n: "Under Armour", v: 50 }, { n: "Nike", v: 150 }, { n: "DraftKings", v: 75 },
      { n: "World Cup", v: 5 }, { n: "Olympic Games", v: 5 },
    ],
    perkNote: "NXT pays full hotel + transportation (no logistics sponsor).",
  },
};
export const BRAND_KEYS = ["wcw", "sd", "nxt"];

/* ================================================================
   ENGINE
   ================================================================ */
export const freshMonthLog = (pop) => ({
  shows: 0, ratings: [], bestMatch: 0, titleDefenses: 0, faceMainWins: 0, heelMainWins: 0,
  dirtyMains: 0, selloutHit: false, featured: {}, contenderMatches: 0, blowoffs: 0,
  popStart: pop, popEnd: pop, titlesTouched: {},
});

export const emptyBooking = () => ({ matches: [], segments: [], cashIn: null, market: null, script: { mode: "quick", text: "", grade: null } });

/** Travel for a booked stop — intl costs more; domestic is flat for every brand. */
export function marketTravel(mk) {
  if (!mk) return LOCAL_TRAVEL;
  if (mk.tier === "intl") return mk.travel;
  return LOCAL_TRAVEL;
}

/** Same venue size for every brand — only the market you pick changes capacity/price. */
export function venueSeats(isPLE, stadium, mk) {
  const base = stadium ? VENUE.stadium : isPLE ? VENUE.ple : VENUE.tv;
  return Math.round(base * (mk?.att || 1));
}

/** Gate multiplier — bad shows empty the building; great storytelling packs the house. */
export function gatePerformanceMult(rating, linkedFrac, storyScore, script) {
  const continuity = 0.88 + storyScore / 450;
  const show = 0.52 + rating * 0.085 + linkedFrac * 0.14 + (script ? script.score / 280 : 0);
  return clamp(continuity * show, 0.38, 1.5);
}

function computeBaseMargin(brand, bKey) {
  const cfg = BRAND_CONFIG[bKey];
  const mkRef = MARKETS.find((x) => x.id === DEFAULT_MARKET) || MARKETS[0];
  const perfGate = gatePerformanceMult(7, 0.5, brand.storyScore, null);
  const attEst = Math.round(venueSeats(false, false, mkRef) * 0.65 * perfGate);
  const gate = Math.round(attEst * TICKET.tv * mkRef.price * perfGate);
  const merch = Math.round(attEst * (16 + 7 * 1.6) * (brand.pop / 75));
  const tvMoney = Math.round((mediaAnnualM(brand) * 1e6) / 52);
  const sponsorWeekly = Math.round(
    brand.sponsors.filter((s) => !s.media && s.v > 0).reduce((sum, sp) => sum + ((sp.v / 12) * 1e6 * 0.65 * 0.5) / 4, 0)
  );
  const hasHotel = brand.sponsors.some((s) => s.perk === "hotel");
  const hasTransport = brand.sponsors.some((s) => s.perk === "transport");
  const logistics =
    (hasHotel ? 0 : LOGISTICS.hotel) + (hasTransport ? 0 : LOGISTICS.transport + marketTravel(mkRef)) +
    LOGISTICS.medical + LOGISTICS.catering + LOGISTICS.insurance +
    LOGISTICS.adsTV + LOGISTICS.activationTV + LOGISTICS.media;
  const adRev = Math.round(cfg.baseline * 1.05);
  const rev = gate + merch + tvMoney + adRev + sponsorWeekly;
  const cost = Math.round(payrollWeekly(brand)) + PRODUCTION.tv + logistics;
  return rev > 0 ? (rev - cost) / rev : 0.15;
}

export function ensureUnitStats(u) {
  if (!u) return u;
  const ovr = u.ovr || 75;
  u.rs = u.rs || clamp(ovr - 4, 40, 99);
  u.ps = u.ps || clamp(ovr - 6, 35, 99);
  u.psych = u.psych ?? clamp(ovr - 3, 40, 99);
  u.cha = u.cha ?? clamp(Math.round(u.pop || ovr), 30, 100);
  u.sta = u.sta || 80;
  u.pop = u.pop ?? clamp(ovr, 40, 100);
  return u;
}

export function buildInitialState() {
  const brands = {};
  BRAND_KEYS.forEach((k) => {
    const cfg = BRAND_CONFIG[k];
    const units = clone(cfg.roster);
    units.forEach((u) => {
      u.yrs = 1 + ri(0, 2);
      u.rs = u.rs || clamp(u.ovr + ri(-7, 4), 40, 99);
      u.ps = u.ps || clamp(u.ovr + ri(-9, 6), 35, 99);
      u.psych = u.psych ?? clamp(u.ovr + ri(-5, 3), 40, 99);
      u.cha = u.cha ?? clamp((u.pop || u.ovr) + ri(-6, 8), 30, 100);
      u.members = u.members || [];
      ensureUnitStats(u);
    });
    const top = [...units].sort((a, b) => b.ovr - a.ovr).slice(0, 15);
    const pop = Math.round(top.reduce((s, u) => s + u.pop, 0) / top.length) - 8;
    brands[k] = {
      key: k,
      units,
      cash: cfg.startCash,
      titles: clone(cfg.titles),
      feuds: [],
      sponsors: cfg.sponsors.map((s, i) => ({ id: k + "-sp-" + i, ...s, rel: 65, paused: false })),
      objectives: [],
      objStats: { done: 0, total: 0 },
      pop, startPop: pop,
      fanInv: 50,
      viewership: cfg.baseline, startViewership: cfg.baseline,
      fillHist: [], firstFill: null, lastFill: null,
      storyScore: 50,
      pleRatings: [],
      monthLog: freshMonthLog(pop),
      ledger: [],
      revenueTotal: 0, costTotal: 0,
      recentMatchups: [],
      mandates: [],
      pendingScrewjob: null,
      activeEvent: null,
      lastResult: null,
      showCount: 0,
      viewHist: [],
      social: [],
      images: { logo: "", owner: "", owner2: "", gm: "", titles: {}, units: {}, staff: {} },
      staff: defaultStaff(k),
      podcast: k === "nxt" ? { name: "NXT Unfiltered" } : null,
      podBoost: 0, podWeek: 0, lastPod: null,
      oppCd: {},
      prevRanks: {},
    };
  });
  BRAND_KEYS.forEach((k) => { brands[k].baseMargin = computeBaseMargin(brands[k], k); });
  BRAND_KEYS.forEach((k) => {
    brands[k].results = [];
    brands[k].fiveShow = !!BRAND_CONFIG[k].extraPLE;
    brands[k].titles.forEach((t) => {
      t.defs = 0;
      t.history = t.champ ? [{ champId: t.champ, name: unitById(brands[k], t.champ)?.name || "?", start: 1, d: 0 }] : [];
    });
  });
  return {
    ver: 4,
    screen: "setup",
    players: { wcw: "", sd: "", nxt: "" },
    season: 1,
    freeAgents: [],
    trades: [],
    history: [],
    cases: [],
    calendar: clone(SEASON).map((c) => {
      const events = {};
      BRAND_KEYS.forEach((k) => {
        const on = c.host === k || !!c.all;
        events[k] = { on, ple: on ? c.ple : "", arena: "", location: "", theme: "", stadium: on ? !!c.stadium : false };
      });
      return { month: c.month, events, host: c.host, all: !!c.all, ple: c.ple };
    }),
    week: 1,
    activeBrand: "wcw",
    locked: { wcw: false, sd: false, nxt: false },
    booking: { wcw: { ...emptyBooking(), market: DEFAULT_MARKET }, sd: { ...emptyBooking(), market: DEFAULT_MARKET }, nxt: { ...emptyBooking(), market: DEFAULT_MARKET } },
    brands,
    news: [],
    seasonOver: false,
    awards: null,
    champion: null,
  };
}

export const unitById = (brand, id) => brand.units.find((u) => u.id === id) || null;
export const activeUnits = (brand) => brand.units.filter((u) => !u.status && u.deb !== false && !u.holdout);
export const unitAvailable = (u) => !u.status && u.deb !== false && !u.holdout;
export const titleHeldBy = (brand, unitId) => brand.titles.filter((t) => t.champ === unitId);

export function pushNews(state, bKey, text, kind = "info") {
  state.news.unshift({ id: Date.now() + "-" + Math.random().toString(36).slice(2, 7), week: state.week, brand: bKey, text, kind });
  if (state.news.length > 80) state.news.length = 80;
}

export function payrollWeekly(brand) {
  return brand.units.reduce((s, u) => s + u.sal, 0) / 52;
}
export function capUsed(brand) {
  return brand.units.reduce((s, u) => s + u.sal, 0);
}
export function mediaAnnualM(brand) {
  return brand.sponsors.filter((s) => s.media).reduce((s, x) => s + x.v, 0);
}

/* ---- feud helpers ---- */
export function findFeud(brand, aIds, bIds) {
  return brand.feuds.find((f) => !f.done && ((aIds.includes(f.aId) && bIds.includes(f.bId)) || (aIds.includes(f.bId) && bIds.includes(f.aId))));
}
export const getSides = (m) => (m.sides && m.sides.length ? m.sides : [m.sideA || [], m.sideB || []]);
export function findFeudMulti(brand, sides) {
  for (let i = 0; i < sides.length; i++) for (let j = i + 1; j < sides.length; j++) {
    const f = findFeud(brand, sides[i], sides[j]);
    if (f) return f;
  }
  return null;
}
export const matchKeyV4 = (m) => getSides(m).flat().sort().join("|") + "|" + m.stip;

export function sideStats(brand, ids) {
  const us = ids.map((id) => unitById(brand, id)).filter(Boolean);
  if (!us.length) return { ovr: 0, rs: 0, psych: 0, cha: 0, pop: 0, mom: 50, fat: 0, morAdj: 0, als: [], units: [] };
  return {
    ovr: us.reduce((s, u) => s + u.ovr, 0) / us.length,
    rs: us.reduce((s, u) => s + (u.rs || u.ovr - 4), 0) / us.length,
    psych: us.reduce((s, u) => s + (u.psych ?? u.ovr - 3), 0) / us.length,
    cha: us.reduce((s, u) => s + (u.cha ?? u.pop), 0) / us.length,
    pop: us.reduce((s, u) => s + u.pop, 0) / us.length,
    mom: us.reduce((s, u) => s + u.mom, 0) / us.length,
    fat: Math.max(...us.map((u) => u.fat)),
    morAdj: us.reduce((s, u) => s + ((u.mor ?? 60) < 25 ? -5 : (u.mor ?? 60) < 40 ? -2 : (u.mor ?? 60) > 80 ? 1 : 0), 0) / us.length,
    als: us.map((u) => u.al),
    units: us,
  };
}

export function matchQuality(brand, m, opts) {
  const rawSides = getSides(m);
  const sides = rawSides.map((ids) => sideStats(brand, ids)).filter((s) => s.units.length);
  const n = Math.max(sides.length, 1);
  const avg = (k) => sides.reduce((s, x) => s + x[k], 0) / n;
  const rs = avg("rs"), ovr = avg("ovr"), pop = avg("pop"), mom = avg("mom"), psych = avg("psych");
  /* Work rate carries the match; psychology helps long-form storytelling. */
  let q = rs * 0.34 + ovr * 0.18 + pop * 0.12 + psych * 0.12 + mom * 0.08 - 2;
  q += avg("morAdj");
  const als = sides.flatMap((s) => s.als);
  const hasF = als.includes("F"), hasH = als.includes("H");
  if (hasF && hasH) q += 3;
  else if (als.includes("N")) q += 1;
  else q -= 2;
  const feud = findFeudMulti(brand, rawSides);
  if (feud) q += feud.heat * 0.10;
  const stip = STIPS.find((s) => s.id === m.stip) || STIPS[0];
  q += stip.b;
  if (n > 2) q += 2 + Math.min(n - 2, 4); // multi-man spotfest bonus
  if (m.titleId) q += 2;
  if (m.contender) q += 2;
  if (m.notes && m.notes.trim().length >= 80) q += 1; // produced match
  if (opts.isPLE) q += 3;
  if (opts.isMain) q += 2;
  const key = matchKeyV4(m);
  const repeats = brand.recentMatchups.filter((r) => r.key === key && opts.week - r.week <= 4).length;
  q -= repeats * 5;
  const maxFat = Math.max(...sides.map((s) => s.fat), 0);
  if (maxFat >= 60) q -= 3;
  q += rnd(-4, 4);
  return { q: clamp(Math.round(q), 35, 99), feud, repeats, stip, sides: rawSides, key };
}

function feudBetweenSegment(brand, speakerId, targetId) {
  if (!speakerId || !targetId) return null;
  return findFeud(brand, [speakerId], [targetId]);
}

export function segQuality(brand, seg) {
  const sp = unitById(brand, seg.speakerId);
  if (!sp) return { q: 50, feud: null };
  /* Promo skill + charisma carry the segment; psychology helps emotional beats. */
  let q = (sp.ps || sp.ovr - 6) * 0.38 + (sp.cha ?? sp.pop) * 0.22 + (sp.psych ?? sp.ovr - 3) * 0.10 + sp.pop * 0.08 + sp.mom * 0.08 - 2;
  if (seg.tone === "Heel Heat" && sp.al === "H") q += 3;
  if (seg.tone === "Emotional" && sp.al === "F") q += 3;
  if (seg.tone === "Call-out" && seg.targetId) q += 2;
  const feud = feudBetweenSegment(brand, seg.speakerId, seg.targetId);
  if (feud) q += feud.heat * 0.06;
  q += rnd(-4, 4);
  return { q: clamp(Math.round(q), 30, 99), feud };
}

/* ---- title reign bookkeeping ---- */
function closeReign(title, week) {
  const h = title.history || (title.history = []);
  const open = h[h.length - 1];
  if (open && !open.end) open.end = week;
}
function openReign(title, champId, name, week) {
  (title.history || (title.history = [])).push({ champId, name, start: week, d: 0 });
}

/* ---- THE SHOW ---- */
export function simulateShow(state, bKey) {
  const brand = state.brands[bKey];
  const cfg = BRAND_CONFIG[bKey];
  const week = state.week;
  const mIdx = monthIdxOf(week);
  const ev = brandEvent(state, mIdx, bKey);
  const hostPLE = !!(isPLEWeek(week) && ev);
  const twoShow = hostPLE && (brand.fiveShow ?? !!cfg.extraPLE);
  const tvDoneAlready = twoShow && (brand.results || []).some((r) => r.week === week && (r.season || 1) === (state.season || 1));
  const isPLE = hostPLE && (!twoShow || tvDoneAlready);
  const stadium = isPLE && !!(ev && ev.stadium);
  const booking = state.booking[bKey];
  const mk = MARKETS.find((x) => x.id === booking.market) || MARKETS.find((x) => x.id === DEFAULT_MARKET) || MARKETS[0];
  const L = brand.monthLog;
  const lines = [];
  const matchResults = [];
  let heatNotes = [];
  let showDefenses = 0;

  /* matches */
  booking.matches.forEach((m, i) => {
    const isMain = i === booking.matches.length - 1;
    const { q, feud, repeats, stip } = matchQuality(brand, m, { isPLE, isMain, week });
    const sides = getSides(m);
    const wIdx = clamp(parseInt(m.winner, 10) || 0, 0, sides.length - 1);
    const winnerIds = m.finish === "No Contest" ? [] : sides[wIdx] || [];
    const loserIds = m.finish === "No Contest" ? [] : sides.filter((_, ix) => ix !== wIdx).flat();
    const all = sides.flat();
    const isBR = stip.id === "battleroyal";
    all.forEach((id) => {
      const u = unitById(brand, id); if (!u) return;
      u.fat = clamp(u.fat + Math.round((10 + stip.fat * 5) * ((115 - (u.sta || 80)) / 35)), 0, 100);
      L.featured[id] = (L.featured[id] || 0) + 1;
    });
    winnerIds.forEach((id) => {
      const u = unitById(brand, id); if (!u) return;
      u.w += 1; u.mom = clamp(u.mom + 8, 0, 100);
      u.pop = clamp(u.pop + (q >= 85 ? 2 : 1), 30, 100);
      u.mor = clamp((u.mor ?? 60) + 3 + (isMain || m.titleId ? 2 : 0), 0, 100);
      u.lastBooked = week;
      u.form = [...(u.form || []), { wk: week, q, win: true, main: !!isMain, title: !!m.titleId }];
    });
    loserIds.forEach((id) => {
      const u = unitById(brand, id); if (!u) return;
      u.l += 1; u.mom = clamp(u.mom - (isBR ? 3 : 6), 0, 100);
      if (m.finish === "Clean" && !isBR) u.pop = clamp(u.pop - 1, 30, 100);
      u.mor = clamp((u.mor ?? 60) - (isBR ? 1 : 3) - (isMain && !isBR ? 2 : 0), 0, 100);
      u.lastBooked = week;
      u.form = [...(u.form || []), { wk: week, q, win: false, main: !!isMain, title: !!m.titleId }];
    });

    /* title logic + reign tracking */
    let titleNote = null;
    if (m.titleId) {
      const title = brand.titles.find((t) => t.id === m.titleId);
      if (title) {
        L.titlesTouched[title.id] = true;
        const champInMatch = title.champ && all.includes(title.champ);
        if (!title.champ) {
          if (m.finish === "Clean" || m.finish === "Screwjob") {
            if (winnerIds.length) {
              title.champ = winnerIds[0]; title.note = null;
              closeReign(title, week);
              openReign(title, winnerIds[0], unitById(brand, winnerIds[0])?.name || "?", week);
              titleNote = `${unitById(brand, winnerIds[0]).name} crowned NEW ${title.name} champion!`;
              brand.fanInv = clamp(brand.fanInv + 4, 0, 100);
            }
          } else titleNote = `${title.name} remains vacant — no decisive winner.`;
        } else if (champInMatch) {
          const champWon = winnerIds.includes(title.champ);
          if (champWon || m.finish === "DQ" || m.finish === "No Contest") {
            L.titleDefenses += 1; showDefenses += 1; title.defs = (title.defs || 0) + 1;
            const open = (title.history || [])[Math.max(0, (title.history || []).length - 1)];
            if (open && !open.end) open.d = (open.d || 0) + 1;
            titleNote = `${unitById(brand, title.champ)?.name} retains the ${title.name}${m.finish !== "Clean" ? " (" + m.finish + ")" : ""}.`;
          } else {
            const oldU = unitById(brand, title.champ);
            const old = oldU?.name;
            if (oldU) oldU.mor = clamp((oldU.mor ?? 60) - 6, 0, 100);
            closeReign(title, week);
            title.champ = winnerIds[0] || title.champ;
            openReign(title, title.champ, unitById(brand, title.champ)?.name || "?", week);
            const newU = unitById(brand, title.champ);
            if (newU) newU.mor = clamp((newU.mor ?? 60) + 8, 0, 100);
            titleNote = `TITLE CHANGE — ${unitById(brand, title.champ)?.name} defeats ${old} for the ${title.name}!`;
            brand.fanInv = clamp(brand.fanInv + 3, 0, 100);
          }
        }
      }
    }

    /* themed PLE payoffs */
    if (isPLE && m.mitb && ev && ev.theme === "mitb" && winnerIds.length) {
      const wu = unitById(brand, winnerIds[0]);
      const tgt = brand.titles[0];
      if (wu && tgt && !(state.cases || []).some((c) => c.holderId === wu.id)) {
        (state.cases = state.cases || []).push({ id: "c" + Date.now(), name: ev.ple + " Briefcase", holderId: wu.id, titleId: tgt.id, brandKey: bKey });
        heatNotes.push(`💼 ${wu.name} wins the ${ev.ple} briefcase — a shot at the ${tgt.name}, any time.`);
        addPost(state, bKey, { kind: "pundit", name: "Squared Circle SZN", handle: "@SquaredCircleSZN", text: `${wu.name} has the BRIEFCASE. Every ${tgt.name} match just got must-watch. #${cfg.name.replace(/\W/g, "")}`, viral: true });
      }
    }
    if (isPLE && m.rumble && ev && ev.theme === "rumble" && winnerIds.length) {
      const wu = unitById(brand, winnerIds[0]);
      if (wu) {
        wu.mom = clamp(wu.mom + 15, 0, 100);
        heatNotes.push(`🏆 ${wu.name} wins the ${ev.ple} match — punching a main-event ticket.`);
        pushNews(state, bKey, `🏆 ${wu.name} is going to the main event scene — ${ev.ple} winner.`, "good");
      }
    }

    /* feud */
    if (feud) {
      feud.lastTouched = week;
      if (isPLE && m.blowoff) {
        L.blowoffs += 1;
        brand.fanInv = clamp(brand.fanInv + Math.round(feud.heat / 12), 0, 100);
        brand.storyScore = clamp(brand.storyScore + 5, 0, 100);
        heatNotes.push(`BLOWOFF: ${feud.label} paid off at ${ev.ple} (heat ${Math.round(feud.heat)}).`);
        feud.done = true;
      } else {
        feud.heat = clamp(feud.heat + ri(8, 14), 0, 100);
      }
    }

    /* mandates */
    brand.mandates = brand.mandates.filter((md) => {
      if (!all.includes(md.unitId)) return true;
      const won = winnerIds.includes(md.unitId);
      const nm = unitById(brand, md.unitId)?.name;
      if ((md.type === "win" && !won) || (md.type === "lose" && won)) {
        brand.cash -= 2000000;
        brand.ledger.push({ week, label: `Network fine — ${nm} mandate violated`, amt: -2000000 });
        pushNews(state, bKey, `The network fined ${cfg.name} $2.00M — ${nm} mandate violated.`, "bad");
        return false;
      }
      md.remaining -= 1;
      if (md.remaining <= 0) { pushNews(state, bKey, `${nm}'s network mandate fulfilled.`, "good"); return false; }
      return true;
    });

    /* montreal fulfillment */
    if (brand.pendingScrewjob && m.titleId && m.finish === "Screwjob" && loserIds.includes(brand.pendingScrewjob.unitId)) {
      const tgt = unitById(brand, brand.pendingScrewjob.unitId);
      tgt.status = { kind: "Furious — gone", weeks: 8, reducible: false };
      titleHeldBy(brand, tgt.id).forEach((t) => { closeReign(t, week); t.champ = null; t.note = "Vacated — screwjob fallout"; });
      heatNotes.push(`MONTREAL SCREWJOB executed on ${tgt.name}. They've left the building for 8 weeks.`);
      brand.pendingScrewjob = null;
      brand.storyScore = clamp(brand.storyScore + 3, 0, 100);
    }

    if (m.contender) L.contenderMatches += 1;
    if (isMain && m.finish !== "Clean") L.dirtyMains += 1;
    if (isMain && m.finish === "Clean" && winnerIds.length) {
      const wAl = unitById(brand, winnerIds[0])?.al;
      if (wAl === "F") L.faceMainWins += 1;
      if (wAl === "H") L.heelMainWins += 1;
    }
    if (q > L.bestMatch) L.bestMatch = q;
    brand.recentMatchups.push({ key: matchKeyV4(m), week });
    const sideNames = sides.map((ids) => ids.map((id) => unitById(brand, id)?.name).filter(Boolean).join(" & "));
    matchResults.push({
      names: isBR ? `${all.length}-Entrant Battle Royal` : sideNames.join(" vs "),
      q, isMain, stip: stip.n, finish: m.finish,
      winner: winnerIds.length ? winnerIds.map((id) => unitById(brand, id)?.name).join(" & ") : "—",
      titleNote, feudLinked: !!feud, repeats,
      notes: m.notes && m.notes.trim() ? m.notes.trim().slice(0, 300) : null,
    });
  });

  /* Money in the Bank cash-in */
  if (booking.cashIn && booking.cashIn.caseId) {
    const c = (state.cases || []).find((x) => x.id === booking.cashIn.caseId);
    const holder = c ? unitById(brand, c.holderId) : null;
    const title = c ? brand.titles.find((t) => t.id === c.titleId) : null;
    const champ = title && title.champ ? unitById(brand, title.champ) : null;
    if (c && holder && title && champ && unitAvailable(holder) && c.brandKey === bKey) {
      const cq = clamp(Math.round(((holder.rs || holder.ovr) + (champ.rs || champ.ovr)) / 2 + rnd(-2, 6)), 40, 99);
      const success = booking.cashIn.winner !== "champ";
      let note;
      if (success) {
        closeReign(title, week);
        champ.mor = clamp((champ.mor ?? 60) - 8, 0, 100);
        title.champ = holder.id;
        openReign(title, holder.id, holder.name, week);
        holder.mom = clamp(holder.mom + 12, 0, 100);
        holder.mor = clamp((holder.mor ?? 60) + 10, 0, 100);
        holder.w += 1; champ.l += 1;
        note = `💼 CASH-IN! ${holder.name} cashes in on ${champ.name} and WINS the ${title.name}!`;
        brand.fanInv = clamp(brand.fanInv + 6, 0, 100);
      } else {
        holder.mom = clamp(holder.mom - 8, 0, 100);
        holder.l += 1; champ.w += 1;
        title.defs = (title.defs || 0) + 1;
        note = `💼 FAILED CASH-IN — ${champ.name} survives ${holder.name}'s ${c.name}!`;
      }
      state.cases = state.cases.filter((x) => x.id !== c.id);
      heatNotes.push(note);
      matchResults.push({ names: `💼 ${holder.name} cashes in on ${champ.name}`, q: cq, isMain: false, stip: "Cash-In", finish: "Clean", winner: success ? holder.name : champ.name, titleNote: note, feudLinked: false, repeats: 0, notes: null });
      pushNews(state, bKey, note, "good");
      addPost(state, bKey, { kind: "brand", name: cfg.name + " (Official)", handle: handleOf(cfg.name), text: note + " The landscape just CHANGED.", viral: true });
    }
    booking.cashIn = null;
  }

  /* segments */
  const segResults = booking.segments.map((sg) => {
    const { q, feud } = segQuality(brand, sg);
    const sp = unitById(brand, sg.speakerId);
    if (sp) { sp.mom = clamp(sp.mom + 3, 0, 100); L.featured[sp.id] = (L.featured[sp.id] || 0) + 1; }
    if (feud) { feud.heat = clamp(feud.heat + ri(6, 10), 0, 100); feud.lastTouched = week; }
    return { who: sp?.name || "?", kind: sg.kind, tone: sg.tone, q, feudLinked: !!feud, target: sg.targetId ? unitById(brand, sg.targetId)?.name : null };
  });

  /* show rating */
  const linked = matchResults.filter((r) => r.feudLinked).length;
  const linkedFrac = matchResults.length ? linked / matchResults.length : 0;
  let wSum = 0, wTot = 0;
  matchResults.forEach((r) => { const w = r.isMain ? 1.5 : 1; wSum += r.q * w; wTot += w; });
  const matchAvg = wTot ? wSum / wTot : 50;
  const script = booking.script && booking.script.mode === "script" && booking.script.grade ? booking.script.grade : null;
  const segAvg = segResults.length ? segResults.reduce((s, r) => s + r.q, 0) / segResults.length : matchAvg - 2;
  /* one combined grade: in script mode the AI's whole-show creative grade folds into the rating */
  let r100 = script ? matchAvg * 0.55 + script.score * 0.45 : matchAvg * 0.78 + segAvg * 0.22;
  if (brand.podBoost) {
    r100 += brand.podBoost;
    lines.push(`🎙 ${(brand.podcast && brand.podcast.name) || "The podcast"} buzz lifted the show.`);
    brand.podBoost = 0;
  }
  r100 += linkedFrac * 5 - (1 - linkedFrac) * 3;
  if (booking.matches.length < cfg.minTV) r100 -= (cfg.minTV - booking.matches.length) * 4;
  if (isPLE) {
    r100 -= 4;
    r100 += Math.min(L.blowoffs, 3) * 2.5;
  }
  const rating = clamp(Math.round((r100 / 10) * 10) / 10, 1, 10);

  /* audience — attendance and viewership follow the show you put on + your ongoing story */
  const prevView = brand.viewership;
  const viewStory = (brand.storyScore - 50) * 0.0012;
  brand.viewership = Math.round(clamp(brand.viewership * (1 + viewPct(rating) + viewStory), VIEW_FLOOR, VIEW_CEIL));
  const avgHeat = brand.feuds.filter((f) => !f.done).reduce((s, f) => s + f.heat, 0) / Math.max(1, brand.feuds.filter((f) => !f.done).length);
  const capSeats = venueSeats(isPLE, stadium, mk);
  const fill = clamp(0.30 + brand.pop / 280 + rating / 36 + brand.storyScore / 300 + (avgHeat || 0) / 420 + (isPLE ? 0.06 : 0), 0.22, 1);
  const att = Math.round(capSeats * fill);
  if (fill >= 0.9) L.selloutHit = true;
  if (brand.firstFill === null) brand.firstFill = fill;
  brand.lastFill = fill;
  const selloutTag = fill >= 0.97 ? "SELLOUT" : fill >= 0.9 ? "Near Sellout" : fill >= 0.8 ? "Strong Crowd" : fill >= 0.65 ? "Decent House" : "Soft Crowd";
  booking.segments.forEach((sg) => { const su = unitById(brand, sg.speakerId); if (su) su.lastBooked = week; });

  /* money — gate scales with tonight's performance AND your continuity; TV/ad money still pays the bills */
  const ticketPrice = Math.round((stadium ? TICKET.stadium : isPLE ? TICKET.ple : TICKET.tv) * mk.price);
  const gateMult = gatePerformanceMult(rating, linkedFrac, brand.storyScore, script);
  const gate = Math.round(att * ticketPrice * gateMult);
  const merchHotFeatured = brand.units.some((u) => u.merchHot > 0 && L.featured[u.id]);
  const merch = Math.round(att * (16 + rating * 1.6) * (brand.pop / 75) * (merchHotFeatured ? 1.5 : 1));
  const viewFactor = clamp(brand.viewership / cfg.baseline, 0.6, 1.6);
  const tvMoney = Math.round((mediaAnnualM(brand) * 1e6) / 52 * viewFactor);
  const adRev = Math.round(brand.viewership * 1.05 * (rating / 7));
  const pleBonus = isPLE ? Math.round(2500000 * (rating / 7.5) * (stadium ? 2 : 1)) : 0;
  const production = stadium ? PRODUCTION.stadium : isPLE ? PRODUCTION.ple : PRODUCTION.tv;
  const hasHotelPerk = brand.sponsors.some((s) => s.perk === "hotel" && !s.paused);
  const hasTransportPerk = brand.sponsors.some((s) => s.perk === "transport" && !s.paused);
  const logistics =
    (hasHotelPerk ? 0 : LOGISTICS.hotel) + (hasTransportPerk ? 0 : LOGISTICS.transport + marketTravel(mk)) +
    LOGISTICS.medical + LOGISTICS.catering + LOGISTICS.insurance +
    (isPLE ? LOGISTICS.adsPLE : LOGISTICS.adsTV) + (isPLE ? LOGISTICS.activationPLE : LOGISTICS.activationTV) + LOGISTICS.media;
  const payroll = (twoShow && isPLE) ? 0 : Math.round(payrollWeekly(brand)); /* PLE-as-second-show: payroll already paid on TV night */
  const revenue = gate + merch + tvMoney + adRev + pleBonus;
  const costs = payroll + production + logistics;
  const net = revenue - costs;
  brand.cash += net;
  brand.revenueTotal += revenue; brand.costTotal += costs;
  brand.ledger.push({ week, label: `${isPLE ? ev.ple : cfg.show} ${mk.flag} ${mk.n.split(",")[0]}`, amt: net });

  /* brand meters */
  brand.pop = clamp(brand.pop + (rating - 6.5) * 0.6, 30, 95);
  brand.fanInv = clamp(brand.fanInv + (rating >= 8 ? 2 : 0) + (isPLE ? (rating - 6) * 2 : 0), 0, 100);
  const repeatHits = matchResults.reduce((s, r) => s + r.repeats, 0);
  brand.storyScore = clamp(
    brand.storyScore + linkedFrac * 6 - (1 - linkedFrac) * 2 + Math.min(showDefenses, 1) * 1.5 - Math.min(repeatHits, 2) + (rating >= 7.5 ? 1.5 : rating < 6 ? -1.5 : 0),
    0, 100
  );
  if (script) brand.storyScore = clamp(brand.storyScore + clamp((script.score - 60) / 12, -3, 4), 0, 100);
  if (isPLE) brand.pleRatings.push(rating);
  L.shows += 1; L.ratings.push(rating); L.popEnd = brand.pop;
  brand.viewHist.push({ week, v: brand.viewership });
  brand.showCount += 1;
  /* hot crowd merch decay tick happens weekly in advanceWeek */

  const result = {
    week, season: state.season || 1, isPLE, eventName: isPLE ? ev.ple : cfg.show, stadium,
    rating, grade: letter(rating * 10),
    matches: matchResults, segments: segResults,
    viewership: brand.viewership, viewDelta: brand.viewership - prevView,
    att, fill, selloutTag, capSeats, market: mk.n, marketFlag: mk.flag,
    gate, gateMult, merch, tvMoney, adRev, pleBonus, payroll, production, logistics, revenue, costs, net,
    linkedFrac, heatNotes, lines, script,
  };
  (brand.results = brand.results || []).push({
    week, season: state.season || 1, eventName: result.eventName, isPLE, rating, grade: result.grade,
    matches: matchResults, segments: segResults, script: script ? { score: script.score, verdict: script.verdict } : null,
    viewership: brand.viewership, att, selloutTag, net,
  });
  if (brand.results.length > 60) brand.results.splice(0, brand.results.length - 60);
  genShowSocial(state, bKey, result, ev);
  brand.lastResult = result;
  if (twoShow && !isPLE) {
    const keepMk = booking.market;
    state.booking[bKey] = { ...emptyBooking(), market: keepMk };
    pushNews(state, bKey, `📺 TV is in the books (${rating.toFixed(1)}/10) — ${ev.ple} still to come this week. Book it!`, "info");
  } else {
    state.locked[bKey] = true;
  }
  pushNews(state, bKey, `${result.eventName}: ${rating.toFixed(1)}/10 (${result.grade}) — ${fmtNum(brand.viewership)} viewers, ${selloutTag.toLowerCase()}.`, rating >= 8 ? "good" : rating < 6 ? "bad" : "info");
  return result;
}

/* ---- objectives ---- */
export function issueObjectives(state, bKey, mIdx) {
  const brand = state.brands[bKey];
  const products = brand.sponsors.filter((s) => !s.media && !s.paused && s.v > 0);
  if (!products.length) { brand.objectives = []; return; }
  const ev = brandEvent(state, mIdx, bKey);
  const hostsPLE = !!ev;
  const pool = OBJ_TEMPLATES.filter((t) => !t.pleOnly || hostsPLE);
  const objs = [];
  for (let i = 0; i < 3; i++) {
    const sp = pick(products);
    const tpl = pick(pool);
    const star = tpl.needsStar ? pick(activeUnits(brand)) : null;
    const monthlyM = sp.v / 12;
    objs.push({
      id: bKey + "-obj-" + mIdx + "-" + i,
      sponsor: sp.n, spId: sp.id, t: tpl.t,
      star: star ? star.id : null,
      text: tpl.text(sp.n, star ? star.name : "", ev ? ev.ple : ""),
      payout: Math.round(monthlyM * 1e6 * 0.5),
      done: false, scored: false,
    });
  }
  brand.objectives = objs;
}

export function monthEnd(state, bKey, mIdx) {
  const brand = state.brands[bKey];
  const L = brand.monthLog;
  let payoutTotal = 0, baseTotal = 0;
  const report = { month: calOf(state, mIdx).month, objectives: [], base: 0, payouts: 0, notes: [] };
  brand.objectives.forEach((o) => {
    const tpl = OBJ_TEMPLATES.find((t) => t.t === o.t);
    const ok = tpl ? !!tpl.check(L, o) : false;
    o.done = ok; o.scored = true;
    brand.objStats.total += 1;
    const sp = brand.sponsors.find((s) => s.id === o.spId);
    if (ok) {
      brand.objStats.done += 1; payoutTotal += o.payout;
      if (sp) sp.rel = clamp(sp.rel + 5, 0, 100);
    } else if (sp) sp.rel = clamp(sp.rel - 12, 0, 100);
    report.objectives.push({ text: o.text, done: ok, payout: ok ? o.payout : 0 });
  });
  brand.sponsors.forEach((sp) => {
    if (sp.media || sp.v <= 0) return;
    if (sp.paused) {
      sp.rel = clamp(sp.rel + 3, 0, 100);
      if (sp.rel >= 45) { sp.paused = false; report.notes.push(`${sp.n} contract reactivated — relationship repaired.`); }
      return;
    }
    if (sp.rel < 30) { sp.paused = true; report.notes.push(`${sp.n} PAUSED their contract — relationship too low.`); return; }
    baseTotal += Math.round((sp.v / 12) * 1e6 * (sp.rel / 100) * 0.5);
  });
  /* undefended titles */
  brand.titles.forEach((t) => {
    if (t.champ && !L.titlesTouched[t.id]) {
      brand.storyScore = clamp(brand.storyScore - 3, 0, 100);
      report.notes.push(`${t.name} sat in a duffel bag all month — story score dinged.`);
    }
  });
  /* montreal deadline */
  if (brand.pendingScrewjob && brand.pendingScrewjob.byMonth <= mIdx) {
    brand.cash -= 10000000;
    brand.ledger.push({ week: state.week, label: "Montreal demand ignored — forced settlement", amt: -10000000 });
    report.notes.push("You never pulled the trigger on the screwjob. Management settled for $10M.");
    brand.pendingScrewjob = null;
  }
  brand.cash += baseTotal + payoutTotal;
  if (baseTotal) brand.ledger.push({ week: state.week, label: "Sponsor base income (relationship-scaled)", amt: baseTotal });
  if (payoutTotal) brand.ledger.push({ week: state.week, label: "Sponsor objective bonuses", amt: payoutTotal });
  brand.revenueTotal += baseTotal + payoutTotal;
  report.base = baseTotal; report.payouts = payoutTotal;
  brand.lastMonthReport = report;
  pushNews(state, bKey, `${calOf(state, mIdx).month} close-out: ${report.objectives.filter(o => o.done).length}/${report.objectives.length} sponsor objectives hit — ${money(baseTotal + payoutTotal)} sponsor income.`, "info");
  brand.monthLog = freshMonthLog(brand.pop);
  if (mIdx + 1 < SEASON.length) issueObjectives(state, bKey, mIdx + 1);
}

/* ---- events ---- */
export function rollEvent(state, bKey) {
  if (Math.random() > 0.5) return;
  const brand = state.brands[bKey];
  if (brand.activeEvent) return;
  const bag = [];
  EVENTS.forEach((e) => { for (let i = 0; i < e.w; i++) bag.push(e); });
  let ev = pick(bag);
  let eligible = brand.units.filter((u) => !u.status && !u.guest && u.deb !== false);
  if (ev.womenOnly) eligible = eligible.filter((u) => u.sex === "F" && u.type === "s");
  if (!eligible.length) return;
  const unit = pick(eligible);
  brand.activeEvent = { evId: ev.id, unitId: unit.id, week: state.week };
  pushNews(state, bKey, `INCIDENT: ${ev.name} — ${unit.name}.`, ev.positive ? "good" : "bad");
}

export function applyEventChoice(state, bKey, choice) {
  const brand = state.brands[bKey];
  const ae = brand.activeEvent; if (!ae) return;
  const ev = EVENTS.find((e) => e.id === ae.evId);
  const u = unitById(brand, ae.unitId);
  if (!ev || !u) { brand.activeEvent = null; return; }
  const name = u.name;
  const pay = (amt, label) => { brand.cash -= amt; brand.ledger.push({ week: state.week, label, amt: -amt }); };
  if (choice === "buyout" && !ev.noBuyout) {
    pay(ev.buyout, `Buyout — ${ev.name} (${name})`);
    pushNews(state, bKey, `${BRAND_CONFIG[bKey].name} paid ${money(ev.buyout)} to make "${ev.name}" go away (${name}).`, "info");
  } else if (ev.positive) {
    u.pop = clamp(u.pop + 8, 30, 100); u.mom = clamp(u.mom + 10, 0, 100); u.merchHot = 8;
    pushNews(state, bKey, `${name} is WHITE HOT with the crowd — popularity and merch surging.`, "good");
  } else if (ev.special === "renewal") {
    if (choice === "double") {
      u.sal *= 2;
      pushNews(state, bKey, `${name} re-signed at DOUBLE money (${money(u.sal)}/yr).`, "info");
    } else if (choice === "walk") {
      titleHeldBy(brand, u.id).forEach((t) => { closeReign(t, state.week); t.champ = null; t.note = "Vacated — contract dispute"; });
      brand.units = brand.units.filter((x) => x.id !== u.id);
      state.freeAgents.push(toFreeAgent(u));
      pushNews(state, bKey, `${name} walked — now an UNRESTRICTED FREE AGENT.`, "bad");
    }
  } else if (ev.special === "turn") {
    u.al = u.al === "F" ? "H" : u.al === "H" ? "F" : pick(["F", "H"]);
    u.mom = clamp(u.mom + 10, 0, 100);
    pushNews(state, bKey, `${name} TURNED — now a ${u.al === "F" ? "babyface" : "heel"}.`, "info");
  } else if (ev.special === "montreal") {
    brand.pendingScrewjob = { unitId: u.id, byMonth: monthIdxOf(state.week) };
    pushNews(state, bKey, `Management demands you SCREW ${name} in a championship match THIS month.`, "bad");
  } else if (ev.special === "mandate-win" || ev.special === "mandate-lose") {
    brand.mandates.push({ unitId: u.id, type: ev.special === "mandate-win" ? "win" : "lose", remaining: 4 });
    pushNews(state, bKey, `Network mandate: ${name} must ${ev.special === "mandate-win" ? "WIN" : "LOSE"} their next 4 matches.`, "bad");
  } else if (ev.eff) {
    u.status = { kind: ev.eff.kind, weeks: ev.eff.weeks, reducible: !!ev.eff.reducible };
    if (ev.eff.vacate) {
      titleHeldBy(brand, u.id).forEach((t) => { closeReign(t, state.week); t.champ = null; t.note = "Vacated — " + ev.name; });
    }
    pushNews(state, bKey, `${name}: ${ev.eff.kind} — out ${ev.eff.weeks} weeks.`, "bad");
  }
  genEventSocial(state, bKey, ev, u, choice);
  brand.activeEvent = null;
}

export function reduceStatus(state, bKey, unitId) {
  const brand = state.brands[bKey];
  const u = unitById(brand, unitId);
  if (!u || !u.status || !u.status.reducible || brand.cash < REDUCE_COST) return;
  brand.cash -= REDUCE_COST;
  brand.ledger.push({ week: state.week, label: `Premium care — ${u.name} recovery accelerated`, amt: -REDUCE_COST });
  u.status.weeks = Math.max(1, u.status.weeks - 4);
  pushNews(state, bKey, `${u.name}'s timetable cut by a month (${u.status.weeks} wks left).`, "good");
}

/* ---- week advance ---- */
export function advanceWeek(state) {
  const wk = state.week;
  const mIdx = monthIdxOf(wk);
  BRAND_KEYS.forEach((bKey) => {
    const brand = state.brands[bKey];
    brand.units.forEach((u) => {
      u.fat = Math.max(0, u.fat - 12);
      if (u.merchHot > 0) u.merchHot -= 1;
      if (u.status) {
        u.status.weeks -= 1;
        if (u.status.weeks <= 0) { pushNews(state, bKey, `${u.name} is BACK.`, "good"); u.status = null; }
      }
      if (u.deb === false) return; // undebuted — morale frozen
      u.mor = clamp((u.mor ?? 60) + ((u.mor ?? 60) > 50 ? -0.5 : 0.5), 0, 100);
      if (!u.status && !u.guest && wk - (u.lastBooked || 0) >= 3) u.mor = clamp(u.mor - 4, 0, 100);
      if (u.mor < 25) {
        u.angryWks = (u.angryWks || 0) + 1;
        if (!u.wants) { u.wants = pick(["trade", "release"]); pushNews(state, bKey, `😡 ${u.name} has requested a ${u.wants}.`, "bad"); }
        if (u.angryWks >= 3 && !u.holdout) { u.holdout = true; pushNews(state, bKey, `🚫 ${u.name} is HOLDING OUT — unavailable until morale recovers.`, "bad"); }
      } else {
        u.angryWks = 0;
        if (u.mor >= 40) {
          if (u.wants) pushNews(state, bKey, `${u.name} has withdrawn their ${u.wants} request.`, "good");
          u.wants = null; u.holdout = false;
        } else if (u.holdout) { u.holdout = false; pushNews(state, bKey, `${u.name} grudgingly returns to work.`, "info"); }
      }
    });
    brand.feuds = brand.feuds.filter((f) => {
      if (f.done) return false;
      const idle = wk - f.lastTouched;
      if (idle >= 2) { f.heat = clamp(f.heat - 8, 0, 100); brand.storyScore = clamp(brand.storyScore - 1, 0, 100); }
      if (f.heat <= 0 || idle >= 5) {
        brand.storyScore = clamp(brand.storyScore - 4, 0, 100);
        pushNews(state, bKey, `Feud fizzled: ${f.label}. Fans noticed.`, "bad");
        return false;
      }
      return true;
    });
    brand.fanInv = clamp(brand.fanInv - 0.6, 0, 100);
    brand.recentMatchups = brand.recentMatchups.filter((r) => wk - r.week <= 5);
  });
  BRAND_KEYS.forEach((bKey) => {
    const br = state.brands[bKey];
    br.prevRanks = {};
    brandRankings(br).forEach((u, i) => { br.prevRanks[u.id] = i + 1; });
  });
  const wasPLEWeek = weekOfMonth(wk) === 4;
  if (wasPLEWeek) BRAND_KEYS.forEach((bKey) => monthEnd(state, bKey, mIdx));
  state.week = wk + 1;
  state.locked = { wcw: false, sd: false, nxt: false };
  const _mks = { wcw: state.booking?.wcw?.market || DEFAULT_MARKET, sd: state.booking?.sd?.market || DEFAULT_MARKET, nxt: state.booking?.nxt?.market || DEFAULT_MARKET };
  state.booking = { wcw: { ...emptyBooking(), market: _mks.wcw }, sd: { ...emptyBooking(), market: _mks.sd }, nxt: { ...emptyBooking(), market: _mks.nxt } };
  if (state.week > TOTAL_WEEKS) {
    state.seasonOver = true; state.screen = "seasonEnd";
    finishSeason(state);
    return;
  }
  if (wasPLEWeek) BRAND_KEYS.forEach((bKey) => rollEvent(state, bKey)); // fallout only lands after PLE weeks
}

/* ---- morale / contracts / free agency ---- */
export const moraleLabel = (m) => (m >= 70 ? ["😊 Pleased", "#22c55e"] : m >= 40 ? ["😐 Neutral", "#9ca3af"] : ["😡 Unhappy", "#ef4444"]);
export const toFreeAgent = (u) => ({ ...u, status: null, holdout: false, wants: null, fac: null, fat: 0, askBump: 0 });
export function faAsk(u) {
  const base = Math.round(Math.pow(1.6, (u.ovr - 60) / 5) * 600000);
  return Math.round(Math.max(base, u.sal * 0.9) * (0.8 + u.pop / 250) * (1 + (u.askBump || 0)));
}

export function releaseUnit(state, bKey, unitId) {
  const brand = state.brands[bKey];
  const u = unitById(brand, unitId);
  if (!u) return;
  const cost = Math.round(u.sal * 0.5);
  brand.cash -= cost;
  brand.ledger.push({ week: state.week, label: `Released ${u.name} — contract buyout`, amt: -cost });
  titleHeldBy(brand, u.id).forEach((t) => { closeReign(t, state.week); t.champ = null; t.note = "Vacated — released"; });
  brand.feuds.forEach((f) => { if (!f.done && (f.aId === u.id || f.bId === u.id)) { f.done = true; } });
  brand.mandates = brand.mandates.filter((md) => md.unitId !== u.id);
  if (brand.pendingScrewjob && brand.pendingScrewjob.unitId === u.id) brand.pendingScrewjob = null;
  if (brand.activeEvent && brand.activeEvent.unitId === u.id) brand.activeEvent = null;
  brand.units = brand.units.filter((x) => x.id !== u.id);
  state.freeAgents.push(toFreeAgent(u));
  pushNews(state, bKey, `${u.name} RELEASED (buyout ${money(cost)}) — hits the free agent market.`, "bad");
  addPost(state, bKey, { kind: "pundit", name: "Wrestle Economist", handle: "@WrestleEconomist", text: `${u.name} released by ${BRAND_CONFIG[bKey].name}. Buyout ${money(cost)}. Cap space opens — smart business or panic move?` });
}

export function signFreeAgent(state, bKey, faId, offer, yrs, success) {
  const brand = state.brands[bKey];
  const i = state.freeAgents.findIndex((x) => x.id === faId);
  if (i < 0) return;
  const u = state.freeAgents[i];
  if (!success) {
    u.askBump = (u.askBump || 0) + 0.04;
    u.cool = u.cool || {}; u.cool[bKey] = state.week + 2;
    pushNews(state, bKey, `${u.name} REJECTED ${BRAND_CONFIG[bKey].name}'s offer of ${money(offer)}/yr. Camp won't talk for 2 weeks.`, "bad");
    return;
  }
  state.freeAgents.splice(i, 1);
  const nu = { ...u, sal: offer, yrs, mor: 65, deb: true, lastBooked: state.week, w: 0, l: 0, form: [], askBump: 0, cool: {} };
  brand.units.push(nu);
  pushNews(state, bKey, `✍️ SIGNED: ${u.name} joins ${BRAND_CONFIG[bKey].name} — ${money(offer)}/yr × ${yrs}.`, "good");
  addPost(state, bKey, { kind: "pundit", name: "Squared Circle SZN", handle: "@SquaredCircleSZN", text: `BREAKING: ${u.name} signs with ${BRAND_CONFIG[bKey].name} — ${money(offer)}/yr. The landscape shifts.`, viral: true });
}

export function clearTheAir(state, bKey, unitId) {
  const brand = state.brands[bKey];
  const u = unitById(brand, unitId);
  if (!u || brand.cash < 500000) return;
  brand.cash -= 500000;
  brand.ledger.push({ week: state.week, label: `Sit-down with ${u.name} (catering upgrade + creative promises)`, amt: -500000 });
  u.mor = clamp((u.mor ?? 60) + 18, 0, 100);
  if (u.mor >= 25) { u.holdout = false; u.angryWks = 0; }
  if (u.mor >= 40) u.wants = null;
  pushNews(state, bKey, `${BRAND_CONFIG[bKey].name} management cleared the air with ${u.name}.`, "good");
}

/* ---- trades ---- */
export function tradePayrollCheck(state, t) {
  const A = state.brands[t.from], B = state.brands[t.to];
  const sal = (br, ids) => ids.reduce((s, id) => s + (unitById(br, id)?.sal || 0), 0);
  const aPost = capUsed(A) - sal(A, t.fromUnits) + sal(B, t.toUnits);
  const bPost = capUsed(B) - sal(B, t.toUnits) + sal(A, t.fromUnits);
  if (aPost > BRAND_CONFIG[t.from].cap) return `${BRAND_CONFIG[t.from].name} would be ${money(aPost - BRAND_CONFIG[t.from].cap)} over the cap.`;
  if (bPost > BRAND_CONFIG[t.to].cap) return `${BRAND_CONFIG[t.to].name} would be ${money(bPost - BRAND_CONFIG[t.to].cap)} over the cap.`;
  return null;
}

function moveUnitBetweenBrands(state, fromKey, toKey, unitId, week) {
  const from = state.brands[fromKey], to = state.brands[toKey];
  const u = unitById(from, unitId);
  if (!u) return null;
  titleHeldBy(from, u.id).forEach((t) => { closeReign(t, week); t.champ = null; t.note = "Vacated — traded"; });
  from.feuds.forEach((f) => { if (!f.done && (f.aId === u.id || f.bId === u.id)) { f.done = true; } });
  from.mandates = from.mandates.filter((md) => md.unitId !== u.id);
  if (from.pendingScrewjob && from.pendingScrewjob.unitId === u.id) from.pendingScrewjob = null;
  if (from.activeEvent && from.activeEvent.unitId === u.id) from.activeEvent = null;
  if (from.images.units[u.id]) { to.images.units[u.id] = from.images.units[u.id]; delete from.images.units[u.id]; }
  from.units = from.units.filter((x) => x.id !== u.id);
  u.fac = null; u.lastBooked = week;
  if (u.wants === "trade") { u.mor = 68; u.wants = null; u.holdout = false; u.angryWks = 0; }
  else u.mor = clamp((u.mor ?? 60) + 5, 0, 100);
  to.units.push(u);
  return u;
}

export function acceptTrade(state, tradeId) {
  const t = state.trades.find((x) => x.id === tradeId && x.status === "pending");
  if (!t) return;
  const A = state.brands[t.from], B = state.brands[t.to];
  const capErr = tradePayrollCheck(state, t);
  if (capErr) { t.status = "rejected"; t.reason = capErr; pushNews(state, t.to, `Trade voided — ${capErr}`, "bad"); return; }
  if (A.cash < t.fromCash || B.cash < t.toCash) { t.status = "rejected"; t.reason = "Insufficient cash."; pushNews(state, t.to, "Trade voided — insufficient cash.", "bad"); return; }
  const names = [];
  t.fromUnits.forEach((id) => { const u = moveUnitBetweenBrands(state, t.from, t.to, id, state.week); if (u) names.push(u.name + " → " + BRAND_CONFIG[t.to].name); });
  t.toUnits.forEach((id) => { const u = moveUnitBetweenBrands(state, t.to, t.from, id, state.week); if (u) names.push(u.name + " → " + BRAND_CONFIG[t.from].name); });
  A.cash -= t.fromCash; B.cash += t.fromCash;
  B.cash -= t.toCash; A.cash += t.toCash;
  if (t.fromCash) { A.ledger.push({ week: state.week, label: "Trade — cash out", amt: -t.fromCash }); B.ledger.push({ week: state.week, label: "Trade — cash in", amt: t.fromCash }); }
  if (t.toCash) { B.ledger.push({ week: state.week, label: "Trade — cash out", amt: -t.toCash }); A.ledger.push({ week: state.week, label: "Trade — cash in", amt: t.toCash }); }
  t.status = "accepted"; t.week = state.week;
  const line = names.join(" · ") || "cash considerations";
  pushNews(state, t.from, `🔁 TRADE COMPLETE: ${line}.`, "info");
  pushNews(state, t.to, `🔁 TRADE COMPLETE: ${line}.`, "info");
  addPost(state, t.to, { kind: "pundit", name: "Squared Circle SZN", handle: "@SquaredCircleSZN", text: `🚨 TRADE: ${line}. Wrestling twitter is COOKED tonight.`, viral: true });
}

export function rejectTrade(state, tradeId, reason) {
  const t = state.trades.find((x) => x.id === tradeId && x.status === "pending");
  if (!t) return;
  t.status = "rejected"; t.reason = reason || "Declined.";
  pushNews(state, t.from, `Trade offer to ${BRAND_CONFIG[t.to].name} was REJECTED.`, "bad");
}

/* ---- power rankings ---- */
export function powerScore(u) {
  const f = u.form || [];
  const last = f.slice(-5);
  const fq = last.length ? last.reduce((s, x) => s + x.q, 0) / last.length : u.ovr - 8;
  let streak = 0;
  for (let i = f.length - 1; i >= 0; i--) { if (f[i].win) streak++; else break; }
  const wins = last.filter((x) => x.win).length, losses = last.length - wins;
  return u.mom * 0.45 + u.pop * 0.2 + (fq - 55) * 0.55 + wins * 1.6 - losses * 1.1 + streak * 1.2;
}
export function brandRankings(brand) {
  return brand.units.filter((u) => u.deb !== false && !u.guest).map((u) => u).sort((a, b) => powerScore(b) - powerScore(a));
}

/* ---- exclusive brand opportunities (lanes mirror the BFG app) ---- */
export const OPPORTUNITIES = {
  wcw: [
    { id: "wcw-half", lane: "NBA / NFL Lane", name: "NFL Halftime Show", rev: 1200000, pop: 6, mom: 8, mor: 5, view: 90000, cd: 6, viral: true },
    { id: "wcw-espn", lane: "ESPN / CBS Sports Lane", name: "ESPN SportsCenter Segment", rev: 600000, pop: 4, mom: 5, mor: 3, view: 45000, cd: 4 },
    { id: "wcw-draft", lane: "Draft Pick Lane", name: "NBA Draft Desk Guest", rev: 450000, pop: 3, mom: 4, mor: 3, view: 25000, cd: 4 },
    { id: "wcw-belt", lane: "NBA / NFL Lane", name: "Belt Presented at a Sports Game", rev: 350000, pop: 5, mom: 5, mor: 4, view: 35000, cd: 5, champOnly: true },
  ],
  sd: [
    { id: "sd-grammy", lane: "Grammys / Music Awards Lane", name: "Grammys Appearance", rev: 1000000, pop: 6, mom: 7, mor: 5, view: 80000, cd: 6, viral: true },
    { id: "sd-vma", lane: "Grammys / Music Awards Lane", name: "MTV VMA Segment", rev: 650000, pop: 4, mom: 5, mor: 3, view: 45000, cd: 4 },
    { id: "sd-mv", lane: "Music Video / Concert Lane", name: "Music Video Cameo", rev: 500000, pop: 4, mom: 4, mor: 3, view: 30000, cd: 4 },
    { id: "sd-concert", lane: "Music Video / Concert Lane", name: "Concert Cameo Goes Viral", rev: 700000, pop: 5, mom: 6, mor: 4, view: 60000, cd: 5, viral: true },
  ],
  nxt: [
    { id: "nxt-netflix", lane: "Hollywood / Netflix Lane", name: "Netflix Show Cameo", rev: 1100000, pop: 6, mom: 7, mor: 5, view: 85000, cd: 6, viral: true },
    { id: "nxt-marvel", lane: "Marvel / DC Lane", name: "Marvel Cameo Offer", rev: 1000000, pop: 6, mom: 6, mor: 5, view: 70000, cd: 6 },
    { id: "nxt-snl", lane: "SNL / GMA / Olympics Lane", name: "SNL Sketch Invitation", rev: 700000, pop: 5, mom: 5, mor: 4, view: 50000, cd: 5 },
    { id: "nxt-comicon", lane: "Comic-Con / Toys / Merch Lane", name: "Comic-Con Panel Invite", rev: 450000, pop: 3, mom: 4, mor: 4, view: 25000, cd: 4 },
  ],
};

export function useOpportunity(state, bKey, oppId, unitId) {
  const brand = state.brands[bKey];
  const opp = OPPORTUNITIES[bKey].find((o) => o.id === oppId);
  const u = unitById(brand, unitId);
  if (!opp || !u) return;
  if ((brand.oppCd[oppId] || 0) > state.week) return;
  brand.oppCd[oppId] = state.week + opp.cd;
  brand.cash += opp.rev;
  brand.ledger.push({ week: state.week, label: `Exclusive: ${u.name} — ${opp.name}`, amt: opp.rev });
  brand.viewership = Math.round(clamp(brand.viewership + opp.view, VIEW_FLOOR, VIEW_CEIL));
  u.pop = clamp(u.pop + opp.pop, 30, 100);
  u.mom = clamp(u.mom + opp.mom, 0, 100);
  u.mor = clamp((u.mor ?? 60) + opp.mor, 0, 100);
  brand.sponsors.forEach((sp) => { if (!sp.media && sp.v > 0 && !sp.paused) sp.rel = clamp(sp.rel + 2, 0, 100); });
  pushNews(state, bKey, `🌟 EXCLUSIVE: ${u.name} — ${opp.name} (${money(opp.rev)} in, +pop/mom/morale).`, "good");
  addPost(state, bKey, { kind: "wrestler", name: u.name, handle: handleOf(u.name), unitId: u.id, text: `Big night — ${opp.name}. More eyes on me, more eyes on ${BRAND_CONFIG[bKey].name}.`, viral: !!opp.viral });
}

/* ---- podcast ---- */
export const PODCAST_REV = 200000;

export function applyPodcast(state, bKey, target, grade, transcript = "") {
  const brand = state.brands[bKey];
  brand.podWeek = state.week;
  brand.lastPod = { ...grade, target, week: state.week, transcript: transcript || "" };
  const podName = (brand.podcast && brand.podcast.name) || "The Podcast";
  brand.cash += PODCAST_REV;
  brand.ledger.push({ week: state.week, label: `${podName} — episode ad revenue`, amt: PODCAST_REV });
  if (target === "show") {
    brand.podBoost = clamp((grade.score - 50) / 4, 0, 12);
    pushNews(state, bKey, `🎙 ${podName} drops (${grade.score}/100) — buzz will lift the next show. +$${(PODCAST_REV / 1000).toFixed(0)}K ad revenue.`, "info");
  } else {
    const f = brand.feuds.find((x) => x.id === target && !x.done);
    if (f) {
      const bump = clamp((grade.score - 50) / 8, 0, 6);
      f.heat = clamp(f.heat + bump, 0, 100);
      pushNews(state, bKey, `🎙 ${podName} broke down ${f.label} (${grade.score}/100) — heat +${Math.round(bump)}. +$${(PODCAST_REV / 1000).toFixed(0)}K ad revenue.`, "info");
    }
  }
  addPost(state, bKey, { kind: "brand", name: podName, handle: handleOf(podName), text: `🎙 NEW EPISODE — "${grade.verdict || "the boys went deep this week."}"` });
}

const TTS_CONTRACTIONS = [
  [" do not ", " don't "], [" cannot ", " can't "], [" will not ", " won't "], [" did not ", " didn't "],
  [" is not ", " isn't "], [" are not ", " aren't "], [" was not ", " wasn't "], [" have not ", " haven't "],
  [" has not ", " hasn't "], [" would not ", " wouldn't "], [" should not ", " shouldn't "],
  [" could not ", " couldn't "], [" it is ", " it's "], [" that is ", " that's "], [" we are ", " we're "],
  [" they are ", " they're "], [" I am ", " I'm "], [" let us ", " let's "], [" going to ", " gonna "],
];

export function humanizeDialogueForTts(text) {
  if (!text) return "";
  let t = String(text).trim();
  for (const [a, b] of TTS_CONTRACTIONS) t = t.replace(new RegExp(a.trim(), "gi"), b);
  t = t.replace(/\bHost Name\b/gi, "").replace(/\s{2,}/g, " ").trim();
  return t;
}

/** Parse "Name: \"line\"" blocks (or paragraphs) into speaker lines for browser TTS. */
export function parsePodcastDialogue(script, hosts = []) {
  const hostNames = hosts.map((h) => (typeof h === "string" ? h : h.name)).filter(Boolean);
  const hostSet = new Set(hostNames.map((n) => n.toLowerCase()));
  const segs = [];
  if (!(script || "").trim()) return segs;

  const push = (speaker, text) => {
    const line = humanizeDialogueForTts(text);
    if (line.length >= 3) segs.push({ speaker: speaker.trim(), text: line });
  };

  const reMultiline = /^([A-Za-z][^\n:]{1,42}):\s*\n?"([^"]{3,2000})"/gm;
  const reInline = /^([A-Za-z][^\n:]{1,42}):\s*"([^"]{3,2000})"/gm;
  let m;
  for (const re of [reMultiline, reInline]) {
    while ((m = re.exec(script)) !== null) {
      const pair = { speaker: m[1].trim(), text: humanizeDialogueForTts(m[2].trim()) };
      if (pair.text.length >= 3 && !segs.some((s) => s.speaker === pair.speaker && s.text === pair.text)) {
        segs.push(pair);
      }
    }
  }
  if (segs.length) return segs.slice(0, 120);

  const rePlain = /^([A-Za-z][^\n:]{1,42}):\s+(.+)$/gm;
  while ((m = rePlain.exec(script)) !== null) {
    const sp = m[1].trim();
    const tx = m[2].trim().replace(/^["']|["']$/g, "");
    if (hostSet.size === 0 || hostSet.has(sp.toLowerCase())) push(sp, tx);
  }
  if (segs.length) return segs.slice(0, 120);

  const skip = /^(Episode Title|Host Lineup|Opening Intro|Story Recap|Closing Thoughts)\s*$/i;
  const chunks = script
    .replace(/^(Episode Title|Host Lineup|Opening Intro|Story Recap|Deep Story Analysis|Closing Thoughts)\s*$/gim, "")
    .split(/\n\n+/)
    .map((p) => p.trim())
    .filter((p) => p.length > 45 && !p.endsWith(":") && !skip.test(p));
  chunks.slice(0, 90).forEach((ch, i) => {
    push(hostNames[i % hostNames.length] || "Host", ch.slice(0, 1200));
  });
  return segs.slice(0, 120);
}

/** Per-host voice profiles — NotebookLM-style lenses + neural TTS mapping. */
export const PODCAST_TONES = [
  "emotional deep dive", "serious analyst", "debate show", "fan reaction",
  "business/media breakdown", "PLE fallout special", "locker room psychology", "funny but smart",
];
export const PODCAST_LENGTHS = ["Short (~4 min)", "Medium (~7 min)", "Full Episode (~10 min)", "Deep Dive (~12 min)"];
export const PODCAST_LENGTH_SPECS = {
  "Short (~4 min)": { target_minutes: 4, min_dialogue_chars: 2800, min_lines: 28, lines_per_section: 2 },
  "Medium (~7 min)": { target_minutes: 7, min_dialogue_chars: 5000, min_lines: 48, lines_per_section: 3 },
  "Full Episode (~10 min)": { target_minutes: 10, min_dialogue_chars: 7500, min_lines: 80, lines_per_section: 5 },
  "Deep Dive (~12 min)": { target_minutes: 12, min_dialogue_chars: 9500, min_lines: 100, lines_per_section: 6 },
};
export const PODCAST_TTS_PAUSE_MS = 720;

const EDGE_VOICE = {
  neutral: "en-US-JennyNeural", warm: "en-US-AriaNeural", deep: "en-US-GuyNeural", bright: "en-US-AnaNeural",
  energetic: "en-US-BrandonNeural", smooth: "en-US-RogerNeural", broadcast: "en-US-BrianNeural", "fan-debate": "en-US-ChristopherNeural",
};
const OPENAI_VOICE = {
  neutral: "nova", warm: "shimmer", deep: "onyx", bright: "nova", energetic: "echo", smooth: "fable", broadcast: "onyx", "fan-debate": "echo",
};

export const NXT_PODCAST_HOST_PROFILES = {
  "Maya Cruz": {
    gender: "Female", identity: "Emotional story analyst",
    podcast_role: "breaks down emotion, character pain, betrayal, redemption, and fan investment",
    personality: "thoughtful, sharp, empathetic, serious when needed",
    speaking_style: "calm, deep, emotionally intelligent",
    strengths: ["emotional intelligence", "empathy", "fan investment reads", "character psychology"],
    focuses_on: ["character emotions", "relationship drama", "betrayal", "morale", "fan sympathy"],
    bias: "leans toward emotional truth and fan sympathy",
    catchphrase: "Let us sit with what that moment actually cost them.",
    tts_voice: "warm", tts_speed: 0.94,
  },
  "Dre Walker": {
    gender: "Male", identity: "Fan voice / hot-take debate host",
    podcast_role: "says what fans online are probably thinking",
    personality: "loud, funny, passionate, unpredictable, emotional fan energy",
    speaking_style: "energetic, funny, dramatic, debate-style",
    strengths: ["fan reaction", "viral moment reads", "debate energy"],
    focuses_on: ["Twitter reaction", "fan outrage", "hype moments", "viral clips", "controversial tweets"],
    bias: "fan-first hot takes — loud but not clueless",
    catchphrase: "The timeline is not wrong — it is just early.",
    tts_voice: "fan-debate", tts_speed: 0.98,
  },
  "Tasha Monroe": {
    gender: "Female", identity: "Pop culture and media analyst",
    podcast_role: "connects NXT stories to Hollywood, Netflix, press, and media buzz",
    personality: "stylish, confident, witty, entertainment-focused",
    speaking_style: "fast, smart, celebrity/media aware",
    strengths: ["pop culture framing", "press and trend reads"],
    focuses_on: ["media appearances", "popularity", "Hollywood crossover", "sponsor reactions"],
    bias: "frames everything through mainstream entertainment optics",
    tts_voice: "bright", tts_speed: 0.96,
  },
  "Serena Vale": {
    gender: "Female", identity: "Former athlete / locker room psychology voice",
    podcast_role: "analyzes morale, backstage tension, contracts, creative frustration",
    personality: "direct, competitive, no-nonsense, protective of wrestlers",
    speaking_style: "blunt, honest, athletic, locker-room focused",
    strengths: ["locker room truth", "morale and contract reads"],
    focuses_on: ["morale", "contracts", "locker room tension", "burnout"],
    bias: "protects talent and calls out disrespect",
    tts_voice: "deep", tts_speed: 0.95,
  },
  "Marcus King": {
    gender: "Male", identity: "Wrestling historian and storyline critic",
    podcast_role: "judges whether the story makes sense week to week",
    personality: "analytical, intense, traditional wrestling mind",
    speaking_style: "serious, detailed, sometimes harsh",
    strengths: ["continuity tracking", "booking logic", "long-term storytelling"],
    focuses_on: ["continuity", "booking logic", "title prestige", "PLE build"],
    bias: "continuity hawk — rewards earned stories",
    tts_voice: "broadcast", tts_speed: 0.93,
  },
  "Dante Brooks": {
    gender: "Male", identity: "Business and ratings analyst",
    podcast_role: "explains viewership, money, sponsorships, and company prestige",
    personality: "smooth, strategic, numbers-focused",
    speaking_style: "polished, confident, business-like",
    strengths: ["ratings and revenue reads", "sponsor trust"],
    focuses_on: ["viewership", "attendance", "profit", "sponsor trust"],
    bias: "numbers-first but respects emotional payoffs that sell",
    tts_voice: "smooth", tts_speed: 0.94,
  },
  "Rico Blaze": {
    gender: "Male", identity: "Fan voice / hot-take debate host",
    podcast_role: "says what fans online are probably thinking",
    personality: "loud, funny, passionate, unpredictable",
    speaking_style: "energetic, funny, dramatic, debate-style",
    strengths: ["fan reaction", "viral moment reads"],
    focuses_on: ["Twitter", "fan outrage", "viral clips"],
    bias: "fan-first hot takes",
    tts_voice: "fan-debate", tts_speed: 0.98,
  },
};

export function getPodcastHostProfile(name) {
  const p = NXT_PODCAST_HOST_PROFILES[name] || {
    identity: "Podcast host", podcast_role: "breaks down the week",
    personality: "sharp, conversational", speaking_style: "natural, podcast conversational",
    strengths: ["analysis"], focuses_on: ["the story"], bias: "balanced",
    tts_voice: "neutral", tts_speed: 0.95,
  };
  const style = p.tts_voice || "neutral";
  return {
    ...p, name,
    edgeVoice: EDGE_VOICE[style] || EDGE_VOICE.neutral,
    openaiVoice: OPENAI_VOICE[style] || OPENAI_VOICE.neutral,
  };
}

/** Per-host browser voice hints (fallback only — neural TTS preferred). */
export const PODCAST_HOST_VOICE = {
  "Maya Cruz": { rate: 0.94, pitch: 1.05, voiceRe: /female|aria|samantha|victoria|zira|jenny|karen/i },
  "Dre Walker": { rate: 0.98, pitch: 0.92, voiceRe: /male|guy|david|mark|alex|daniel|fred|christopher/i },
  "Tasha Monroe": { rate: 0.96, pitch: 1.08, voiceRe: /female|ana|sara|jenny/i },
  "Serena Vale": { rate: 0.95, pitch: 0.88, voiceRe: /female|guy|deep|brian/i },
  "Marcus King": { rate: 0.93, pitch: 0.9, voiceRe: /male|brian|guy|broadcast/i },
  "Dante Brooks": { rate: 0.94, pitch: 0.95, voiceRe: /male|roger|smooth|fable/i },
  "Rico Blaze": { rate: 0.98, pitch: 1.1, voiceRe: /male|christopher|brandon|energetic/i },
};

export function buildPodcastStoryContext(state, brand, targetFeudId) {
  const cfg = BRAND_CONFIG[state.activeBrand] || {};
  const res = brand.lastResult;
  const feud = targetFeudId && targetFeudId !== "show" ? brand.feuds.find((f) => f.id === targetFeudId && !f.done) : null;
  const champs = brand.titles.filter((t) => t.champ).map((t) => `${t.name}: ${unitById(brand, t.champ)?.name || "?"}`).join("; ");
  const news = (brand.news || []).slice(0, 6).map((n) => n.text).join(" | ");
  const lines = [`Week ${state.week} — ${cfg.name || "NXT"}`, `Viewership: ${fmtNum(brand.viewership)}`, `Brand popularity: ${Math.round(brand.pop)}`];
  if (res) {
    lines.push(`Latest show: ${res.eventName}, rated ${res.rating}/10`);
    lines.push(`Results: ${(res.matches || []).map((m) => `${m.names} (winner: ${m.winner})`).join("; ")}`);
    if (res.lines?.length) lines.push(`Show notes: ${res.lines.slice(0, 4).join(" ")}`);
  }
  if (feud) lines.push(`Main program: ${feud.label} (heat ${Math.round(feud.heat)})`);
  else {
    const active = brand.feuds.filter((f) => !f.done).map((f) => `${f.label} (${Math.round(f.heat)} heat)`);
    if (active.length) lines.push(`Active programs: ${active.join("; ")}`);
  }
  if (champs) lines.push(`Champions: ${champs}`);
  if (news) lines.push(`Recent headlines: ${news}`);
  return lines.join("\n");
}

function hostProfileBlock(name) {
  const h = getPodcastHostProfile(name);
  return `${h.name} (${h.gender || ""}) — ${h.identity}
Role: ${h.podcast_role}
Personality: ${h.personality}
Speaking style: ${h.speaking_style}
Strengths: ${(h.strengths || []).join(", ")}
Focus: ${(h.focuses_on || []).join(", ")}
Bias: ${h.bias}
Catchphrase (optional): ${h.catchphrase || ""}`;
}

export function buildPodcastGenerationPrompt(state, brand, hosts, fields) {
  const hostNames = hosts.map((h) => (typeof h === "string" ? h : h.name)).filter(Boolean);
  const hostBlocks = hostNames.map(hostProfileBlock).join("\n\n");
  const spec = PODCAST_LENGTH_SPECS[fields.length] || PODCAST_LENGTH_SPECS["Full Episode (~10 min)"];
  const story = fields.storyText || buildPodcastStoryContext(state, brand, fields.targetFeudId);
  const podName = (brand.podcast && brand.podcast.name) || "NXT Unfiltered";
  return `You are writing a NotebookLM-style podcast script for **${podName}** — exclusive to NXT's cinematic Hollywood storytelling brand.

ONLY these hosts may speak (each must sound distinct — do NOT make them sound the same):
${hostBlocks}

Host count: ${hostNames.length} — ${hostNames.length === 2 ? "focused two-host conversation" : hostNames.length >= 4 ? "roundtable debate" : "panel discussion"}

USER INPUTS:
Episode title: ${fields.episodeTitle || `Week ${state.week} — NXT Unfiltered`}
Week: ${state.week}
Main story/rivalry: ${fields.mainStory || "Infer from story text"}
Main characters: ${fields.mainCharacters || "Infer from story text"}
User notes: ${fields.userNotes || ""}
Tone: ${fields.tone || "emotional deep dive"}
Length: ${fields.length || "Full Episode (~10 min)"}

FULL STORY TEXT (use details from this — do not invent unrelated plots):
${story.slice(0, 12000)}

FORMAT — actual podcast script. Each line MUST be:
Host Name:
"dialogue in quotes"

DO NOT only summarize what happened. Explain WHY it matters beneath the surface — character psychology, locker room reads, sponsor/media optics, fan reaction, business impact.

Include these sections with clear headers:
Opening Intro, Story Recap, Deep Story Analysis, Real-Life Connection, Character Thought Process,
World-Building Meaning, Hidden Motivation, What The Locker Room Might Think, What Sponsors Might Worry About,
Morale Watch, Popularity Movement, What Made Sense, What Did Not Make Sense,
Business / Viewership Impact, Twitter Reaction Prediction, Next Week Predictions, Closing Thoughts

Rules:
- Use ONLY the listed hosts for dialogue.
- NXT Unfiltered is EXCLUSIVE to NXT.
- TARGET RUNTIME: ~${spec.target_minutes} minutes (~${spec.min_dialogue_chars}+ characters inside quotes, at least ${spec.min_lines} quoted host lines).
- Each section needs at least ${spec.lines_per_section} back-and-forth exchanges — hosts interrupt, disagree, push back like a real podcast.
- Sound human: contractions, reactions by name, not lecture notes.
- NO bullet lists in dialogue. Reference specific details from the story text.
- Never claim fake real-world allegations or copy copyrighted scenes.
- Return ONLY the script — no preamble, no markdown fences.`;
}

const EDGE_TTS_TOKEN = "6A5AA1D4EAFF4F9B847E4F56A0D5D2B4";

function escapeSsml(text) {
  return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function speedToEdgeRate(speed) {
  const pct = Math.max(-35, Math.min(45, Math.round((Number(speed || 1) - 1) * 100)));
  return `${pct >= 0 ? "+" : ""}${pct}%`;
}

function sleep(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) { reject(new DOMException("Aborted", "AbortError")); return; }
    const t = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => { clearTimeout(t); reject(new DOMException("Aborted", "AbortError")); }, { once: true });
  });
}

function playAudioBlob(blob, signal) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    const cleanup = () => URL.revokeObjectURL(url);
    audio.onended = () => { cleanup(); resolve(); };
    audio.onerror = () => { cleanup(); reject(new Error("Audio playback failed")); };
    if (signal?.aborted) { cleanup(); reject(new DOMException("Aborted", "AbortError")); return; }
    signal?.addEventListener("abort", () => { audio.pause(); cleanup(); reject(new DOMException("Aborted", "AbortError")); }, { once: true });
    audio.play().catch(reject);
  });
}

export async function synthesizeEdgeTts(text, voiceName, speed = 1.0) {
  const connectId = crypto.randomUUID().replace(/-/g, "");
  const url = `wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1?TrustedClientToken=${EDGE_TTS_TOKEN}&ConnectionId=${connectId}`;
  const rate = speedToEdgeRate(speed);
  const ssml = `<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'><voice name='${voiceName}'><prosody rate='${rate}'>${escapeSsml(humanizeDialogueForTts(text))}</prosody></voice></speak>`;

  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    const audioChunks = [];
    let settled = false;
    const finish = (err, blob) => {
      if (settled) return;
      settled = true;
      try { ws.close(); } catch (_) { /* ignore */ }
      if (err) reject(err);
      else resolve(blob);
    };

    ws.binaryType = "arraybuffer";
    ws.onopen = () => {
      ws.send(`Content-Type:application/json; charset=utf-8\r\nPath:speech.config\r\n\r\n{"context":{"synthesis":{"audio":{"metadataoptions":{"sentenceBoundaryEnabled":"false","wordBoundaryEnabled":"false"},"outputFormat":"audio-24khz-48kbitrate-mono-mp3"}}}}`);
      const requestId = crypto.randomUUID().replace(/-/g, "");
      ws.send(`X-RequestId:${requestId}\r\nContent-Type:application/ssml+xml\r\nPath:ssml\r\n\r\n${ssml}`);
    };
    ws.onmessage = (ev) => {
      if (typeof ev.data === "string") {
        if (ev.data.includes("Path:turn.end")) finish(null, new Blob(audioChunks, { type: "audio/mpeg" }));
        return;
      }
      const buf = new Uint8Array(ev.data);
      const headerLen = (buf[0] << 8) | buf[1];
      const header = new TextDecoder().decode(buf.slice(2, 2 + headerLen));
      if (header.includes("Path:audio")) audioChunks.push(buf.slice(2 + headerLen));
    };
    ws.onerror = () => finish(new Error("Neural voice connection failed"));
    ws.onclose = () => {
      if (!settled && audioChunks.length) finish(null, new Blob(audioChunks, { type: "audio/mpeg" }));
      else if (!settled) finish(new Error("Neural voice closed without audio"));
    };
  });
}

export async function synthesizeOpenAiTts(text, voice, apiKey, speed = 1.0) {
  const res = await fetch("https://api.openai.com/v1/audio/speech", {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "tts-1-hd",
      voice: voice || "nova",
      input: humanizeDialogueForTts(text).slice(0, 4096),
      speed: clamp(speed, 0.82, 1.08),
    }),
  });
  if (!res.ok) throw new Error("OpenAI voice failed");
  return res.blob();
}

/** Play podcast with smooth neural voices (Edge TTS, OpenAI fallback). Returns mode used. */
export async function playPodcastNeural(script, hosts, onStatus, signal) {
  const segs = parsePodcastDialogue(script, hosts);
  if (!segs.length) throw new Error('Format lines as Host Name: "dialogue"');
  const openaiKey = import.meta.env.VITE_OPENAI_API_KEY;
  let mode = "edge";
  for (let i = 0; i < segs.length; i++) {
    if (signal?.aborted) break;
    const { speaker, text } = segs[i];
    const profile = getPodcastHostProfile(speaker);
    onStatus?.(`🎧 ${speaker} (${i + 1}/${segs.length})`);
    let blob;
    try {
      blob = await synthesizeEdgeTts(text, profile.edgeVoice, profile.tts_speed);
    } catch (e) {
      if (openaiKey) {
        mode = "openai";
        blob = await synthesizeOpenAiTts(text, profile.openaiVoice, openaiKey, profile.tts_speed);
      } else throw e;
    }
    await playAudioBlob(blob, signal);
    if (i < segs.length - 1) await sleep(PODCAST_TTS_PAUSE_MS, signal);
  }
  onStatus?.("Done");
  return mode;
}

/* ---- staff ---- */
export const STAFF_ROLES = ["Commentator", "Producer", "Ring Announcer", "Referee", "Podcast Host"];
export function defaultStaff(k) {
  const cfg = BRAND_CONFIG[k];
  const st = [
    { id: k + "-own", name: cfg.owner, role: "Owner", locked: true },
    ...(cfg.owner2 ? [{ id: k + "-own2", name: cfg.owner2, role: "Owner", locked: true }] : []),
    { id: k + "-gm", name: cfg.gm, role: "General Manager", locked: true },
  ];
  if (k === "nxt") st.push({ id: "nxt-pod1", name: "Maya Cruz", role: "Podcast Host" }, { id: "nxt-pod2", name: "Dre Walker", role: "Podcast Host" });
  return st;
}

/* ---- custom superstar ---- */
export function makeCustomUnit(o) {
  let id = slug(o.name);
  o._taken = o._taken || [];
  while (o._taken.includes(id)) id += "x";
  return {
    id, name: o.name, div: o.div, al: o.al, ovr: clamp(o.ovr, 40, 99), sal: o.sal,
    sex: o.sex, type: o.type || "s", fac: null, guest: false,
    pop: clamp(o.pop, 30, 100), mom: clamp(o.mom, 0, 100), sta: clamp(o.sta, 40, 100), fat: 0,
    rs: clamp(o.rs || o.ovr, 40, 99), ps: clamp(o.ps || o.ovr - 4, 35, 99),
    psych: clamp(o.psych ?? o.ovr - 3, 40, 99), cha: clamp(o.cha ?? o.pop, 30, 100),
    members: o.members || [],
    w: 0, l: 0, status: null, merchHot: 0,
    mor: 60, yrs: o.yrs || 2, bio: o.bio || "", deb: o.deb !== false, lastBooked: 0,
    angryWks: 0, wants: null, holdout: false, form: [], cool: {},
  };
}

/* ---- endless seasons ---- */
export function startNextSeason(state) {
  state.history.push({ season: state.season, champion: state.champion ? { name: state.champion.player, brand: state.champion.name, power: Math.round(state.champion.p.power) } : null });
  BRAND_KEYS.forEach((k) => {
    const brand = state.brands[k];
    /* contracts tick + expiry resolution */
    const leaving = [];
    brand.units.forEach((u) => {
      if (u.guest) return;
      u.yrs = (u.yrs || 2) - 1;
      if (u.yrs <= 0) {
        if ((u.mor ?? 60) >= 40) {
          u.yrs = 2; u.sal = Math.round(u.sal * 1.1);
          pushNews(state, k, `✍️ ${u.name} RE-SIGNS with ${BRAND_CONFIG[k].name} — 2 yrs, ${money(u.sal)}/yr.`, "good");
        } else {
          leaving.push(u.id);
        }
      }
    });
    leaving.forEach((id) => {
      const u = unitById(brand, id);
      titleHeldBy(brand, id).forEach((t) => { closeReign(t, state.week); t.champ = null; t.note = "Vacated — contract expired"; });
      brand.feuds.forEach((f) => { if (!f.done && (f.aId === id || f.bId === id)) f.done = true; });
      brand.units = brand.units.filter((x) => x.id !== id);
      state.freeAgents.push(toFreeAgent(u));
      pushNews(state, k, `📤 ${u.name}'s contract EXPIRED — too unhappy to re-sign. Free agent.`, "bad");
    });
    /* per-season resets, carry the universe forward */
    brand.units.forEach((u) => { u.fat = 0; u.w = 0; u.l = 0; u.form = []; u.lastBooked = 0; u.merchHot = 0; u.trainCd = 0; });
    brand.objectives = []; brand.objStats = { done: 0, total: 0 };
    brand.pleRatings = [];
    brand.monthLog = freshMonthLog(brand.pop);
    brand.ledger = brand.ledger.slice(-10);
    brand.revenueTotal = 0; brand.costTotal = 0;
    brand.startViewership = brand.viewership; brand.startPop = brand.pop;
    brand.viewHist = []; brand.fillHist = []; brand.firstFill = null; brand.lastFill = null;
    brand.storyScore = 50;
    brand.recentMatchups = []; brand.mandates = []; brand.pendingScrewjob = null; brand.activeEvent = null;
    brand.lastResult = null; brand.showCount = 0;
    brand.podBoost = 0; brand.podWeek = 0; brand.oppCd = {}; brand.prevRanks = {};
    brand.results = (brand.results || []).slice(-12);
    brand.baseMargin = computeBaseMargin(brand, k);
  });
  state.trades = state.trades.filter((t) => t.status !== "pending");
  state.season += 1;
  state.week = 1;
  state.locked = { wcw: false, sd: false, nxt: false };
  state.booking = { wcw: { ...emptyBooking(), market: DEFAULT_MARKET }, sd: { ...emptyBooking(), market: DEFAULT_MARKET }, nxt: { ...emptyBooking(), market: DEFAULT_MARKET } };
  state.seasonOver = false; state.screen = "game";
  state.champion = null; state.awards = null; state.standings = null;
  BRAND_KEYS.forEach((k) => issueObjectives(state, k, 0));
  BRAND_KEYS.forEach((k) => pushNews(state, k, `🔥 SEASON ${state.season} BEGINS — May is here. New objectives are live.`, "info"));
}

/* ---- training ---- */
export const TRAIN_TIERS = [
  { id: "basic", n: "Basic Camp", cost: 250000, min: 1, max: 3, fail: 0.12, failMin: 1, failMax: 1, desc: "Fundamentals with the trainers." },
  { id: "adv", n: "Advanced Camp", cost: 600000, min: 2, max: 5, fail: 0.18, failMin: 1, failMax: 2, desc: "Intensive work with veterans." },
  { id: "elite", n: "Elite Camp", cost: 1500000, min: 3, max: 8, fail: 0.25, failMin: 2, failMax: 3, desc: "High risk, high reward masterclass." },
];

export function trainUnit(state, bKey, unitId, skill, delta, cost, tierName) {
  const brand = state.brands[bKey];
  const u = unitById(brand, unitId);
  if (!u || brand.cash < cost) return;
  brand.cash -= cost;
  brand.ledger.push({ week: state.week, label: `${tierName} ${skill === "rs" ? "ring" : "promo"} training — ${u.name}`, amt: -cost });
  const key = skill === "rs" ? "rs" : "ps";
  u[key] = clamp((u[key] || u.ovr) + delta, 30, 99);
  u.fat = clamp(u.fat + 8, 0, 100);
  u.trainCd = state.week + 3;
  if (delta >= 0) {
    u.mor = clamp((u.mor ?? 60) + 2, 0, 100);
    pushNews(state, bKey, `📈 ${u.name} leveled up in ${tierName} training (+${delta} ${skill === "rs" ? "Ring Skill" : "Promo Skill"}).`, "good");
  } else {
    u.mor = clamp((u.mor ?? 60) - 4, 0, 100);
    pushNews(state, bKey, `📉 Training BACKFIRED — ${u.name} picked up bad habits (${delta} ${skill === "rs" ? "Ring Skill" : "Promo Skill"}).`, "bad");
  }
}

/* ---- pillars & season end ---- */
export function computePillars(brand) {
  const story = brand.storyScore;
  const compPct = brand.objStats.total ? (brand.objStats.done / brand.objStats.total) * 100 : 50;
  const products = brand.sponsors.filter((s) => !s.media && s.v > 0);
  const avgRel = products.length ? products.reduce((s, x) => s + x.rel, 0) / products.length : 50;
  const sponsor = clamp(compPct * 0.7 + avgRel * 0.3, 0, 100);
  const avgPLE = brand.pleRatings.length ? brand.pleRatings.reduce((a, b) => a + b, 0) / brand.pleRatings.length : 0;
  const ple = clamp(brand.fanInv * 0.55 + avgPLE * 10 * 0.45, 0, 100);
  const viewD = ((brand.viewership - brand.startViewership) / brand.startViewership) * 100;
  const popD = brand.pop - brand.startPop;
  const fillD = brand.firstFill !== null && brand.lastFill !== null ? brand.lastFill - brand.firstFill : 0;
  const growth = clamp(50 + viewD * 2.2 + popD * 2 + fillD * 30, 0, 100);
  const margin = brand.revenueTotal > 0 ? (brand.revenueTotal - brand.costTotal) / brand.revenueTotal : 0;
  const bm = typeof brand.baseMargin === "number" ? brand.baseMargin : 0.15;
  const profit = clamp(50 + (margin - bm) * 350, 0, 100);
  const power = story * 0.34 + ple * 0.26 + growth * 0.22 + sponsor * 0.10 + profit * 0.08;
  return { story, sponsor, ple, growth, profit, power };
}

export function finishSeason(state) {
  const rows = BRAND_KEYS.map((k) => ({ k, name: BRAND_CONFIG[k].name, player: state.players[k], p: computePillars(state.brands[k]) }));
  rows.sort((a, b) => b.p.power - a.p.power);
  state.champion = rows[0];
  const bestOf = (fn, label) => {
    const r = [...rows].sort((a, b) => fn(b) - fn(a))[0];
    return { label, who: `${r.player} (${r.name})`, val: fn(r) };
  };
  state.awards = [
    bestOf((r) => r.p.story, "Best Storytelling"),
    bestOf((r) => r.p.sponsor, "Sponsor Darling"),
    bestOf((r) => r.p.ple, "PLE of the Year Energy"),
    bestOf((r) => r.p.growth, "Fastest Growing Brand"),
    bestOf((r) => r.p.profit, "Money Mark Award"),
  ];
  state.standings = rows;
}

/* ================================================================
   SOCIAL MEDIA ENGINE + AI
   ================================================================ */
export const PUNDITS = [
  { n: "Squared Circle SZN", h: "@SquaredCircleSZN" }, { n: "Heel Heat Daily", h: "@HeelHeatDaily" },
  { n: "Markout Matt", h: "@MarkoutMatt" }, { n: "The Smark Tank", h: "@TheSmarkTank" },
  { n: "Kayfabe Karen", h: "@KayfabeKaren" }, { n: "Botched Spots Bot", h: "@BotchedSpotsBot" },
  { n: "Main Event Maven", h: "@MainEventMaven" }, { n: "Wrestle Economist", h: "@WrestleEconomist" },
  { n: "Jobber Journal", h: "@JobberJournal" }, { n: "Five Star Frank", h: "@FiveStarFrank" },
  { n: "Turnbuckle Tea", h: "@TurnbuckleTea" }, { n: "The Dirt Sheet Don", h: "@DirtSheetDon" },
  { n: "Cheap Pop Charlie", h: "@CheapPopCharlie" }, { n: "Ratings Hawk", h: "@RatingsHawk" },
  { n: "Gorilla Position Pod", h: "@GorillaPosPod" }, { n: "Banner Bella", h: "@BannerBella" },
];
export const fmtSoc = (n) => n >= 1e9 ? (n / 1e9).toFixed(1) + "B" : n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(1) + "K" : String(n);
export const handleOf = (name) => "@" + name.replace(/[^a-zA-Z0-9]+/g, "");

export function engagement(brand, { viral = false, mega = false } = {}) {
  let views = Math.round(brand.viewership * rnd(0.05, 0.4));
  if (viral) views = Math.round(views * rnd(4, 9));
  if (mega) views = Math.round(views * rnd(25, 60));
  views = Math.min(views, 2200000000);
  return { views, likes: Math.round(views * rnd(0.03, 0.08)), rts: Math.round(views * rnd(0.008, 0.02)), replies: Math.round(views * rnd(0.002, 0.008)) };
}

export function addPost(state, bKey, post) {
  const brand = state.brands[bKey];
  brand.social.unshift({
    id: "p" + Date.now() + Math.random().toString(36).slice(2, 6),
    week: state.week, brand: bKey, viral: false, mega: false, ai: false,
    ...engagement(brand, post), ...post,
  });
  if (brand.social.length > 80) brand.social.length = 80;
}

/* posts already on any timeline recently — never repeat a take */
function usedTexts(state) {
  const t = new Set();
  BRAND_KEYS.forEach((k) => (state.brands[k].social || []).slice(0, 50).forEach((p) => t.add(p.text)));
  return t;
}
function freshPick(state, arr) {
  const used = usedTexts(state);
  const pool = arr.filter((x) => !used.has(x));
  return pool.length ? pick(pool) : pick(arr);
}

function genShowSocial(state, bKey, res) {
  const brand = state.brands[bKey];
  const cfg = BRAND_CONFIG[bKey];
  const r = res.rating;
  const tag = "#" + cfg.name.replace(/\W/g, "");
  const best = [...res.matches].sort((a, b) => b.q - a.q)[0];
  const bestN = best ? best.names : "the main event";
  const view = fmtNum(res.viewership);

  /* ---- brand account: 2K/Madden-style headlines ---- */
  const head =
    r >= 9 ? [
      `🚨 INSTANT CLASSIC: ${res.eventName} delivers a ${r.toFixed(1)}/10. ${bestN} steal the show. ${tag}`,
      `🏆 HISTORY MADE. ${res.eventName} grades out at ${r.toFixed(1)} — highest marks of the season.`,
      `⭐⭐⭐⭐⭐ ${bestN} just went five stars. ${res.eventName} will be talked about for YEARS.`,
      `📈 RATINGS ALERT: ${view} watched ${res.eventName} go ${r.toFixed(1)}/10. Appointment television.`,
      `🏈 GAME BALL: ${best ? best.winner : cfg.name} walks out of ${res.eventName} a made star.`,
      `💯 99 OVR PERFORMANCE. ${res.eventName} hits ${r.toFixed(1)} and the ${res.selloutTag.toLowerCase()} crowd lost it.`,
    ] : r >= 8 ? [
      `📊 STOCK UP: ${cfg.name} is rolling. ${res.eventName} lands a ${r.toFixed(1)} with ${view} watching.`,
      `📈 POWER RANKINGS RISER: another strong week — ${res.eventName} goes ${r.toFixed(1)}/10.`,
      `💪 STATEMENT WIN for the brand. ${r.toFixed(1)}/10 and ${bestN} cooking. Momentum is REAL.`,
      `🧾 BOX SCORE: ${r.toFixed(1)}/10 · ${view} viewers · ${res.selloutTag}. Efficient night at the office.`,
      `🎮 FRANCHISE MODE: ${cfg.show} keeps stacking wins. ${res.eventName}, ${r.toFixed(1)}/10.`,
      `📺 TRENDING UP: ${bestN} headline a ${r.toFixed(1)} show. The locker room felt that one.`,
    ] : r >= 6.5 ? [
      `${res.eventName} goes ${r.toFixed(1)}/10 in front of a ${res.selloutTag.toLowerCase()} crowd.`,
      `📋 MID-TABLE FINISH: ${r.toFixed(1)}/10. Some bright spots — ${bestN} delivered.`,
      `🤝 HOLD: ${res.eventName} grades a ${r.toFixed(1)}. Not bad, not appointment TV. Yet.`,
      `Box score says ${r.toFixed(1)}/10, ${view} watching. Coaching staff will take it.`,
      `${cfg.show} puts up a workmanlike ${r.toFixed(1)}. The film session will be honest.`,
    ] : [
      `📉 STOCK DOWN: rough night. ${res.eventName} limps to a ${r.toFixed(1)}. The locker room knows.`,
      `🥶 DRAFT BUST WATCH: ${r.toFixed(1)}/10. Somebody owes the ${res.selloutTag.toLowerCase()} crowd an apology.`,
      `🚨 PANIC METER RISING: ${res.eventName} bottoms out at ${r.toFixed(1)}. Creative is on notice.`,
      `🧊 ICE COLD: ${r.toFixed(1)}/10 with ${view} watching them watch nothing happen.`,
      `Front office statement incoming after THAT. ${res.eventName}: ${r.toFixed(1)}/10.`,
    ];
  addPost(state, bKey, { kind: "brand", name: cfg.name + " (Official)", handle: handleOf(cfg.name), text: freshPick(state, head), viral: r >= 9 });

  /* ---- pundit take ---- */
  const p = pick(PUNDITS);
  const takes =
    r >= 8.5 ? [
      `${bestN} just reminded everyone why we watch. ${cfg.name} cooked tonight.${best ? " " + best.q + "/100." : ""}`,
      `I need ${bestN} to run it back at a PLE immediately. Television of the YEAR candidate.`,
      `Called it in the preseason: ${cfg.name} is the deepest roster in the game. Tonight proved it.`,
      `My scorecard for ${res.eventName} ran out of ink. ${r.toFixed(1)} feels LOW.`,
      `That ${best ? best.stip.toLowerCase() : "main event"} was art. Put it in the Louvre.`,
      `Whoever laid out ${res.eventName} deserves a raise. Pacing, payoffs, heat — all of it.`,
    ] : r >= 7 ? [
      `Solid ${cfg.show} this week. Nothing I'd run through a wall for, but the booking made sense.`,
      `${bestN} quietly had a great one. Don't let it get lost in the shuffle.`,
      `B-show energy but A-show effort from ${best ? best.winner : "the undercard"}. Respect.`,
      `Watchable, logical, occasionally great. ${cfg.name} is building something — slowly.`,
      `Fine show. The ${res.selloutTag.toLowerCase()} was louder than the booking deserved, honestly.`,
    ] : r >= 5.5 ? [
      `Somebody check on ${cfg.name} creative. ${res.eventName} felt like a show booked during lunch.`,
      `That was 2 hours of my life. The ${bestN} match was the only thing keeping the lights on.`,
      `${cfg.show} is stuck in traffic. Talent's there, direction isn't.`,
      `I've seen house shows with more stakes than ${res.eventName}. ${r.toFixed(1)}/10 is generous.`,
      `Hot take: nothing about that was hot. Take a week off, creative.`,
    ] : [
      `I sat through ${res.eventName} so you didn't have to. ${r.toFixed(1)}/10. The refund line forms here.`,
      `${cfg.name} just speedran how to lose an audience. ${view} watched. Fewer will next week.`,
      `Burn the format sheet. Start over. ${r.toFixed(1)}/10.`,
      `My dog walked out of the room during the main event. Smart dog.`,
      `That wasn't a wrestling show, that was a hostage situation with pyro.`,
    ];
  addPost(state, bKey, { kind: "pundit", name: p.n, handle: p.h, text: freshPick(state, takes) });

  /* ---- title change = breaking, viral ---- */
  res.matches.forEach((m) => {
    if (m.titleNote && (m.titleNote.includes("TITLE CHANGE") || m.titleNote.includes("crowned"))) {
      const tc = [
        `🚨 BREAKING: ${m.titleNote} ${res.isPLE ? "Scenes at " + res.eventName + "." : "On free TV?!"}`,
        `👑 NEW CHAMP ALERT — ${m.titleNote} The group chat is in SHAMBLES.`,
        `🔄 CHANGE AT THE TOP: ${m.titleNote} Where does the division go from here?!`,
        `THE BELT MOVED. ${m.titleNote} I was NOT ready.`,
        `🎥 ${m.titleNote} Somebody clip the crowd reaction RIGHT NOW.`,
      ];
      addPost(state, bKey, { kind: "pundit", name: "Squared Circle SZN", handle: "@SquaredCircleSZN", text: freshPick(state, tc), viral: true });
    }
  });

  /* ---- blowoff ---- */
  if (res.heatNotes.some((h) => h.includes("BLOWOFF"))) {
    const bo = [
      `That blowoff at ${res.eventName}? Cinema. THIS is how you pay off a program.`,
      `Months of build. One perfect ending. ${res.eventName} understood the assignment.`,
      `Feud-ender of the year candidate at ${res.eventName}. Storytelling still lives.`,
      `They actually PAID IT OFF. No screwy finish, no reset button. Bravo, ${cfg.name}.`,
    ];
    addPost(state, bKey, { kind: "pundit", name: "Five Star Frank", handle: "@FiveStarFrank", text: freshPick(state, bo), viral: true });
  }

  /* ---- sellout flex ---- */
  if (res.fill >= 0.97) {
    const so = [
      `🎟 SOLD. OUT. ${fmtNum(res.att)} strong for ${res.eventName}. ${tag} nation showed UP.`,
      `No seats left in the building tonight. ${cfg.name} is a hot ticket again.`,
      `Scalpers eating GOOD off ${res.eventName}. Full house, ${fmtNum(res.att)} deep.`,
    ];
    addPost(state, bKey, { kind: "brand", name: cfg.name + " (Official)", handle: handleOf(cfg.name), text: freshPick(state, so) });
  }

  /* ---- in-character wrestler post ---- */
  if (best) {
    const winnerName = best.winner !== "—" ? best.winner.split(" & ")[0] : null;
    const u = winnerName ? brand.units.find((x) => x.name === winnerName) : null;
    if (u) {
      const wPools = u.al === "H" ? [
        `I told every single one of you. ${best.q}/100 and it wasn't close. Crown me.`,
        `Boo louder. It pays the same. ${tag}`,
        `They booked me to lose sleep, not matches.`,
        `Film study: me, winning. Again. Class dismissed.`,
        `Your favorite's favorite villain. Check the scoreboard on your way out.`,
        `I don't need your respect. I'll just keep taking everything else.`,
      ] : u.al === "F" ? [
        `WE did that tonight. Every one of you in that building — that was for you. ❤️`,
        `Sore everywhere. Worth everything. See you next week.`,
        `They said it couldn't be done. Watch the replay.`,
        `From the first row to the last — I heard ALL of you tonight. Thank you.`,
        `Hard work doesn't trend. Wins do. Let's keep stacking them.`,
        `One more step up the mountain. Nobody's pulling me off it.`,
      ] : [
        `Results speak. Everything else is noise.`,
        `Next.`,
        `No friends, no enemies. Just opponents and outcomes.`,
        `Scoreboard doesn't care about your opinion. Neither do I.`,
      ];
      addPost(state, bKey, { kind: "wrestler", name: u.name, handle: handleOf(u.name), unitId: u.id, text: freshPick(state, wPools) });
    }
    /* salty loser take on bad finishes */
    if (r < 9 && Math.random() < 0.45 && best.winner !== "—") {
      const loserSide = res.matches.find((m) => m.isMain);
      if (loserSide && loserSide.finish !== "Clean" && loserSide.winner !== "—") {
        const lPools = [
          `Count slow much? This isn't over.`,
          `Funny how the rulebook only matters when I'm winning.`,
          `Enjoy it. Borrowed time hits different.`,
          `Refs sleep fine, apparently. I won't. See you soon.`,
        ];
        const lu = brand.units.find((x) => loserSide.names.includes(x.name) && !loserSide.winner.includes(x.name));
        if (lu) addPost(state, bKey, { kind: "wrestler", name: lu.name, handle: handleOf(lu.name), unitId: lu.id, text: freshPick(state, lPools) });
      }
    }
  }
}

function genEventSocial(state, bKey, ev, u, choice) {
  if (!ev || !u) return;
  if (choice === "buyout" && !ev.noBuyout) {
    addPost(state, bKey, { kind: "pundit", name: "Wrestle Economist", handle: "@WrestleEconomist", text: `Sources: ${BRAND_CONFIG[bKey].name} quietly wrote a very large check to make a ${u.name} situation disappear. Business as usual.` });
    return;
  }
  const lines = {
    dui: `🚔 REPORT: ${u.name} arrested overnight. ${BRAND_CONFIG[bKey].name} says they're "gathering facts."`,
    assault: `📹 Video circulating of ${u.name} in an altercation outside the arena. This is not good.`,
    majinj: `Prayers up — ${u.name} stretchered out at a live event. Word backstage is it's BAD.`,
    mininj: `${u.name} banged up — out roughly two months per sources. Brutal timing.`,
    wellness: `🚫 ${u.name} flagged by the wellness program. 60 days. No comment from the company.`,
    movie: `🎬 EXCLUSIVE: ${u.name} lands a major film role. Hollywood keeps raiding the roster.`,
    pregnancy: `👶 ${u.name} announces she's expecting! Congratulations pouring in from the entire locker room.`,
    turn: `DID THAT JUST HAPPEN?! ${u.name} just flipped the script. The crowd is in SHOCK.`,
    renewal: choice === "walk" ? `💼 FREE AGENCY ALERT: ${u.name} and ${BRAND_CONFIG[bKey].name} could not reach a deal. Open market!` : `💰 ${u.name} got PAID. New deal done with ${BRAND_CONFIG[bKey].name}.`,
    walkout: `Backstage source: ${u.name} walked out over creative. "They had nothing for them."`,
    montreal: `Weird vibes around ${u.name} this month. Something's brewing backstage and nobody is talking.`,
    brother: `${u.name} reportedly "not feeling" this month's creative, brother. Working dates anyway.`,
    hot: `The ${u.name} fan edit going around has ${fmtSoc(ri(8000000, 60000000))} views. They are SO over.`,
    noshow: `${u.name} no-showed last night with zero notice. Office is furious.`,
    leave: `${u.name} taking personal time away from the road. Respect. See you soon.`,
    favor: `Network sources say the TV side LOVES ${u.name} right now. Expect a push.`,
    interfere: `Hearing the network wants ${u.name} cooled off. Politics, man.`,
  };
  const txt = lines[ev.id];
  if (txt) addPost(state, bKey, { kind: "pundit", name: pick(PUNDITS).n, handle: pick(PUNDITS).h, text: txt, viral: ["dui", "assault", "turn", "majinj"].includes(ev.id) });
}

/* ---------------- Claude API helpers ---------------- */
export function hasAnthropicKey() {
  const key = import.meta.env.VITE_ANTHROPIC_API_KEY;
  return !!(key && String(key).trim() && !String(key).includes("sk-ant-..."));
}

async function claudeFetch(prompt, maxTokens) {
  const headers = {
    "Content-Type": "application/json",
    "anthropic-version": "2023-06-01",
    "anthropic-dangerous-direct-browser-access": "true",
  };
  const key = import.meta.env.VITE_ANTHROPIC_API_KEY;
  if (key) headers["x-api-key"] = key;
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers,
    body: JSON.stringify({ model: "claude-sonnet-4-20250514", max_tokens: maxTokens, messages: [{ role: "user", content: prompt }] }),
  });
  const data = await response.json();
  if (data.error) throw new Error(data.error.message || "Claude API error");
  return (data.content || []).filter((b) => b.type === "text").map((b) => b.text).join("");
}

async function callClaude(prompt) {
  const text = await claudeFetch(prompt, 1000);
  const clean = text.replace(/```json|```/g, "").trim();
  return JSON.parse(clean);
}

async function callClaudeRaw(prompt, maxTokens = 8192) {
  return claudeFetch(prompt, maxTokens).then((t) => t.replace(/^```[\s\S]*?\n|```$/g, "").trim());
}

export async function generatePodcastEpisodeAI(state, brand, hosts, fields) {
  if (!hasAnthropicKey()) {
    throw new Error("Add your Anthropic key to brand-wars-gm/.env as VITE_ANTHROPIC_API_KEY=sk-ant-… then restart npm run dev.");
  }
  const prompt = buildPodcastGenerationPrompt(state, brand, hosts, fields);
  const script = await callClaudeRaw(prompt, 8192);
  if (script.length < 400) throw new Error("Episode generation returned too little text — try again.");
  return script;
}

export async function gradePromoAI(brand, ctx, scriptText, card) {
  const feudLines = brand.feuds.filter((f) => !f.done).map((f) => `${f.label} (heat ${Math.round(f.heat)})`).join("; ") || "no active programs";
  const champs = brand.titles.filter((t) => t.champ).map((t) => `${t.name}: ${unitById(brand, t.champ)?.name}`).join("; ") || "no champions crowned yet";
  const low = scriptText.toLowerCase();
  const bios = brand.units.filter((u) => u.bio && u.bio.trim() && low.includes(u.name.toLowerCase()))
    .map((u) => `- ${u.name} (${u.al === "F" ? "face" : u.al === "H" ? "heel" : "tweener"}): ${u.bio.trim()}`).join("\n");
  const bioBlock = bios ? `\nBooker's character guides (canon — judge authenticity against THESE):\n${bios}\n` : "";
  const prompt = `You are the harshest, most respected creative grader in professional wrestling.
RUNNING ORDER RULE (critical): the script is a TIMELINE in the order written. Segments and promos weave between the booked matches in sequence.
UNIVERSE RULES (absolute canon): every wrestler in this universe is in their absolute PRIME — judge them at their peak. Crossovers between eras are normal here.
Context — Brand: ${ctx.brandName}, Week ${ctx.week}${ctx.pleName ? ", building to/at " + ctx.pleName : ""}.
Active programs: ${feudLines}.
Champions: ${champs}.${bioBlock}
TONIGHT'S BOOKED CARD (in order — the script weaves around these):
${(card || "no card provided").slice(0, 2500)}

Grade the whole show's creative on: character authenticity, continuity with the programs above, escalation/stakes, pacing, and payoff logic.
Respond with ONLY a JSON object, no preamble, no markdown fences:
{"score": <integer 0-100>, "verdict": "<one brutal-but-fair sentence about the SHOW>", "strengths": ["<short>", "<short>"], "weaknesses": ["<short>", "<short>"]}

FULL SHOW SCRIPT (timeline order):
${scriptText.slice(0, 6000)}`;
  const out = await callClaude(prompt);
  if (typeof out.score !== "number") throw new Error("bad grade payload");
  return { score: clamp(Math.round(out.score), 0, 100), verdict: out.verdict || "", strengths: (out.strengths || []).slice(0, 3), weaknesses: (out.weaknesses || []).slice(0, 3) };
}

export async function gradePodcastAI(brand, ctx, text) {
  const feudLines = brand.feuds.filter((f) => !f.done).map((f) => `${f.label} (heat ${Math.round(f.heat)})`).join("; ") || "no active programs";
  const hosts = (brand.staff || []).filter((s) => s.role === "Podcast Host").map((s) => s.name).join(" & ") || "the hosts";
  const prompt = `You are a ruthless podcast critic reviewing a kayfabe wrestling talk-show episode for "${ctx.podName}" (hosts: ${hosts}).
Brand context: ${ctx.brandName || ""}. Active programs: ${feudLines}.
Judge: host chemistry, kayfabe consistency, hype-building, entertainment value.
Respond ONLY with JSON, no fences: {"score": <integer 0-100>, "verdict": "<one sharp sentence>", "highlights": ["<short>", "<short>"]}

EPISODE TRANSCRIPT:
${text.slice(0, 6000)}`;
  const out = await callClaude(prompt);
  if (typeof out.score !== "number") throw new Error("bad grade payload");
  return { score: clamp(Math.round(out.score), 0, 100), verdict: out.verdict || "", highlights: (out.highlights || []).slice(0, 3) };
}

export async function aiSocialTakes(state, bKey) {
  const brand = state.brands[bKey];
  const cfg = BRAND_CONFIG[bKey];
  const res = brand.lastResult;
  const names = activeUnits(brand).slice(0, 25).map((u) => `${u.name} (${u.al === "F" ? "face" : u.al === "H" ? "heel" : "tweener"})`).join(", ");
  const prompt = `Generate 4 short in-character social media posts (under 220 chars each) reacting to the latest ${cfg.name} wrestling show.
Show: ${res ? `${res.eventName}, rated ${res.rating}/10, ${res.matches.map((m) => m.names + " (winner: " + m.winner + ")").join("; ")}` : "no show yet — react to the brand in general"}.
Roster voices available: ${names}.
Respond ONLY with a JSON array, no fences: [{"name":"<poster name — a roster name above OR an invented fan/pundit>","handle":"@<handle>","text":"<the post>"}]`;
  const arr = await callClaude(prompt);
  if (!Array.isArray(arr)) throw new Error("bad takes payload");
  return arr.slice(0, 4);
}

export const hashPin = (p) => { let h = 7; for (const ch of p) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return String(h); };

/* migrate older saves to the current viewership rules (3M start, 700K–5M bounds)
   + current sponsor terms (Netflix PAYS NXT now) */
export function applyViewershipRules(s) {
  if (!s || !s.brands) return s;
  const nxtNetflix = s.brands.nxt && (s.brands.nxt.sponsors || []).find((sp) => sp.media && sp.n.startsWith("Netflix"));
  if (nxtNetflix && nxtNetflix.v < 0) { nxtNetflix.v = 250; nxtNetflix.n = "Netflix"; }
    BRAND_KEYS.forEach((k) => {
    const b = s.brands[k];
    if (!b) return;
    (b.units || []).forEach(ensureUnitStats);
    if ((b.viewHist || []).length === 0) {
      // no shows aired yet this season — snap to the fresh 3M baseline
      b.viewership = BRAND_CONFIG[k].baseline;
      b.startViewership = BRAND_CONFIG[k].baseline;
    } else {
      b.viewership = Math.round(clamp(b.viewership, VIEW_FLOOR, VIEW_CEIL));
      b.startViewership = Math.round(clamp(b.startViewership, VIEW_FLOOR, VIEW_CEIL));
    }
  });
  return s;
}
