/**
 * Cloud storage for Brand Wars GM online mode.
 * Uses Supabase game_saves (same table as the main Streamlit app).
 * Personal keys still use localStorage.
 */
import { createClient } from "@supabase/supabase-js";

export const ROOM_KEY = "brand-wars-room-v1";
const SHARED_GAME_KEY = "brand-wars-online-v4";
const SAVE_TYPE = "brand_wars_online";

let supabase = null;

function validCreds(url, key) {
  if (!url || !key) return false;
  const bad = ["YOUR_PROJECT", "your-anon-key", "your-service-role", "xxxx.supabase.co"];
  if (bad.some((p) => url.includes(p) || key.includes(p))) return false;
  return url.startsWith("https://") && url.includes(".supabase.co") && key.length >= 20;
}

export function isCloudStorageEnabled() {
  return !!supabase;
}

export function getStoredRoom() {
  try {
    const raw = localStorage.getItem(ROOM_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredRoom(room) {
  localStorage.setItem(ROOM_KEY, JSON.stringify(room));
}

export function clearStoredRoom() {
  localStorage.removeItem(ROOM_KEY);
}

function genRoomCode() {
  return "BWG-" + Math.floor(1000 + Math.random() * 9000);
}

async function fetchRoomRow(roomCode) {
  const code = (roomCode || "").trim().toUpperCase();
  if (!code || !supabase) return null;
  const { data, error } = await supabase
    .from("game_saves")
    .select("session_id, payload, updated_at")
    .eq("save_type", SAVE_TYPE)
    .eq("save_key", code)
    .maybeSingle();
  if (error || !data) return null;
  return { ...data, roomCode: code };
}

async function upsertRoomGame(room, gameObj) {
  if (!supabase || !room?.sessionId || !room?.roomCode) throw new Error("No room session");
  const row = {
    session_id: room.sessionId,
    company: "All",
    save_type: SAVE_TYPE,
    save_key: room.roomCode.toUpperCase(),
    payload: gameObj,
    updated_at: new Date().toISOString(),
  };
  const { error } = await supabase
    .from("game_saves")
    .upsert(row, { onConflict: "session_id,company,save_type,save_key" });
  if (error) throw error;
}

/** Create a new online room and persist the initial game payload. */
export async function createRoomSession(initialGame) {
  if (!supabase) throw new Error("Cloud storage not configured");
  let sessionId = crypto.randomUUID().replace(/-/g, "").slice(0, 16);
  let roomCode = genRoomCode();
  for (let attempt = 0; attempt < 8; attempt++) {
    const taken = await fetchRoomRow(roomCode);
    if (!taken) break;
    roomCode = genRoomCode();
  }
  const room = { sessionId, roomCode: roomCode.toUpperCase() };
  await upsertRoomGame(room, initialGame);
  setStoredRoom(room);
  return room;
}

/** Join an existing room by invite code. Returns parsed game state or null. */
export async function joinRoomByCode(roomCode) {
  const row = await fetchRoomRow(roomCode);
  if (!row?.payload) return null;
  setStoredRoom({ sessionId: row.session_id, roomCode: row.roomCode });
  return row.payload;
}

async function sharedGet() {
  const room = getStoredRoom();
  if (!room?.roomCode) return null;
  const row = await fetchRoomRow(room.roomCode);
  if (!row?.payload) return null;
  return JSON.stringify(row.payload);
}

async function sharedSet(jsonStr) {
  const room = getStoredRoom();
  if (!room?.sessionId) throw new Error("No room — create or join first");
  let game;
  try {
    game = JSON.parse(jsonStr);
  } catch {
    throw new Error("Invalid game JSON");
  }
  await upsertRoomGame(room, game);
}

async function sharedDelete() {
  const room = getStoredRoom();
  if (!room?.sessionId || !supabase) return;
  await supabase
    .from("game_saves")
    .delete()
    .eq("session_id", room.sessionId)
    .eq("save_type", SAVE_TYPE)
    .eq("save_key", room.roomCode.toUpperCase());
}

function localKey(k, shared) {
  return (shared ? "shared::" : "") + k;
}

export function initStorage() {
  const url = (import.meta.env.VITE_SUPABASE_URL || "").trim();
  const key = (import.meta.env.VITE_SUPABASE_ANON_KEY || "").trim();
  if (validCreds(url, key)) {
    supabase = createClient(url, key);
  }

  if (typeof window === "undefined") return;

  window.bwgOnline = {
    enabled: !!supabase,
    getRoom: getStoredRoom,
    createRoomSession,
    joinRoomByCode,
    clearRoom: clearStoredRoom,
  };

  window.storage = {
    async get(k, shared) {
      if (shared && k === SHARED_GAME_KEY && supabase) {
        return sharedGet();
      }
      return localStorage.getItem(localKey(k, shared));
    },
    async set(k, v, shared) {
      if (shared && k === SHARED_GAME_KEY && supabase) {
        await sharedSet(v);
        return;
      }
      localStorage.setItem(localKey(k, shared), v);
    },
    async delete(k, shared) {
      if (shared && k === SHARED_GAME_KEY && supabase) {
        await sharedDelete();
        return;
      }
      localStorage.removeItem(localKey(k, shared));
    },
  };
}
