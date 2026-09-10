-- urth. dashboard — Owners + multi-person Makers/Owners
-- Paste this whole block into Supabase → SQL Editor → Run. Safe to re-run.

-- 1) Per-order multi-person fields (jsonb arrays). Legacy `maker` text stays as an
--    auto-derived comma-joined summary, so nothing that reads it today breaks.
alter table orders add column if not exists makers jsonb;
alter table orders add column if not exists owners jsonb;

-- 2) Shared, synced staff roster — makers + owners, addable from any laptop via the app.
create table if not exists staff (
  id bigint generated always as identity primary key,
  name text not null,
  role text not null check (role in ('maker','owner')),
  created_at timestamptz default now(),
  unique (name, role)
);

alter table staff enable row level security;

-- any logged-in staff can read/write (same policy as the other tables)
drop policy if exists staff_rw on staff;
create policy staff_rw on staff for all to authenticated using (true) with check (true);

-- 3) Seed the 7 existing makers so the list is populated on first load.
insert into staff (name, role) values
  ('Surjith','maker'),('Ganesh','maker'),('Ranjith','maker'),('Dharma','maker'),
  ('Dinesh','maker'),('Rickwin','maker'),('Pradeep','maker')
on conflict (name, role) do nothing;

-- Owners start empty — add your operations heads from the app
-- (Add order → Owners → "＋ Add"), or seed a few here, e.g.:
-- insert into staff (name, role) values ('Rhea','owner') on conflict do nothing;
