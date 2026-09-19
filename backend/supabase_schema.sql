-- VoiceGuard AI — Supabase schema.
-- Run once in the Supabase SQL editor, then set SUPABASE_URL / SUPABASE_KEY
-- (the service_role key) in backend/.env.

-- Stored analyses (case history) — used by app/storage.py
create table if not exists analyses (
  case_id       text primary key,
  created_at    timestamptz not null default now(),
  audio_sha256  text,
  tier          text,
  overall_risk  real,
  triggered     text[],
  transcript    text
);

-- Registered voiceprints (Check 2 / identity). We store ONLY the 192-number
-- voiceprint embedding, never the raw audio.
create table if not exists voiceprints (
  name        text primary key,
  embedding   double precision[] not null,
  created_at  timestamptz not null default now()
);
