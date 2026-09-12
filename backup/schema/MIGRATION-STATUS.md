# Migration status — verified 2026-09-10

Determined by probing the live API (a column that doesn't exist returns HTTP 400;
a missing table returns 404). No dashboard access was needed or used.

## Applied and live

| Migration | Evidence |
|---|---|
| Base schema (orders / products / subscriptions) | all base columns return 200 |
| `staff_and_multiperson_2026-08-01.sql` | `staff` table 200; `orders.makers`, `orders.owners` present |
| Multi-item orders + discount | `orders.items`, `orders.discount` present |

## NOT applied — pending, blocked by the dashboard lockout

| Migration | Missing in production |
|---|---|
| `polaroid_qty_2026-08-12.sql` | `orders.polaroid_qty` |
| `push_setup_2026-07-20.sql` | the whole `push_subscriptions` table |

**Correction (probed 2026-09-12):** `orders.receiver_phone` and `orders.attachments` **do exist**
in production — `select` on both returns 200 with the anon key — so `HAS_FILES` and
`HAS_RECV_PHONE` are true and the attachments + receiver-number UI is live for staff. Somebody
ran `receiver_phone_and_files_2026-09-10.sql` after all. Whether the `order-files` **bucket** and
its storage policies exist can't be confirmed with the anon key (a list on a real and a fake
bucket both return `[]` under RLS); if uploads fail with "bucket not found", that half of the
migration still needs to run. `polaroid_qty` and `push_subscriptions` remain missing.

### What this means in practice

The app is written to survive exactly this. It probes on load — `HAS_POLA_QTY`,
`HAS_FILES`, `HAS_RECV_PHONE` — and hides any feature whose column is absent.
So nothing is broken or throwing errors for staff. But three shipped features are
**dormant in production**:

- **Attachments** — the upload section is hidden outright. No photos or PDFs can
  be attached to orders.
- **Receiver contact number** — the field is hidden; deliveries have no separate
  arrival number.
- **Polaroid quantity** — polaroids still work as a yes/no. The ± counter is
  inactive, so multiples aren't billed per unit.

These are the direct, ongoing cost of the Supabase lockout.

### To apply once dashboard access is restored

Run in this order in Supabase → SQL Editor. All are safe to re-run:

1. `polaroid_qty_2026-08-12.sql`
2. `receiver_phone_and_files_2026-09-10.sql`
3. `push_setup_2026-07-20.sql` *(only if push notifications are wanted; the Edge
   Function in `supabase/functions/notify-order-status/` must also be deployed)*

Or simply run `backup/schema/schema.sql`, which is idempotent and brings the
database to the full intended state in one paste.

**Re-verify afterwards** by re-running the probe — replace `COLUMN` below:

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://zfzofzwngvfjdzjkjolz.supabase.co/rest/v1/orders?select=COLUMN&limit=1" \
  -H "apikey: <the SB_KEY from index.html>"
```

`200` = the column exists. `400` = still missing.
