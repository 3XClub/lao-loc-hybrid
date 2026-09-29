
import os
import time
import pandas as pd
import requests

FALLBACK_PATH = os.path.join(os.path.dirname(__file__), "data", "SOXL_fallback.csv")
UA = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142 Safari/537.36"}

def _wilder_adx(df, n=14):
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)
    up = high.diff()
    down = -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    tr = pd.concat(
        [high-low, (high-close.shift()).abs(), (low-close.shift()).abs()],
        axis=1
    ).max(axis=1)
    atr = tr.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    plus_sm = plus_dm.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    minus_sm = minus_dm.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    plus_di = 100 * plus_sm / atr
    minus_di = 100 * minus_sm / atr
    dx = 100 * (plus_di-minus_di).abs() / (plus_di+minus_di)
    return dx.ewm(alpha=1/n, adjust=False, min_periods=n).mean()

def _normalize(df):
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    for c in ["Open","High","Low","Close","Adj Close","Volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "Adj Close" not in df.columns:
        df["Adj Close"] = df["Close"]
    keep = [c for c in ["Date","Open","High","Low","Close","Adj Close","Volume"] if c in df.columns]
    return df[keep]

def _yahoo_chart():
    # Yahoo's direct chart JSON endpoint does not require cookie/crumb handling.
    now = int(time.time())
    start = now - 220 * 24 * 60 * 60
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/SOXL"
        f"?period1={start}&period2={now+86400}&interval=1d"
        "&events=history&includeAdjustedClose=true"
    )
    r = requests.get(url, headers=UA, timeout=12)
    r.raise_for_status()
    obj = r.json()
    result = obj["chart"]["result"][0]
    ts = result.get("timestamp") or []
    quote = result["indicators"]["quote"][0]
    adj = (result["indicators"].get("adjclose") or [{}])[0].get("adjclose", [])
    rows = []
    for i, t in enumerate(ts):
        try:
            rows.append({
                "Date": pd.to_datetime(t, unit="s", utc=True).tz_convert("America/New_York").tz_localize(None),
                "Open": quote["open"][i],
                "High": quote["high"][i],
                "Low": quote["low"][i],
                "Close": quote["close"][i],
                "Adj Close": adj[i] if i < len(adj) else quote["close"][i],
                "Volume": quote["volume"][i],
            })
        except Exception:
            continue
    df = pd.DataFrame(rows)
    if len(df) < 20:
        raise RuntimeError("Yahoo chart returned too few rows")
    return _normalize(df)

def _yfinance():
    import yfinance as yf
    df = yf.download(
        "SOXL",
        period="6mo",
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
        timeout=12
    )
    if df is None or len(df) < 20:
        raise RuntimeError("yfinance returned too few rows")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.reset_index()
    if "Date" not in df.columns:
        df.rename(columns={df.columns[0]:"Date"}, inplace=True)
    return _normalize(df)

def fetch_soxl_bars():
    fallback = _normalize(pd.read_csv(FALLBACK_PATH))
    live = None
    source = "bundled_fallback"

    # 1) Prefer direct Yahoo chart JSON.
    try:
        live = _yahoo_chart()
        source = "yahoo_chart"
    except Exception:
        # 2) Fall back to yfinance.
        try:
            live = _yfinance()
            source = "yfinance"
        except Exception:
            live = None

    if live is not None and len(live):
        merged = pd.concat([fallback, live], ignore_index=True)
        merged = merged.drop_duplicates("Date", keep="last")
    else:
        merged = fallback

    merged = merged.sort_values("Date").dropna(subset=["High","Low","Close"]).reset_index(drop=True)
    merged["ADX14"] = _wilder_adx(merged, 14)
    merged["RET20"] = merged["Close"].astype(float).pct_change(20)
    merged.attrs["source"] = source
    return merged
