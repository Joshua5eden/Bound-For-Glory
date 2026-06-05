-- Run once in Supabase SQL Editor for Bound For Glory multiplayer saves.
-- Keys: session_id + company + save_type + save_key (NXT / SmackDown / WCW stay separate).

create table if not exists public.game_saves (
  id bigint generated always as identity primary key,
  session_id text not null,
  company text not null default 'All',
  save_type text not null,
  save_key text not null default '*',
  payload jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  constraint game_saves_unique unique (session_id, company, save_type, save_key)
);

create index if not exists game_saves_session_idx on public.game_saves (session_id);
create index if not exists game_saves_invite_idx on public.game_saves (save_type, save_key)
  where save_type = 'private_session';

-- Use the service_role key in Streamlit secrets (recommended for server-side saves).
-- If you use the anon key instead, keep RLS enabled and allow app access:
alter table public.game_saves enable row level security;

create policy if not exists game_saves_select on public.game_saves for select using (true);
create policy if not exists game_saves_insert on public.game_saves for insert with check (true);
create policy if not exists game_saves_update on public.game_saves for update using (true) with check (true);
create policy if not exists game_saves_delete on public.game_saves for delete using (true);
