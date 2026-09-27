import os
import pandas as pd

FALLBACK_PATH=os.path.join(os.path.dirname(__file__),"SOXL_fallback.csv")

def _wilder_adx(df,n=14):
    h=df["High"].astype(float); l=df["Low"].astype(float); c=df["Close"].astype(float)
    up=h.diff(); dn=-l.diff()
    pdm=up.where((up>dn)&(up>0),0.0)
    mdm=dn.where((dn>up)&(dn>0),0.0)
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    pdi=100*pdm.ewm(alpha=1/n,adjust=False,min_periods=n).mean()/atr
    mdi=100*mdm.ewm(alpha=1/n,adjust=False,min_periods=n).mean()/atr
    dx=100*(pdi-mdi).abs()/(pdi+mdi)
    return dx.ewm(alpha=1/n,adjust=False,min_periods=n).mean()

def _finish(df):
    df=df.copy()
    df["Date"]=pd.to_datetime(df["Date"])
    df=df.sort_values("Date").dropna(subset=["High","Low","Close"]).reset_index(drop=True)
    df["ADX14"]=_wilder_adx(df,14)
    df["RET20"]=df["Close"].astype(float).pct_change(20)
    return df

def fetch_soxl_bars():
    try:
        import yfinance as yf
        df=yf.download("SOXL",period="6mo",interval="1d",
                       auto_adjust=False,progress=False,threads=False,timeout=12)
        if df is not None and len(df)>=30:
            if isinstance(df.columns,pd.MultiIndex):
                df.columns=[c[0] for c in df.columns]
            df=df.reset_index()
            if "Date" not in df.columns:
                df.rename(columns={df.columns[0]:"Date"},inplace=True)
            return _finish(df)
    except Exception:
        pass

    # Render/Yahoo 연결 실패 시 이 파일을 사용합니다.
    return _finish(pd.read_csv(FALLBACK_PATH))
