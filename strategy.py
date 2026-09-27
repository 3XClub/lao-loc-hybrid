
import json
import math
import sqlite3
from datetime import datetime

FEE_DEFAULT = 0.0002

def get_db(path):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c

def initialize_database(path):
    c = get_db(path)
    try:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cash_ledger(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            amount REAL NOT NULL,
            reason TEXT NOT NULL,
            fill_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS layers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opened_at TEXT NOT NULL,
            fill_price REAL NOT NULL,
            effective_cost REAL NOT NULL,
            original_qty INTEGER NOT NULL,
            remaining_qty INTEGER NOT NULL,
            source_order TEXT,
            closed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS fills(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date TEXT NOT NULL,
            side TEXT NOT NULL,
            price REAL NOT NULL,
            qty INTEGER NOT NULL,
            layer_id INTEGER,
            order_slot TEXT,
            fee REAL NOT NULL,
            cash_effect REAL NOT NULL,
            realized_pnl REAL,
            note TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS signals(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            close REAL NOT NULL,
            adx14 REAL,
            ret20 REAL,
            hybrid_strict INTEGER NOT NULL,
            account_json TEXT NOT NULL,
            orders_json TEXT NOT NULL,
            note TEXT
        );
        """)
        defaults = {
            "initial_budget": "10000",
            "line_count": "13",
            "fee": str(FEE_DEFAULT),
        }
        for k,v in defaults.items():
            c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k,v))
        if c.execute("SELECT COUNT(*) n FROM cash_ledger").fetchone()["n"] == 0:
            initial = float(c.execute("SELECT value FROM settings WHERE key='initial_budget'").fetchone()["value"])
            c.execute("INSERT INTO cash_ledger(ts, amount, reason) VALUES(datetime('now'), ?, 'INITIAL')", (initial,))
        c.commit()
    finally:
        c.close()

def setting(c, key, default=None):
    r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default

def cash_balance(c):
    return float(c.execute("SELECT COALESCE(SUM(amount),0) s FROM cash_ledger").fetchone()["s"])

def open_layers(c):
    return [dict(r) for r in c.execute(
        "SELECT * FROM layers WHERE remaining_qty>0 ORDER BY id ASC"
    ).fetchall()]

def account_state(c, mark_price=None):
    layers = open_layers(c)
    cash = cash_balance(c)
    qty = sum(int(x["remaining_qty"]) for x in layers)
    total_cost = sum(float(x["effective_cost"]) * int(x["remaining_qty"]) for x in layers)
    avg = total_cost / qty if qty else None
    market_value = qty * mark_price if mark_price is not None else None
    equity = cash + market_value if market_value is not None else None
    initial = float(setting(c, "initial_budget", "10000"))
    unrealized = (market_value - total_cost) if market_value is not None else None
    total_pnl = (equity - initial) if equity is not None else None
    return {
        "cash": cash,
        "qty": qty,
        "avg_cost": avg,
        "total_cost": total_cost,
        "market_value": market_value,
        "equity": equity,
        "unrealized_pnl": unrealized,
        "total_pnl": total_pnl,
        "cash_ratio": (cash/equity if equity and equity != 0 else None),
        "layer_count": len(layers),
        "initial_budget": initial,
    }

def _last_fill(c):
    r = c.execute("SELECT * FROM fills ORDER BY id DESC LIMIT 1").fetchone()
    return dict(r) if r else None

def _round_price(x):
    return round(float(x) + 1e-10, 2)

def _buy1_held(close, anchor, last_side):
    if not anchor or anchor <= 0:
        return _round_price(close * 0.993)
    r = close / anchor
    if last_side == "BUY":
        if r < 0.90: f = 0.980
        elif r < 0.95: f = 0.988
        elif r < 1.00: f = 0.992
        else: f = 0.995
    elif last_side == "SELL":
        if r < 0.95: f = 0.983
        elif r < 1.00: f = 0.991
        else: f = 0.995
    else:
        f = 0.993
    return _round_price(anchor * f)

def build_signal(c, bars, state):
    close = float(bars.iloc[-1]["Close"])
    market_date = str(bars.iloc[-1]["Date"].date())
    adx = float(bars.iloc[-1]["ADX14"]) if bars.iloc[-1]["ADX14"] == bars.iloc[-1]["ADX14"] else None
    ret20 = float(bars.iloc[-1]["RET20"]) if bars.iloc[-1]["RET20"] == bars.iloc[-1]["RET20"] else None
    hybrid = bool(adx is not None and ret20 is not None and adx >= 25 and ret20 <= -0.20)

    initial = float(setting(c, "initial_budget", "10000"))
    line_count = int(float(setting(c, "line_count", "13")))
    line_budget = initial / line_count
    fee = float(setting(c, "fee", str(FEE_DEFAULT)))
    layers = open_layers(c)
    last = _last_fill(c)

    if not layers:
        b1 = _round_price(close * 1.07 - 0.04)
        b2 = _round_price(close * 0.999)
    else:
        recent = layers[-1]
        anchor = float(recent["fill_price"])
        b1 = _buy1_held(close, anchor, last["side"] if last else None)
        b2 = _round_price(min(close * 0.999, anchor - 0.02))

    b1q = max(1, math.floor(line_budget / b1))
    b2q = max(1, math.floor(line_budget / b2))
    orders = [
        {"kind":"BUY","slot":"Buy1","target":b1,"qty":b1q,
         "rule":"LOC: 종가 ≤ Target이면 종가 체결"},
        {"kind":"BUY","slot":"Buy2","target":b2,"qty":b2q,
         "rule":"LOC: 종가 ≤ Target이면 종가 체결"},
    ]

    # Sell candidates based on current layer ledger.
    # Recent layer first is the user's live decision rule.
    recent_layers = list(reversed(layers))
    slot_names = ["Sell2","Sell1","Sell3"]
    for i, layer in enumerate(recent_layers[:3]):
        slot = slot_names[i]
        effective = float(layer["effective_cost"])
        target = _round_price(float(layer["fill_price"]) * 1.0015)
        profitable_now = close * (1-fee) > effective
        active = profitable_now or hybrid
        orders.append({
            "kind":"SELL",
            "slot":slot,
            "target":target,
            "qty":int(layer["remaining_qty"]),
            "layer_id":int(layer["id"]),
            "layer_price":float(layer["fill_price"]),
            "effective_cost":effective,
            "layer_pnl_pct": close*(1-fee)/effective - 1,
            "active":active,
            "status":"정상 익절" if profitable_now else ("Hybrid Strict 손실 Exit 허용" if hybrid else "손실 Layer 보류"),
            "rule":"LOC: 종가 ≥ Target이면 종가 체결; 손실 Layer는 Hybrid Strict일 때만 허용"
        })

    note = (
        "Layer별 수익 실현 + 현금 재순환. "
        + ("Hybrid Strict ON: 손실 Layer Exit 허용." if hybrid else "Hybrid Strict OFF: 손실 Layer 보류.")
    )
    return {
        "market_date":market_date,
        "close":close,
        "adx14":adx,
        "ret20":ret20,
        "hybrid_strict":hybrid,
        "account":state,
        "orders":orders,
        "note":note,
    }

def apply_fill(c, payload):
    side = str(payload.get("side","")).upper().strip()
    if side not in ("BUY","SELL"):
        raise ValueError("side는 BUY 또는 SELL이어야 합니다.")
    try:
        price = float(payload.get("price"))
        qty = int(payload.get("qty"))
    except Exception:
        raise ValueError("체결가와 수량을 확인해 주세요.")
    if price <= 0 or qty <= 0:
        raise ValueError("체결가와 수량은 0보다 커야 합니다.")
    trade_date = str(payload.get("trade_date") or datetime.now().date())
    order_slot = str(payload.get("order_slot") or "")
    note = str(payload.get("note") or "")
    fee_rate = float(setting(c, "fee", str(FEE_DEFAULT)))
    created_at = datetime.now().isoformat(timespec="seconds")

    if side == "BUY":
        gross = price * qty
        fee = gross * fee_rate
        total = gross + fee
        if cash_balance(c) + 1e-8 < total:
            raise ValueError("현금이 부족합니다.")
        cur = c.execute(
            """INSERT INTO fills(trade_date,side,price,qty,layer_id,order_slot,fee,cash_effect,realized_pnl,note,created_at)
               VALUES(?,?,?,?,NULL,?,?,?,?,?,?)""",
            (trade_date, side, price, qty, order_slot, fee, -total, None, note, created_at)
        )
        fill_id = cur.lastrowid
        cur2 = c.execute(
            """INSERT INTO layers(opened_at,fill_price,effective_cost,original_qty,remaining_qty,source_order)
               VALUES(?,?,?,?,?,?)""",
            (trade_date, price, price*(1+fee_rate), qty, qty, order_slot)
        )
        layer_id = cur2.lastrowid
        c.execute("UPDATE fills SET layer_id=? WHERE id=?", (layer_id, fill_id))
        c.execute(
            "INSERT INTO cash_ledger(ts,amount,reason,fill_id) VALUES(?,?,?,?)",
            (created_at, -total, "BUY", fill_id)
        )
        return {"ok":True,"fill_id":fill_id,"layer_id":layer_id,"cash_effect":-total}

    layer_id = payload.get("layer_id")
    if layer_id is None:
        raise ValueError("매도할 Layer를 선택해 주세요.")
    layer = c.execute("SELECT * FROM layers WHERE id=?", (int(layer_id),)).fetchone()
    if not layer or int(layer["remaining_qty"]) <= 0:
        raise ValueError("유효한 Layer가 아닙니다.")
    if qty > int(layer["remaining_qty"]):
        raise ValueError("매도수량이 Layer 잔여수량보다 많습니다.")
    gross = price * qty
    fee = gross * fee_rate
    proceeds = gross - fee
    cost_basis = float(layer["effective_cost"]) * qty
    realized = proceeds - cost_basis
    cur = c.execute(
        """INSERT INTO fills(trade_date,side,price,qty,layer_id,order_slot,fee,cash_effect,realized_pnl,note,created_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (trade_date, side, price, qty, int(layer_id), order_slot, fee, proceeds, realized, note, created_at)
    )
    fill_id = cur.lastrowid
    remaining = int(layer["remaining_qty"]) - qty
    c.execute(
        "UPDATE layers SET remaining_qty=?, closed_at=CASE WHEN ?=0 THEN ? ELSE closed_at END WHERE id=?",
        (remaining, remaining, trade_date, int(layer_id))
    )
    c.execute(
        "INSERT INTO cash_ledger(ts,amount,reason,fill_id) VALUES(?,?,?,?)",
        (created_at, proceeds, "SELL", fill_id)
    )
    return {"ok":True,"fill_id":fill_id,"layer_id":int(layer_id),"cash_effect":proceeds,"realized_pnl":realized}
