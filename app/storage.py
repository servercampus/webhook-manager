import os
import json
import uuid
import secrets
from typing import Dict, Optional, Tuple

DATA_DIR = os.path.dirname(__file__)
USERS_FILE = os.path.join(DATA_DIR, "users.json")
WEBHOOKS_FILE = os.path.join(DATA_DIR, "webhooks.json")


def _read_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _write_json(path: str, data: dict) -> None:
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def get_all_webhooks() -> Dict[str, dict]:
    return _read_json(WEBHOOKS_FILE)


def add_webhook(discord_url: str) -> Tuple[str, str]:
    """Create a webhook and return (wid, secret)."""
    wid = str(uuid.uuid4())[:8]
    secret_value = secrets.token_hex(20)
    data = get_all_webhooks()
    data[wid] = {"discord_url": discord_url, "secret": secret_value}
    _write_json(WEBHOOKS_FILE, data)
    return wid, secret_value


def get_webhook(wid: str) -> Optional[dict]:
    return get_all_webhooks().get(wid)


def get_all_users() -> Dict[str, str]:
    """Return username -> password_hash"""
    return _read_json(USERS_FILE)


def add_user(username: str, password_hash: str) -> None:
    users = get_all_users()
    users[username] = password_hash
    _write_json(USERS_FILE, users)
