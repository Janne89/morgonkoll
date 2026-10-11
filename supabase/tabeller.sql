-- Morgonkoll: tabeller i Supabase-projektet "morgonkoll".
-- Kör i SQL Editor. Auto-expose är av, så rättigheterna sätts här uttryckligen.

-- En rad per rätt och vecka.
create table if not exists lunch (
  id          bigint generated always as identity primary key,
  restaurang  text not null,
  ar          int  not null,
  vecka       int  not null,
  sektion     text not null check (sektion in ('veckans', 'alltid')),
  namn        text not null,
  beskrivning text,
  pris        int,
  dag         text check (dag in ('måndag', 'tisdag', 'onsdag', 'torsdag', 'fredag')),
  kalla       text,
  hamtad      timestamptz not null default now()
);
create index if not exists lunch_vecka on lunch (restaurang, ar, vecka);

-- Övrig info per restaurang och vecka, t.ex. "Sallad, bröd och kaffe ingår".
create table if not exists lunch_info (
  restaurang text not null,
  ar         int  not null,
  vecka      int  not null,
  info       text[] not null default '{}',
  kalla      text,
  hamtad     timestamptz not null default now(),
  primary key (restaurang, ar, vecka)
);

-- Nyhetsrubriker. Bara rubrik, ingress och länk – inte artikeltexten.
create table if not exists nyheter (
  lank       text primary key,
  kalla      text not null,
  rubrik     text not null,
  ingress    text,
  publicerad timestamptz not null,
  hamtad     timestamptz not null default now()
);
create index if not exists nyheter_publicerad on nyheter (publicerad desc);
-- "nyheter" eller "ai" – AI-nyheterna visas under egen flik.
alter table nyheter add column if not exists amne text not null default 'nyheter';

-- Senaste läget per index/valuta, med en månads dagshistorik för minidiagram.
create table if not exists bors (
  symbol         text primary key,
  namn           text not null,
  typ            text not null check (typ in ('index', 'valuta')),
  varde          numeric not null,
  forandring_pct numeric,
  datum          date not null,
  historik       jsonb not null default '[]',
  kalla          text,
  hamtad         timestamptz not null default now()
);

-- Kommande släpp på Systembolaget, en rad per produkt. Ersätts helt vid varje hämtning.
create table if not exists systembolaget (
  artikelnummer text primary key,
  namn          text not null,
  namn2         text,
  kategori      text,
  typ           text,
  land          text,
  pris          numeric,
  volym_ml      numeric,
  sortiment     text not null,
  saljstart     date not null,
  hamtad        timestamptz not null default now()
);

-- RLS: alla (anon) får läsa, ingen får skriva. Hämtningen använder den hemliga
-- nyckeln (service_role) som går förbi RLS.
alter table lunch      enable row level security;
alter table lunch_info enable row level security;
alter table nyheter    enable row level security;
alter table bors       enable row level security;
alter table systembolaget enable row level security;

drop policy if exists "alla får läsa" on lunch;
drop policy if exists "alla får läsa" on lunch_info;
drop policy if exists "alla får läsa" on nyheter;
drop policy if exists "alla får läsa" on bors;
drop policy if exists "alla får läsa" on systembolaget;
create policy "alla får läsa" on lunch      for select to anon, authenticated using (true);
create policy "alla får läsa" on lunch_info for select to anon, authenticated using (true);
create policy "alla får läsa" on nyheter    for select to anon, authenticated using (true);
create policy "alla får läsa" on bors       for select to anon, authenticated using (true);
create policy "alla får läsa" on systembolaget for select to anon, authenticated using (true);

grant select on lunch, lunch_info, nyheter, bors, systembolaget to anon, authenticated;
grant select, insert, update, delete on lunch, lunch_info, nyheter, bors, systembolaget to service_role;
