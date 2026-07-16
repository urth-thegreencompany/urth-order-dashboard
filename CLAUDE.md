# urth. Order Dashboard

A mobile-first order-tracking dashboard for **urth. — The Green Company**, a Bangalore flower shop.
Replaces a monthly-tab Excel sheet. B2C orders only for now (Shopify B2B is phase 2, not yet built).

## Stack
- Single static `index.html` (HTML/CSS/vanilla JS — no build step, no framework)
- Hosted on **GitHub Pages** (free, static hosting)
- Backend: **Supabase** (Postgres + Auth + Realtime)
- Supabase JS client loaded via CDN: `@supabase/supabase-js@2`

## Supabase project
- Project URL: `https://zfzofzwngvfjdzjkjolz.supabase.co`
- Anon key is embedded in `index.html` (`SB_URL` / `SB_KEY` constants) — this is intentional and safe
  because Row Level Security is ON and requires an authenticated session. Never embed the `service_role` key.
- Auth: email/password, staff added manually via Supabase Dashboard → Authentication → Users.
  "Confirm email" is OFF so staff can be added without an inbox round-trip.

## Schema (as currently deployed)

```sql
create type order_status as enum
  ('new','confirmed','prep','ready','dispatched','delivered','cancelled');

products (
  id bigint identity pk, name text, type text default 'Bouquet',
  price_inr integer default 0, flowers text
)

subscriptions (
  id bigint identity pk, client text, type text, preferred_day text,
  status text default 'On-Going', value_inr integer default 0,
  flower_prefs text, last_delivery date, end_date date
)

orders (
  id bigint identity pk, order_no text, customer_name text,
  order_date date, delivery_date date not null,
  order_type text, details text, value_inr integer default 0,
  delivery_time text, source text, transport_mode text, maker text,
  payment_status text, address text, status order_status default 'new',
  urgent boolean default false, created_at timestamptz default now(),
  message_note text,       -- customer's note to include with the flowers
  polaroid boolean default false,  -- whether a polaroid photo is requested
  remarks text             -- internal team notes, not customer-facing
)
```
RLS: enabled on all three tables, policy = any `authenticated` user can read/write.

## Data model notes
- **Order numbers**: WhatsApp and Walk-in orders auto-assign the next sequential number
  (`#2001`, `#2002`, ...). **Website orders already have a Shopify-side order number** —
  that number is entered manually and preserved as-is, never overwritten.
- **New vs Repeat customer**: derived client-side by matching `customer_name` (case-insensitive)
  against earlier orders — not a stored column. Ideally should key on phone number instead
  of name once that's a captured field (currently isn't).
- **Delivery time** is a free-text slot: "Morning (8am–11am)", "Mid-Morning (10am–1pm)",
  "Afternoon (1pm–4pm)", "Evening (6pm–9pm)". Cards sort by this slot within a day so the
  team can see what needs to go out first.
- **Status pipeline**: new → confirmed → prep (in progress) → ready → dispatched → delivered,
  with cancelled as a side-branch (has a Restore action back to `new`). Cancelled orders are
  excluded from KPI counts/revenue but stay in the data.
- **Order types**: Bouquet (from catalogue, autofills price+flowers), Custom (colour palette +
  flower types, free text), Vase Arrangement (flowers + vase picker), Loose Flowers
  (multi-select from catalogue stems).
- **Urgent** is a boolean toggle (⚡) that visually rings the card and sorts it to the top of
  its delivery-time slot.

## Original data source
Historical orders (~7,675 rows, April 2024 – July 2026) were extracted from a legacy
"Master Order Sheet" Excel workbook with a new tab per month, and imported into Supabase via
CSV. Known data-quality issues inherited from that sheet, not yet cleaned:
- Owner/maker name spelling drift (e.g. "Michael" / "Micheal")
- Payment status column historically mixed status (Paid/Pending) with method (Cash/Card/Razorpay)
- ~700 historical orders have no `value_inr` recorded (shows as 0, understates revenue)

## Feature history / product decisions (why things are the way they are)
- Ops lead's top priority on open: "how many orders today, what are they" — hence Home tab
  opens to a date-range board, not a raw list.
- Logistics only needs address + transport mode once an order is marked Ready/Dispatched —
  marking Dispatched fires a toast notification (via Supabase Realtime on the `orders` table)
  so any other open dashboard sees it live. This replaces the old manual WhatsApp handoff.
- Subscriptions auto-surface as a card on whichever day matches their `preferred_day`.
- Calendar tab is passcode-gated client-side (not real auth) — passcode is `urth@001122`.
  This is a soft privacy gate, not security; real access control is Supabase Auth (login screen).
- Design language matches the urth. Shopify site: cream background (#F3EADF), deep forest green
  header (#23372B), terracotta/clay accent (#A4432B), serif "Fraunces" for headings, "Nunito Sans"
  for body text.
- Mobile is the primary usage surface — ops/logistics use phones. Sheets (add/edit order,
  reschedule) are bottom-sheet style with a sticky "‹ Back" button and support the phone's
  native back gesture (via `history.pushState`/`popstate`) to close.

## Not yet built (known next steps)
- Shopify webhook integration (`orders/create` → Supabase Edge Function) to auto-ingest
  website orders instead of manual entry — deliberately deferred to a later phase.
- Historical data cleanup pass (name normalization, payment status/method split, backfilling
  missing order values) — SQL not yet written.
- Granular RLS policies (e.g. logistics role restricted to certain fields) — currently all
  authenticated users have full read/write on all tables.
- Bulk CSV upload UI for the product catalogue (currently a placeholder toast; real bulk
  import is done manually via Supabase Table Editor).

## Working conventions
- Keep this a single-file app unless there's a strong reason to split it — simplicity was a
  deliberate choice for a non-technical owner to host on GitHub Pages with no build step.
- Preserve the design system (colors/fonts above) in any new UI.
- When adding DB columns, always use `alter table ... add column if not exists ...` so
  migrations are safe to re-run, and tell the user exactly what SQL to paste into the
  Supabase SQL Editor (they are non-technical and self-serve there).
