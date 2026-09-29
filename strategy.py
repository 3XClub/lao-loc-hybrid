import math
FEE=0.0002
def rp(x): return round(float(x)+1e-10,2)

def buy1_held(close,anchor,last_side):
    if not anchor or anchor<=0: return rp(close*0.993)
    r=close/anchor
    if last_side=="BUY":
        f=0.980 if r<0.90 else 0.988 if r<0.95 else 0.992 if r<1.00 else 0.995
    elif last_side=="SELL":
        f=0.983 if r<0.95 else 0.991 if r<1.00 else 0.995
    else: f=0.993
    return rp(anchor*f)

def account_from_client(payload,mark):
    initial=float(payload.get("initial_budget") or 10000)
    cash=float(payload.get("cash") if payload.get("cash") is not None else initial)
    layers=payload.get("layers") or []
    qty=sum(int(l.get("remaining_qty",0)) for l in layers)
    cost=sum(float(l.get("effective_cost",l.get("fill_price",0)))*int(l.get("remaining_qty",0)) for l in layers)
    avg=cost/qty if qty else None; mv=qty*mark; eq=cash+mv
    return {"initial_budget":initial,"cash":cash,"qty":qty,"avg_cost":avg,"total_cost":cost,
            "market_value":mv,"equity":eq,"unrealized_pnl":mv-cost,"total_pnl":eq-initial,
            "cash_ratio":cash/eq if eq else None,"layer_count":len([l for l in layers if int(l.get("remaining_qty",0))>0])}

def build_signal_from_client(bars,payload):
    row=bars.iloc[-1]; close=float(row["Close"]); market_date=str(row["Date"].date())
    adx=None if row["ADX14"]!=row["ADX14"] else float(row["ADX14"])
    ret20=None if row["RET20"]!=row["RET20"] else float(row["RET20"])
    hybrid=bool(adx is not None and ret20 is not None and adx>=25 and ret20<=-0.20)
    initial=float(payload.get("initial_budget") or 10000); line_count=int(payload.get("line_count") or 13)
    line_budget=initial/line_count
    layers=[l for l in (payload.get("layers") or []) if int(l.get("remaining_qty",0))>0]
    last_fill=payload.get("last_fill") or {}
    account=account_from_client(payload,close)

    if not layers:
        b1=rp(close*1.07-0.04); b2=rp(close*0.999)
    else:
        recent=sorted(layers,key=lambda x:int(x.get("id",0)))[-1]
        anchor=float(recent["fill_price"])
        b1=buy1_held(close,anchor,str(last_fill.get("side","")).upper() or None)
        b2=rp(min(close*0.999,anchor-0.02))
    orders=[
        {"kind":"BUY","slot":"Buy1","target":b1,"qty":max(1,math.floor(line_budget/b1)),"status":"활성"},
        {"kind":"BUY","slot":"Buy2","target":b2,"qty":max(1,math.floor(line_budget/b2)),"status":"활성"},
    ]
    recent_layers=sorted(layers,key=lambda x:int(x.get("id",0)),reverse=True)
    for i,l in enumerate(recent_layers[:3]):
        eff=float(l.get("effective_cost",float(l["fill_price"])*(1+FEE)))
        target=rp(float(l["fill_price"])*1.0015)
        current_pnl=close*(1-FEE)/eff-1
        target_pnl=target*(1-FEE)/eff-1
        target_profitable=target_pnl>0
        orders.append({"kind":"SELL","slot":["Sell2","Sell1","Sell3"][i],"target":target,
                       "qty":int(l["remaining_qty"]),"layer_id":int(l["id"]),"layer_price":float(l["fill_price"]),
                       "current_layer_pnl_pct":current_pnl,"target_pnl_pct":target_pnl,
                       "layer_pnl_pct":target_pnl,"active":target_profitable or hybrid,
                       "status":"정상 익절 주문" if target_profitable else ("Hybrid Strict 손실 Exit 허용" if hybrid else "손실 Layer 보류")})
    return {"market_date":market_date,"close":close,"adx14":adx,"ret20":ret20,"hybrid_strict":hybrid,
            "account":account,"orders":orders,
            "note":"Layer별 수익 실현 + 현금 재순환. "+("Hybrid Strict ON" if hybrid else "Hybrid Strict OFF")}
