
from flask import Flask, render_template, request, jsonify
from market import fetch_soxl_bars
from strategy import build_signal_from_client
import os

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

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

@app.get("/api/health")
def health():
    return jsonify({"ok":True})

@app.errorhandler(Exception)
def unhandled(e):
    app.logger.exception("unhandled")
    return jsonify({"error":str(e), "type":type(e).__name__}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT","8000")), debug=True)
