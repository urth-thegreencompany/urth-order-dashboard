# backup/

Everything needed to survive losing access to Supabase, this laptop, or both.

Created 2026-09-10, while the Supabase dashboard account was locked out (the
GitHub account it was created through had been deleted).

## What's here

```
backup/
  README.md                  <- you are here
  HANDOFF.md                 <- developer handoff: how the whole system works
  OWNERSHIP-MIGRATION.md     <- moving personal accounts -> company accounts
  schema/
    schema.sql               <- rebuilds the entire database from zero
    MIGRATION-STATUS.md      <- what's live vs pending (verified, not assumed)
  scripts/
    export.py                <- pulls all data out via a staff login
    encrypt.sh               <- turns an export into one committable encrypted file
    decrypt.sh               <- restores it
  data/                      <- raw exports land here. GITIGNORED (contains PII).
  encrypted/                 <- encrypted exports. Tracked in git on purpose.
```

## Two layers, on purpose

| Layer | Location | In git? | Protects against |
|---|---|---|---|
| Raw export | `backup/data/` | **No** — gitignored | Losing Supabase access |
| Encrypted copy | `backup/encrypted/` | **Yes** — tracked | Losing this laptop |

Raw exports hold customer names, phone numbers, and addresses. This repo is also
the Vercel deploy source, so anything committed here is one push from being
public-adjacent. `backup/data/` is therefore gitignored, and that rule is
verified — `git check-ignore` confirms it. The encrypted copy is safe to commit
because without the passphrase it is meaningless.

## Taking a backup

```bash
# 1. Export everything (asks for a staff email + password)
python3 backup/scripts/export.py

# 2. Encrypt a copy that can safely live on GitHub
bash backup/scripts/encrypt.sh backup/data/<timestamp>

# 3. Commit the encrypted file
git add backup/encrypted/ && git commit -m "Backup: <date>" && git push
```

Step 1 asks for the **same email and password used to sign into the dashboard**.
It is typed at the prompt, kept in memory only, and never written to disk or
logged. It is not the Supabase dashboard login (that's a different account, and
the one currently locked out).

**Store the encryption passphrase in a password manager immediately.** There is
no recovery path. A lost passphrase means a lost backup.

## Restoring

```bash
bash backup/scripts/decrypt.sh backup/encrypted/urth-backup-<stamp>.tar.gz.enc
```

To rebuild onto a fresh Supabase project:

1. Create the project, then run `backup/schema/schema.sql` in the SQL Editor.
2. Import the CSVs from the export via Table Editor → Import.
3. Re-upload `attachments/` into a new private `order-files` bucket.
4. **Recreate staff logins by hand** (see gap below).
5. Update `SB_URL` / `SB_KEY` in `index.html`, add the new origin to
   `img-src` and `connect-src` in `vercel.json`, then push.

## Known gap: staff logins are not exportable

Supabase auth users (Authentication → Users) cannot be read with a normal staff
login — it needs the `service_role` key or dashboard access, neither of which is
available while locked out. **Staff accounts must be recreated by hand after any
restore.** Keep a list of who has a login somewhere outside this repo.

This is the one piece of the system with no backup. It's also cheap to rebuild:
a handful of email/password accounts, with "Confirm email" turned OFF.

## What a backup does and doesn't cover

Covered: every row of `orders`, `products`, `subscriptions`, `staff`,
`push_subscriptions`; every file in the `order-files` bucket; the full schema;
the app source (in git); the Edge Function source (in git).

Not covered: staff login accounts, auth settings, Vercel project config,
DNS records, and the Supabase project's own database password.
