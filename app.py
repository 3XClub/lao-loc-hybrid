
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from market import fetch_soxl_bars
from strategy import build_signal_from_client
from cloud_store import load_state, save_state, configured
import os

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.secret_key = os.getenv("FLASK_SECRET_KEY", "CHANGE-ME-IN-RENDER")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")


@app.before_request
def require_login():
    # Keep login and static assets accessible.
    if request.endpoint in ("login", "static"):
        return None
    if not APP_PASSWORD:
        return "APP_PASSWORD is not configured in Render Environment.", 503
    if not session.get("logged_in"):
        return redirect(url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form.get("password","") == APP_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "비밀번호가 맞지 않습니다."
    return f"""<!doctype html>
<html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Lao-LOC+ Login</title>
<style>
body{{margin:0;background:#0b0f14;color:#e8edf3;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;display:grid;place-items:center;min-height:100vh}}
.box{{width:min(420px,calc(100% - 32px));background:#121821;border:1px solid #283241;border-radius:16px;padding:24px}}
h1{{margin:0 0 8px}}p{{color:#93a1b1}}input{{width:100%;box-sizing:border-box;background:#18202b;color:#fff;border:1px solid #364257;border-radius:9px;padding:12px;margin:10px 0}}
button{{width:100%;background:#4f8cff;color:#fff;border:0;border-radius:9px;padding:12px;font-weight:700;cursor:pointer}}
.err{{color:#ff7b7b;margin-top:8px}}
</style></head>
<body><div class='box'><h1>Lao-LOC+</h1><p>운용기록 보호를 위해 비밀번호를 입력하세요.</p>
<form method='post'><input name='password' type='password' autofocus placeholder='비밀번호'>
<button type='submit'>로그인</button></form><div class='err'>{error}</div></div></body></html>"""

@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/signal")
def signal():
    try:
        payload = request.get_json(silent=True) or {}
        bars = fetch_soxl_bars()
        if bars is None or len(bars) < 30:
            return jsonify({"error":"SOXL 시장 데이터를 충분히 불러오지 못했습니다."}), 503
        result = build_signal_from_client(bars, payload)
        result["data_source"] = bars.attrs.get("source","unknown")
        result["fallback_used"] = result["data_source"] == "bundled_fallback"
        return jsonify(result)
    except Exception as e:
        app.logger.exception("signal error")
        return jsonify({"error":str(e), "type":type(e).__name__}), 500


@app.get("/api/state")
def get_state():
    try:
        payload = load_state()
        return jsonify({"configured": configured(), "state": payload})
    except Exception as e:
        app.logger.exception("state load error")
        return jsonify({"error": str(e), "type": type(e).__name__}), 500

@app.put("/api/state")
def put_state():
    try:
        payload = request.get_json(force=True)
        save_state(payload)
        return jsonify({"ok": True})
    except Exception as e:
        app.logger.exception("state save error")
        return jsonify({"error": str(e), "type": type(e).__name__}), 500

@app.get("/api/health")
def health():
    return jsonify({"ok":True})

@app.errorhandler(Exception)
def unhandled(e):
    app.logger.exception("unhandled")
    return jsonify({"error":str(e), "type":type(e).__name__}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT","8000")), debug=True)
