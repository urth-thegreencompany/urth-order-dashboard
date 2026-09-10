#!/usr/bin/env bash
# Restore an encrypted backup created by encrypt.sh.
#   bash backup/scripts/decrypt.sh backup/encrypted/urth-backup-<stamp>.tar.gz.enc
# Prompts for the passphrase and unpacks into backup/data/.
set -euo pipefail

ENC="${1:-}"
if [ -z "$ENC" ] || [ ! -f "$ENC" ]; then
  echo "Usage: bash backup/scripts/decrypt.sh <file.tar.gz.enc>"
  echo "Available:"; ls -1 backup/encrypted 2>/dev/null || echo "  (none)"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
mkdir -p "$ROOT/backup/data"
TAR="$(mktemp -t urthrs).tar.gz"

echo "Passphrase for $(basename "$ENC"):"
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -in "$ENC" -out "$TAR"
tar -xzf "$TAR" -C "$ROOT/backup/data"
rm -f "$TAR"
echo "Restored into backup/data/"
ls -1 "$ROOT/backup/data"
