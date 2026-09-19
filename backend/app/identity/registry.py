"""Voiceprint registry — stores speaker embeddings (192 numbers), never raw
audio, so a caller can be checked against a trusted 'name' later.

Dual storage: a local JSON file is ALWAYS written (so the app runs offline,
hassle-free), and — if Supabase is configured — the same voiceprint is mirrored
to the cloud (best-effort, never raises). Reads prefer local, then Supabase.
"""

import json
import os
from pathlib import Path

import httpx

from app.config import settings

_PATH = Path(os.getenv("VOICEPRINT_DB", ".voiceprints.json"))
_TABLE = "/rest/v1/voiceprints"


# ---- Supabase (optional cloud mirror, best-effort) ----

def _sb_on() -> bool:
    return bool(settings.supabase_url and settings.supabase_key)


def _sb_url() -> str:
    return settings.supabase_url.rstrip("/") + _TABLE


def _sb_headers(extra: dict | None = None) -> dict:
    h = {
        "apikey": settings.supabase_key,
        "Authorization": f"Bearer {settings.supabase_key}",
        "Content-Type": "application/json",
    }
    if extra:
        h.update(extra)
    return h


# ---- local JSON (always-on primary) ----

def _load() -> dict:
    if _PATH.exists():
        try:
            return json.loads(_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_local(db: dict) -> None:
    _PATH.write_text(json.dumps(db), encoding="utf-8")


# ---- public API ----

def save_voiceprint(name: str, embedding: list[float]) -> None:
    db = _load()
    db[name] = embedding
    _save_local(db)
    if _sb_on():
        try:  # upsert on the 'name' primary key
            httpx.post(
                _sb_url(),
                json={"name": name, "embedding": embedding},
                headers=_sb_headers({"Prefer": "resolution=merge-duplicates,return=minimal"}),
                timeout=8,
            )
        except Exception:
            pass  # local copy already saved — cloud is a mirror


def load_voiceprint(name: str):
    local = _load().get(name)
    if local is not None:
        return local
    if _sb_on():
        try:
            r = httpx.get(
                _sb_url(),
                params={"name": f"eq.{name}", "select": "embedding"},
                headers=_sb_headers(),
                timeout=8,
            )
            rows = r.json()
            if rows:
                return rows[0]["embedding"]
        except Exception:
            pass
    return None


def list_voiceprints() -> list[str]:
    names = set(_load().keys())
    if _sb_on():
        try:
            r = httpx.get(_sb_url(), params={"select": "name"}, headers=_sb_headers(), timeout=8)
            for row in r.json():
                names.add(row["name"])
        except Exception:
            pass
    return sorted(names)


def delete_voiceprint(name: str) -> bool:
    db = _load()
    existed = name in db
    if existed:
        del db[name]
        _save_local(db)
    if _sb_on():
        try:
            httpx.delete(
                _sb_url(),
                params={"name": f"eq.{name}"},
                headers=_sb_headers({"Prefer": "return=minimal"}),
                timeout=8,
            )
            existed = True
        except Exception:
            pass
    return existed
