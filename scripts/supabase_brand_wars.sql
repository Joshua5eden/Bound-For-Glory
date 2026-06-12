-- Brand Wars GM online rooms (React app) — uses the same game_saves table as Streamlit multiplayer.
-- Run scripts/supabase_game_saves.sql first if you have not already.

-- Rows look like:
--   save_type = 'brand_wars_online'
--   save_key  = room invite code (e.g. BWG-4829)
--   session_id = internal room id
--   payload   = full JSON game state (ver 4)

create index if not exists game_saves_brand_wars_idx
  on public.game_saves (save_type, save_key)
  where save_type = 'brand_wars_online';
