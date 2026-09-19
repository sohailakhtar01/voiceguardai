"""Optional Supabase persistence (via its PostgREST API — no extra SDK needed).

Best-effort: if SUPABASE_URL / SUPABASE_KEY aren't set, this no-ops. It never
raises — saving a record must never break the analysis response."""

import httpx

from app.config import settings


def save_analysis(record: dict) -> bool:
    if not settings.supabase_url or not settings.supabase_key:
        return False
    try:
        url = settings.supabase_url.rstrip("/") + "/rest/v1/analyses"
        headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        httpx.post(url, json=record, headers=headers, timeout=5)
        return True
    except Exception:
        return False
