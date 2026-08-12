-- urth. dashboard — multiple polaroids per order (2026-08-12)
-- Paste this whole block into Supabase → SQL Editor → Run. Safe to re-run.

-- 1) How many polaroids the order includes. The existing `polaroid` boolean stays as an
--    auto-derived summary (true when the count is 1 or more), so anything still reading it
--    keeps working.
alter table orders add column if not exists polaroid_qty integer default 0;

-- 2) Backfill: every order that already had a polaroid ticked counts as exactly 1.
update orders set polaroid_qty = 1 where polaroid is true and coalesce(polaroid_qty,0) = 0;
