import os
import pandas as pd

def _wilder_adx(df, n=14):
    high=df["High"].astype(float); low=df["Low"].astype(float); close=df["Close"].astype(float)
    up=high.diff(); down=-low.diff()
    plus_dm=up.where((up>down)&(up>0),0.0)
    minus_dm=down.where((down>up)&(down>0),0.0)
    tr=pd.concat([high-low,(high-close.shift()).abs(),(low-close.shift()).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    plus_sm=plus_dm.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    minus_sm=minus_dm.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    plus_di=100*plus_sm/atr; minus_di=100*minus_sm/atr
    dx=100*(plus_di-minus_di).abs()/(plus_di+minus_di)
    return dx.ewm(alpha=1/n,adjust=False,min_periods=n).mean()

def fetch_soxl_bars():
    csv_path=os.getenv("SOXL_CSV_PATH")
    if csv_path and os.path.exists(csv_path):
        df=pd.read_csv(csv_path); df["Date"]=pd.to_datetime(df["Date"])
    else:
        import yfinance as yf
        df=yf.download("SOXL",period="6mo",interval="1d",auto_adjust=False,progress=False,threads=False)
        if df is None or len(df)==0:
            raise RuntimeError("SOXL 시세를 불러오지 못했습니다. 잠시 후 새로고침해 주세요.")
        if isinstance(df.columns,pd.MultiIndex):
            df.columns=[c[0] for c in df.columns]
        df=df.reset_index()
        if "Date" not in df.columns:
            df.rename(columns={df.columns[0]:"Date"},inplace=True)
        df["Date"]=pd.to_datetime(df["Date"])
    df=df.sort_values("Date").dropna(subset=["High","Low","Close"]).reset_index(drop=True)
    df["ADX14"]=_wilder_adx(df,14)
    df["RET20"]=df["Close"].astype(float).pct_change(20)
    return df
