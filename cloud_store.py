
import os, json, requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")  # legacy fallback
STATE_ID = os.getenv("APP_STATE_ID", "main")

def _key():
    return SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY

def configured():
    return bool(SUPABASE_URL and _key())

def _headers():
    key = _key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

def load_state():
    if not configured():
        return None
    url = f"{SUPABASE_URL}/rest/v1/app_state"
    r = requests.get(
        url,
        headers=_headers(),
        params={"id": f"eq.{STATE_ID}", "select": "payload"},
        timeout=15,
    )
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return None
    return rows[0].get("payload")

def save_state(payload):
    if not configured():
        raise RuntimeError("Supabase 환경변수가 설정되지 않았습니다.")
    url = f"{SUPABASE_URL}/rest/v1/app_state"
    body = {"id": STATE_ID, "payload": payload}
    headers = _headers().copy()
    headers["Prefer"] = "resolution=merge-duplicates,return=representation"
    r = requests.post(
        url + "?on_conflict=id",
        headers=headers,
        data=json.dumps(body, ensure_ascii=False),
        timeout=15,
    )
    r.raise_for_status()
    return True
