
import os
import json
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, render_template, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

from market import fetch_soxl_bars
from strategy import build_signal, account_state, apply_fill, initialize_database, get_db

APP_TZ = os.getenv("APP_TIMEZONE", "Asia/Ho_Chi_Minh")
DB_PATH = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "lao_loc.db"))

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

def conn():
    return get_db(DB_PATH)

def generate_daily_signal(force=False):
    bars = fetch_soxl_bars()
    if bars is None or len(bars) < 30:
        raise RuntimeError("SOXL 시장 데이터를 충분히 불러오지 못했습니다.")
    c = conn()
    try:
        latest_market_date = str(bars.iloc[-1]["Date"].date())
        existing = c.execute(
            "SELECT id FROM signals WHERE market_date = ? ORDER BY id DESC LIMIT 1",
            (latest_market_date,)
        ).fetchone()
        if existing and not force:
            return c.execute("SELECT * FROM signals WHERE id=?", (existing["id"],)).fetchone()

        state = account_state(c, float(bars.iloc[-1]["Close"]))
        signal = build_signal(c, bars, state)
        created_at = datetime.now(ZoneInfo(APP_TZ)).isoformat(timespec="seconds")

        c.execute(
            """INSERT INTO signals
               (market_date, created_at, close, adx14, ret20, hybrid_strict,
                account_json, orders_json, note)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                signal["market_date"], created_at, signal["close"], signal["adx14"],
                signal["ret20"], 1 if signal["hybrid_strict"] else 0,
                json.dumps(signal["account"], ensure_ascii=False),
                json.dumps(signal["orders"], ensure_ascii=False),
                signal["note"],
            )
        )
        c.commit()
        sid = c.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        return c.execute("SELECT * FROM signals WHERE id=?", (sid,)).fetchone()
    finally:
        c.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.get("/api/state")
def api_state():
    bars = fetch_soxl_bars()
    last_close = float(bars.iloc[-1]["Close"]) if bars is not None and len(bars) else None
    c = conn()
    try:
        state = account_state(c, last_close)
        latest_signal = c.execute("SELECT * FROM signals ORDER BY id DESC LIMIT 1").fetchone()
        layers = c.execute(
            "SELECT * FROM layers WHERE remaining_qty > 0 ORDER BY id DESC"
        ).fetchall()
        fills = c.execute(
            "SELECT * FROM fills ORDER BY id DESC LIMIT 100"
        ).fetchall()
        return jsonify({
            "state": state,
            "last_close": last_close,
            "layers": [dict(r) for r in layers],
            "fills": [dict(r) for r in fills],
            "latest_signal": serialize_signal(latest_signal),
        })
    finally:
        c.close()

@app.get("/api/signals")
def api_signals():
    c = conn()
    try:
        rows = c.execute("SELECT * FROM signals ORDER BY id DESC LIMIT 365").fetchall()
        return jsonify([serialize_signal(r) for r in rows])
    finally:
        c.close()

@app.post("/api/signals/generate")
def api_generate_signal():
    row = generate_daily_signal(force=True)
    return jsonify(serialize_signal(row))

@app.post("/api/fills")
def api_fill():
    payload = request.get_json(force=True)
    c = conn()
    try:
        result = apply_fill(c, payload)
        c.commit()
        return jsonify(result)
    except ValueError as e:
        c.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        c.close()

@app.post("/api/settings/reset")
def api_reset():
    payload = request.get_json(force=True) or {}
    initial_budget = float(payload.get("initial_budget", 10000))
    if initial_budget <= 0:
        return jsonify({"error": "운용금은 0보다 커야 합니다."}), 400
    c = conn()
    try:
        c.executescript("""
            DELETE FROM fills;
            DELETE FROM layers;
            DELETE FROM signals;
            DELETE FROM cash_ledger;
        """)
        c.execute("UPDATE settings SET value=? WHERE key='initial_budget'", (str(initial_budget),))
        c.execute("INSERT INTO cash_ledger(ts, amount, reason) VALUES(datetime('now'), ?, 'INITIAL')", (initial_budget,))
        c.commit()
        return jsonify({"ok": True, "initial_budget": initial_budget})
    finally:
        c.close()

def serialize_signal(row):
    if not row:
        return None
    d = dict(row)
    d["account"] = json.loads(d.pop("account_json"))
    d["orders"] = json.loads(d.pop("orders_json"))
    d["hybrid_strict"] = bool(d["hybrid_strict"])
    return d

def scheduled_job():
    try:
        generate_daily_signal(force=False)
        print("[scheduler] daily signal generated")
    except Exception as e:
        print("[scheduler] error:", repr(e))

def start_scheduler():
    if os.getenv("DISABLE_SCHEDULER", "0") == "1":
        return
    scheduler = BackgroundScheduler(timezone=APP_TZ)
    scheduler.add_job(
        scheduled_job,
        "cron",
        hour=8,
        minute=0,
        id="daily_signal",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

initialize_database(DB_PATH)
start_scheduler()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=True)
