# Moving from personal accounts to company accounts

Written 2026-09-10. The project currently runs on the owner's **personal**
Supabase and Vercel accounts. The goal is to move both to the company setup,
which already exists (company email and billing are in place).

## The one rule: transfer, never rebuild

Both Supabase and Vercel support transferring an existing project to another
organization or team. **Use that.** Do not create fresh projects and migrate data
by hand.

Rebuilding means a new Supabase project ref, which means a new API URL and anon
key, which means editing `index.html` *and* `vercel.json` (the CSP pins the
Supabase origin in both `img-src` and `connect-src`), re-uploading every
attachment, re-importing ~7,675 orders, and recreating every staff login — with
downtime for a live shop throughout. A transfer keeps the same project ref, the
same URL, the same keys, and the same data. Nothing in the app changes.

The one case where rebuilding is justified is if Supabase Support cannot restore
account access at all. Treat that as the last resort, not the plan.

---

## Step 0 — Recover the Supabase account first

**Nothing else can proceed until this is done.** Transferring a project requires
being signed in as its owner, and that login is currently locked out.

The situation: the Supabase account `rheapillai.work@gmail.com` was created with
"Sign in with GitHub", and that personal GitHub account was permanently deleted.
Password reset is refused because the account never had a password — GitHub was
its only credential.

The ask to Supabase Support, phrased so it can be actioned:

> My Supabase account `rheapillai.work@gmail.com` was created via GitHub OAuth.
> That GitHub account has been permanently deleted, so I cannot use the GitHub
> login, and password reset is refused because the account has no password.
> Please unlink the dead GitHub identity and enable email/password sign-in.
> I control the account email and can respond from it.

Send it from that Gmail address — controlling the email is itself evidence. Use
`supabase.com/contact/support`; the in-dashboard form needs a login you don't have.

Attach as proof of ownership:
- Project ref `zfzofzwngvfjdzjkjolz` and the organization name
- **Billing records** — card last-4, an invoice ID, a receipt from the inbox.
  If it's a paid project this is the strongest evidence available.
- The deleted GitHub username and roughly when it was deleted

## Step 1 — The moment access is restored, do these four things

Before anything else, in this order. This is what stops a repeat.

1. **Set an email/password login** so the account no longer depends on any OAuth
   provider. This is the root cause of the lockout; remove it permanently.
2. **Add a second owner** on the organization, on a company address. Single-owner
   accounts are how lockouts become emergencies.
3. **Copy the database password** into the company password manager
   (Settings → Database). It's shown once. With it, migrations can be run over a
   direct connection even without dashboard access.
4. **Run the three pending migrations** — see `schema/MIGRATION-STATUS.md`. Three
   shipped features are dormant in production until this happens.

## Step 2 — Transfer Supabase to the company organization

Prerequisites: a company Supabase organization exists, with company billing
attached, and you are an owner of **both** organizations.

1. Sign in with the recovered account.
2. Create the company organization if it doesn't exist, paying with the company
   card — do this *before* transferring so billing lands correctly.
3. Project Settings → General → **Transfer project**, and pick the company org.
4. Add the company owners as members of the new org.

The project ref, URL, anon key, data, storage bucket, and staff logins all carry
over untouched. **No code change is needed** — verify by loading the live site and
confirming staff can still sign in.

Watch for: Supabase may require both organizations to be on compatible plans
before allowing a transfer. If the transfer option is greyed out, that's usually
why — match the plans first.

## Step 3 — Transfer Vercel to the company team

Prerequisites: a company Vercel team exists with company billing.

1. Sign into Vercel as the current owner.
2. Project Settings → Advanced → **Transfer Project** → the company team.
3. Reconnect the Git integration if it detaches. The repo is already in the
   `urth-thegreencompany` GitHub org, so the company team needs GitHub access
   granted to that org.
4. **Re-check the domain.** Custom domains sometimes need re-verification after a
   transfer — confirm the live URL still resolves before calling it done.
5. Push a trivial commit and confirm it auto-deploys, proving the git connection
   survived.

## Step 4 — GitHub

The repository already lives in the `urth-thegreencompany` organization, so the
code itself is company-owned. Two loose ends worth closing:

- **Org ownership.** Confirm the GitHub *org* has a company-controlled owner
  account, not only a personal one. Same single-point-of-failure logic as above.
- **The deploy key.** `~/.ssh/urth_dashboard_deploy` is repo-scoped and tied to
  this laptop. Fine for now. If the laptop is replaced, generate a new key and add
  it in the repo's Settings → Deploy keys.

Also worth fixing while you're there: git has **no configured identity** on this
machine (no `~/.gitconfig`, no local `user.name`/`user.email`), so commits are
authored as `rheapillai@Rheas-MacBook-Pro.local` — not a real address, and it
won't link to any GitHub profile. Set it to a company address:

```bash
git config --global user.name  "Your Name"
git config --global user.email "you@company-domain"
```

## Step 5 — Verify the whole chain

After both transfers:

- [ ] Live site loads and staff can sign in
- [ ] A test order saves, then appears on another device (proves Realtime works)
- [ ] `git push` triggers a Vercel deploy
- [ ] Supabase billing shows the company card
- [ ] Vercel billing shows the company card
- [ ] At least two people have owner access to each service
- [ ] Database password and both encryption passphrases are in the company
      password manager
- [ ] A fresh backup runs clean (`python3 backup/scripts/export.py`)

## What stays personal, and needs a decision

- The **Claude/AI subscription** this project is being built with is personal.
  It doesn't affect the running app at all — it's a development tool — but if the
  company should own it, move it separately.
- The **Gmail address** on the Supabase account is a work-flavoured personal
  address. Once access is recovered, consider changing the account email to a
  company address, though it's safer to do that *after* the transfer completes
  rather than mid-recovery.

## Order of operations, condensed

```
recover Supabase access
  -> add password login + 2nd owner + save DB password
  -> run pending migrations
  -> transfer Supabase project to company org
  -> transfer Vercel project to company team
  -> verify the chain above
```

Do not start Step 2 before Step 1 is complete. Recovering access and then
immediately transferring, without first removing the OAuth-only dependency,
risks recreating the same lockout inside the company account.
