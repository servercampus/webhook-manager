#!/bin/sh
set -e

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
USERS_FILE="$SCRIPT_DIR/app/users.json"

printf "Benutzername: "
read USERNAME

# Passwort-Eingabe (ohne Echo, falls TTY vorhanden)
if [ -t 0 ]; then stty -echo; fi
printf "Passwort: "
read PASSWORD
printf "\n"
if [ -t 0 ]; then stty echo; fi

gen_hash_with_python() {
  CMD="$1"
  "$CMD" - << 'PY'
from werkzeug.security import generate_password_hash
import sys
print(generate_password_hash(sys.argv[1]))
PY
  "$2"
}

supports_werkzeug() {
  CMD="$1"
  "$CMD" -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('werkzeug.security') else 1)" >/dev/null 2>&1
}

# 1) Lokales Python bevorzugen, 2) python3, 3) Docker-Fallback via gebautem Image
if command -v python >/dev/null 2>&1 && supports_werkzeug python; then
  HASH=$(gen_hash_with_python python "$PASSWORD")
elif command -v python3 >/dev/null 2>&1 && supports_werkzeug python3; then
  HASH=$(gen_hash_with_python python3 "$PASSWORD")
else
  echo "Kein lokales Python gefunden. Nutze Docker-Image als Fallback..."
  # Nutzt das bereits gebaute Compose-Image, das werkzeug enthält
  HASH=$(docker run --rm webhook-manager-webhook-manager:latest \
    python -c "from werkzeug.security import generate_password_hash;import sys;print(generate_password_hash(sys.argv[1]))" \
    "$PASSWORD")
fi

# Schreibe/aktualisiere users.json sicher
if command -v python >/dev/null 2>&1; then PYBIN=python; elif command -v python3 >/dev/null 2>&1; then PYBIN=python3; else PYBIN=""; fi

if [ -n "$PYBIN" ]; then
  "$PYBIN" - "$USERS_FILE" "$USERNAME" "$HASH" << 'PY'
import json, os, sys
path, username, pw_hash = sys.argv[1:4]
data = {}
if os.path.exists(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f) or {}
    except Exception:
        data = {}
data[username] = pw_hash
tmp = path + '.tmp'
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
os.replace(tmp, path)
print(f"Benutzer '{username}' hinzugefügt/aktualisiert.")
PY
else
  # Ohne lokales Python: Schreibe JSON via Docker und liefere Daten per ENV
  docker run --rm -e USERNAME="$USERNAME" -e HASH="$HASH" -v "$SCRIPT_DIR/app":/app webhook-manager-webhook-manager:latest \
    python - << 'PY'
import json, os
path = '/app/users.json'
username = os.environ['USERNAME']
pw_hash = os.environ['HASH']
data = {}
if os.path.exists(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f) or {}
    except Exception:
        data = {}
data[username] = pw_hash
tmp = path + '.tmp'
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
os.replace(tmp, path)
print(f"Benutzer '{username}' hinzugefügt/aktualisiert.")
PY
fi

echo "Fertig."

