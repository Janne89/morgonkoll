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

-- RLS: alla (anon) får läsa, ingen får skriva. Hämtningen använder den hemliga
-- nyckeln (service_role) som går förbi RLS.
alter table lunch      enable row level security;
alter table lunch_info enable row level security;

drop policy if exists "alla får läsa" on lunch;
drop policy if exists "alla får läsa" on lunch_info;
create policy "alla får läsa" on lunch      for select to anon, authenticated using (true);
create policy "alla får läsa" on lunch_info for select to anon, authenticated using (true);

grant select on lunch, lunch_info to anon, authenticated;
grant select, insert, update, delete on lunch, lunch_info to service_role;
