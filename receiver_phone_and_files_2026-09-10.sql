-- urth. Order Dashboard — receiver contact number + order attachments
-- Paste this whole file into Supabase → SQL Editor → Run. Safe to re-run.

-- 1. Receiver contact number ------------------------------------------------
-- The number to call on arrival, shown under the address in the 📍 panel.
-- Separate from orders.phone, which stays the *customer* (the person who ordered).
alter table public.orders add column if not exists receiver_phone text;

-- 2. Attachments ------------------------------------------------------------
-- Metadata only: [{path,name,type,size}, ...]. The files themselves live in the
-- private `order-files` storage bucket; `path` is the key inside that bucket.
alter table public.orders add column if not exists attachments jsonb;

-- 3. Storage bucket ---------------------------------------------------------
-- Private (public = false): every view goes through a short-lived signed URL, so
-- customer photos are never on a guessable public link.
insert into storage.buckets (id, name, public, file_size_limit)
values ('order-files', 'order-files', false, 20971520)
on conflict (id) do update set public = false, file_size_limit = 20971520;

-- 4. Bucket policies --------------------------------------------------------
-- Same rule as the tables: any signed-in staff member can read/write. Dropped
-- first so the whole file stays safe to re-run.
drop policy if exists "order-files read"   on storage.objects;
drop policy if exists "order-files insert" on storage.objects;
drop policy if exists "order-files update" on storage.objects;
drop policy if exists "order-files delete" on storage.objects;

create policy "order-files read"   on storage.objects for select to authenticated
  using (bucket_id = 'order-files');
create policy "order-files insert" on storage.objects for insert to authenticated
  with check (bucket_id = 'order-files');
create policy "order-files update" on storage.objects for update to authenticated
  using (bucket_id = 'order-files') with check (bucket_id = 'order-files');
create policy "order-files delete" on storage.objects for delete to authenticated
  using (bucket_id = 'order-files');
