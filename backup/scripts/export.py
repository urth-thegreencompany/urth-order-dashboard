#!/usr/bin/env python3
"""
urth. Order Dashboard — full data export.

Logs in as a staff user (same login as the dashboard), then pulls every row
from every table plus every uploaded attachment, and writes them to
backup/data/<timestamp>/ as both JSON (exact) and CSV (openable in Excel).

Requires only the Python that ships with macOS. No pip install, no Supabase CLI.

Your password is typed at the prompt, held in memory only, and never written
to disk, never logged, and never stored in this file.

Usage:
    python3 backup/scripts/export.py
"""

import csv
import getpass
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

TABLES = ["orders", "products", "subscriptions", "staff", "push_subscriptions"]
BUCKET = "order-files"
PAGE = 1000
TIMEOUT = 60

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
INDEX = os.path.join(ROOT, "index.html")
OUTBASE = os.path.join(ROOT, "backup", "data")


def read_config():
    """Pull SB_URL / SB_KEY straight from index.html so this never drifts."""
    try:
        src = open(INDEX, encoding="utf-8").read()
    except OSError as e:
        sys.exit("Could not read index.html (%s). Run this from the project folder." % e)
    url = re.search(r"SB_URL\s*=\s*'([^']+)'", src)
    key = re.search(r"SB_KEY\s*=\s*'([^']+)'", src)
    if not url or not key:
        sys.exit("Could not find SB_URL / SB_KEY in index.html.")
    return url.group(1).rstrip("/"), key.group(1)


def request(url, key, token=None, method="GET", body=None, raw=False):
    headers = {"apikey": key, "Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        payload = r.read()
    return payload if raw else json.loads(payload.decode())


def login(base, key):
    print("\nLog in with a staff account — the same email and password you use")
    print("to sign into the dashboard itself.\n")
    email = input("  Staff email    : ").strip()
    password = getpass.getpass("  Password       : ")  # not echoed, not stored
    if not email or not password:
        sys.exit("Email and password are both required.")
    try:
        res = request(base + "/auth/v1/token?grant_type=password", key,
                      method="POST", body={"email": email, "password": password})
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        sys.exit("\nLogin failed (HTTP %s).\n%s\n\nCheck the email/password, or try "
                 "signing into the dashboard in a browser first." % (e.code, detail))
    except urllib.error.URLError as e:
        sys.exit("\nCould not reach Supabase: %s" % e)
    del password
    token = res.get("access_token")
    if not token:
        sys.exit("Login returned no access token.")
    print("  -> signed in as %s\n" % res.get("user", {}).get("email", email))
    return token


def fetch_table(base, key, token, table):
    """Page through a table until exhausted. PostgREST caps each page."""
    rows, offset = [], 0
    while True:
        q = urllib.parse.urlencode({"select": "*", "order": "id.asc",
                                    "limit": PAGE, "offset": offset})
        try:
            page = request("%s/rest/v1/%s?%s" % (base, table, q), key, token)
        except urllib.error.HTTPError as e:
            print("  !! %s failed (HTTP %s) — skipping" % (table, e.code))
            return rows, False
        rows.extend(page)
        print("\r  %-14s %d rows" % (table, len(rows)), end="", flush=True)
        if len(page) < PAGE:
            break
        offset += PAGE
    print()
    return rows, True


def write_json(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False, default=str)


def write_csv(path, rows):
    """Flatten for Excel. jsonb columns are re-encoded as JSON text."""
    if not rows:
        open(path, "w").close()
        return
    cols = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v, ensure_ascii=False)
                            if isinstance(v, (dict, list)) else v)
                        for k, v in r.items()})


def download_attachments(base, key, token, orders, outdir):
    """Pull every file referenced by orders.attachments out of the private bucket."""
    wanted = []
    for o in orders:
        for a in (o.get("attachments") or []):
            if isinstance(a, dict) and a.get("path"):
                wanted.append((a["path"], a.get("name") or os.path.basename(a["path"])))
    if not wanted:
        print("  no attachments referenced by any order")
        return 0, 0
    os.makedirs(outdir, exist_ok=True)
    ok = fail = 0
    for i, (path, name) in enumerate(wanted, 1):
        print("\r  attachments    %d/%d" % (i, len(wanted)), end="", flush=True)
        try:
            blob = request("%s/storage/v1/object/%s/%s"
                           % (base, BUCKET, urllib.parse.quote(path)),
                           key, token, raw=True)
        except Exception:
            fail += 1
            continue
        dest = os.path.join(outdir, path.replace("/", "_"))
        with open(dest, "wb") as f:
            f.write(blob)
        ok += 1
    print()
    return ok, fail


def main():
    base, key = read_config()
    print("=" * 62)
    print("  urth. Order Dashboard — full data export")
    print("  project: %s" % base)
    print("=" * 62)

    token = login(base, key)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%SZ")
    outdir = os.path.join(OUTBASE, stamp)
    os.makedirs(outdir, exist_ok=True)

    manifest = {"exported_at_utc": datetime.now(timezone.utc).isoformat(),
                "project_url": base, "tables": {}, "attachments": {}, "gaps": []}

    print("Pulling tables:")
    orders = []
    for t in TABLES:
        rows, complete = fetch_table(base, key, token, t)
        write_json(os.path.join(outdir, t + ".json"), rows)
        write_csv(os.path.join(outdir, t + ".csv"), rows)
        manifest["tables"][t] = {"rows": len(rows), "complete": complete}
        if t == "orders":
            orders = rows

    print("\nPulling attachments from the private '%s' bucket:" % BUCKET)
    ok, fail = download_attachments(base, key, token, orders,
                                    os.path.join(outdir, "attachments"))
    manifest["attachments"] = {"downloaded": ok, "failed": fail}

    manifest["gaps"].append(
        "Staff auth users (Authentication -> Users) are NOT in this export. "
        "Listing them needs the service_role key or dashboard access. "
        "Staff logins must be recreated by hand after any restore.")

    write_json(os.path.join(outdir, "MANIFEST.json"), manifest)

    print("\n" + "=" * 62)
    print("  Done -> backup/data/%s" % stamp)
    for t, info in manifest["tables"].items():
        print("    %-14s %6d rows%s" % (t, info["rows"],
              "" if info["complete"] else "   (INCOMPLETE)"))
    print("    %-14s %6d files%s" % ("attachments", ok,
          "" if not fail else "   (%d failed)" % fail))
    print("=" * 62)
    print("\nNext: encrypt an off-laptop copy with")
    print("  bash backup/scripts/encrypt.sh backup/data/%s\n" % stamp)


if __name__ == "__main__":
    main()
