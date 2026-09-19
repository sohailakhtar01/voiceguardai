from app import storage
from app.config import settings


def test_save_noop_without_config(monkeypatch):
    # With no Supabase keys configured, save must no-op and return False,
    # never raise. (Cleared explicitly so a populated .env can't hit the cloud.)
    monkeypatch.setattr(settings, "supabase_url", "")
    monkeypatch.setattr(settings, "supabase_key", "")
    assert storage.save_analysis({"case_id": "VG-TEST", "tier": "low"}) is False
