# Developer handoff — urth. Order Dashboard

Written 2026-09-10. For a developer picking this up cold, or for reconstructing
the system if access to any account is lost.

`CLAUDE.md` in the repo root documents the *code* — architecture, data model,
design decisions, and why things are built the way they are. **Read it first.**
This document covers what CLAUDE.md deliberately doesn't: accounts, access,
deployment, current operational state, and risk.

## What it is

A mobile-first order-tracking dashboard for urth. — The Green Company, a flower
shop in Bangalore. It replaced a monthly-tab Excel workbook. B2C orders only;
Shopify B2B was scoped as phase 2 and is not built.

Roughly 7,675 historical orders (April 2024 – July 2026) were imported from that
workbook. Ops and logistics staff use it on phones — mobile is the primary
surface, not a nice-to-have.

## Stack, in one breath

One static `index.html` (~1,770 lines of HTML + CSS + vanilla JS, no framework,
no build step) on Vercel, talking to Supabase for Postgres, Auth, Realtime, and
Storage. Deploying is `git push`. That simplicity was a deliberate choice so a
non-technical owner could host it without a toolchain — preserve it.

## The accounts involved

| Service | What it holds | Access route |
|---|---|---|
| **GitHub** | Source. `urth-thegreencompany/urth-order-dashboard` | SSH deploy key, `~/.ssh/urth_dashboard_deploy`, aliased `github-urth` in `~/.ssh/config` |
| **Vercel** | Hosting. Git-connected, auto-deploys `main` | Owner's Vercel login |
| **Supabase** | Database, auth, storage, realtime. Project `zfzofzwngvfjdzjkjolz` | Dashboard login (**locked out** — see below) |
| **Staff logins** | Individual email/password accounts for shop staff | Created manually in the Supabase dashboard |

The SSH key is **repo-scoped** — it can push to this one repository and does
nothing else. It is not a personal account credential. Confirm with
`ssh -T git@github-urth`, which greets you with the repo name rather than a username.

## Deploying

```bash
git push            # that's it
```

Vercel is git-connected to `main`; every push auto-deploys with no manual step.
There is no staging environment and no build — the file that's committed is the
file that's served. Test locally by opening `index.html` in a browser first.

**Caveat:** the security headers in `vercel.json` (CSP and friends) only apply on
Vercel. They don't exist on `file://` or a local server, so something can work
locally and be blocked in production. If you add any new external origin — a
script, font, or API — add it to the CSP in `vercel.json` or the browser will
block it silently in production.

GitHub Pages was the original host and is now unpublished. Vercel is the sole
live host; don't republish Pages, or two versions go live at once.

## Current state — read this before touching anything

**The Supabase dashboard account is locked out.** It was created via "Sign in
with GitHub" using a personal GitHub account that has since been permanently
deleted. Password reset is refused because the account has no password — GitHub
was its only credential. Recovery is in progress with Supabase Support.

Consequences, verified live on 2026-09-10:

- The **app is fully operational.** Staff log in, orders flow, nothing is down.
  Dashboard access and app auth are separate systems.
- **No migrations can be run.** Three are pending — see
  `schema/MIGRATION-STATUS.md`. Their features are shipped but dormant in
  production: attachments, receiver phone, and polaroid quantity.
- **No staff can be added or removed**, and no auth settings can be changed.

Two things were confirmed healthy despite the lockout:

- Public signup is **OFF** (`disable_signup: true`), so nobody can self-register
  into the data. CLAUDE.md still describes this as an open gap — it is closed.
- RLS is genuinely enforcing. Anon-key reads return `[]` for every table.

## The trust model, and why the embedded key is fine

`index.html` contains `SB_URL` and `SB_KEY` in plain sight. That is intentional
and safe: `SB_KEY` is the **anon** key, and RLS requires an authenticated session
for every table, so the key alone reads nothing. This was tested directly — anon
requests to `orders` and `products` return empty arrays.

**Never embed the `service_role` key.** It bypasses RLS entirely.

Two client-side passcodes exist and are *not* security — they're friction to stop
mistakes by people who are already logged in:

- `EDIT_PASS` gates all mutations. Everyone who logs in can view; editing is
  behind the header's lock toggle.
- `CAL_PASS` gates the Calendar tab. Separate from `EDIT_PASS` since Aug 2026 so
  either can be rotated alone.

Real access control is Supabase Auth plus RLS. Treat those passcodes as
shared-secret conveniences, nothing more.

## Things that will bite you

- **Dates must use `Date.UTC`.** The shop runs in IST (+5:30). An earlier
  local-time implementation collapsed every day of a range into "today". Do not
  reintroduce `new Date(s+'T00:00:00')` round-tripped through `toISOString()`.
- **Everything user-entered goes through `esc()`** before landing in `innerHTML`.
  Stored XSS here would expose every staff session. `textContent` is exempt.
- **The `order-files` bucket must stay private.** Making it public would put
  customer photos on guessable, unauthenticated URLs. All views go through
  short-lived signed URLs.
- **supabase-js is pinned with SRI.** To bump it, fetch the new
  `dist/umd/supabase.js`, recompute the sha384, and update both attributes.
  Don't revert to the floating `@2` URL.
- **`window.open` must be claimed synchronously** on tap, before any `await` —
  Safari blocks it once a user gesture has been broken by an await.
- **New columns use `add column if not exists`**, and the app probes for them on
  load (`HAS_FILES`, `HAS_RECV_PHONE`, `HAS_POLA_QTY`) so it can deploy safely
  before the migration is run. Follow that pattern; it's why the lockout is
  survivable.
- **Never commit customer data.** `*.csv`, `*.xlsx`, the legacy import SQL, and
  `backup/data/` are gitignored. The repo is the deploy source.

## Known data-quality debt

Inherited from the Excel workbook, never cleaned:

- Maker name spelling drift ("Michael" / "Micheal")
- `payment_status` mixes status (Paid/Pending) with method (Cash/Card/Razorpay)
- ~700 historical orders have no `value_inr`, so revenue is understated
- Two order-numbering schemes coexist: the shop sequence (`#2001`+, now ~`#2041`)
  and a 6-digit `#118xxx` scheme. New auto-assigned numbers stay in the `#2xxx`
  sequence — `NEXT_NO` ignores anything ≥ 100000.

## Not built

Shopify webhook ingestion (`orders/create` → Edge Function), the historical
cleanup pass, granular per-role RLS, and a bulk CSV upload UI for the catalogue.

## If you lose everything

`backup/README.md` has the full restore path. Short version: `schema/schema.sql`
rebuilds the database structure from zero, an export in `backup/data/` (or a
decrypted one from `backup/encrypted/`) refills it, and the app source is in git.
The single unbackupable piece is **staff login accounts** — those must be
recreated by hand.
