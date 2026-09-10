#!/usr/bin/env bash
# Encrypt one export folder into a single passphrase-protected file that is
# SAFE TO COMMIT — so a copy survives even if this laptop is lost.
#
#   bash backup/scripts/encrypt.sh backup/data/2026-09-10_120000Z
#
# Uses AES-256 via openssl (built into macOS). Anyone with the passphrase can
# restore it; anyone without it gets nothing. LOSE THE PASSPHRASE = LOSE THE FILE.
set -euo pipefail

SRC="${1:-}"
if [ -z "$SRC" ] || [ ! -d "$SRC" ]; then
  echo "Usage: bash backup/scripts/encrypt.sh <export folder>"
  echo "Available exports:"; ls -1 backup/data 2>/dev/null | grep -v gitkeep || echo "  (none yet — run export.py first)"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STAMP="$(basename "$SRC")"
OUT="$ROOT/backup/encrypted/urth-backup-$STAMP.tar.gz.enc"
mkdir -p "$ROOT/backup/encrypted"

echo "Compressing $SRC ..."
TAR="$(mktemp -t urthbk).tar.gz"
tar -czf "$TAR" -C "$(dirname "$SRC")" "$STAMP"
RAWMB=$(( $(wc -c < "$TAR") / 1024 / 1024 ))
echo "  archive: ${RAWMB} MB"

if [ "$RAWMB" -gt 80 ]; then
  echo
  echo "  !! ${RAWMB} MB is large for a git repo (GitHub hard-rejects >100 MB)."
  echo "     Committing big binaries bloats history permanently and cannot be undone easily."
  echo "     Consider re-running with attachments excluded, or store this one off-git."
  printf "     Continue anyway? [y/N] "; read -r a; [ "$a" = "y" ] || { rm -f "$TAR"; exit 1; }
fi

echo
echo "Choose a passphrase. Store it in your password manager NOW — there is no recovery."
openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt -in "$TAR" -out "$OUT"
rm -f "$TAR"

echo
echo "Encrypted -> backup/encrypted/$(basename "$OUT")"
echo "Safe to commit. Restore with:"
echo "  bash backup/scripts/decrypt.sh backup/encrypted/$(basename "$OUT")"
