
const $=s=>document.querySelector(s), $$=s=>document.querySelectorAll(s);
const money=n=>n==null?'—':'$'+Number(n).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
const pct=n=>n==null?'—':(n*100).toFixed(2)+'%';
let currentState=null;

$$('.tab').forEach(b=>b.addEventListener('click',()=>{
  $$('.tab').forEach(x=>x.classList.remove('active')); b.classList.add('active');
  $$('.tabPanel').forEach(x=>x.classList.remove('active')); $('#'+b.dataset.tab).classList.add('active');
}));

$('#side').addEventListener('change',()=>{
  $('#layerField').classList.toggle('hidden',$('#side').value!=='SELL');
  if($('#side').value==='BUY' && $('#orderSlot').value.startsWith('Sell')) $('#orderSlot').value='Buy1';
});
$('#orderSlot').addEventListener('change',()=>{
  if($('#orderSlot').value.startsWith('Sell')){ $('#side').value='SELL'; $('#layerField').classList.remove('hidden'); }
});

async function loadAll(){
  const r=await fetch('/api/state'); const d=await r.json(); currentState=d;
  const s=d.state||{};
  $('#equity').textContent=money(s.equity); $('#cash').textContent=money(s.cash); $('#qty').textContent=(s.qty??0)+'주';
  $('#avg').textContent=money(s.avg_cost); $('#cashRatio').textContent=pct(s.cash_ratio);
  $('#totalPnl').textContent=money(s.total_pnl);
  renderSignal(d.latest_signal);
  renderLayers(d.layers||[],d.last_close);
  renderFills(d.fills||[]);
  await loadSignals();
  $('#tradeDate').value=new Date().toISOString().slice(0,10);
}

function renderSignal(s){
  if(!s){return}
  $('#signalMeta').textContent=`기준일 ${s.market_date} · 생성 ${s.created_at}`;
  $('#sigClose').textContent=money(s.close); $('#sigAdx').textContent=s.adx14==null?'—':Number(s.adx14).toFixed(1);
  $('#sigRet').textContent=pct(s.ret20); $('#signalNote').textContent=s.note||'';
  $('#hybridBadge').textContent='Hybrid Strict '+(s.hybrid_strict?'ON':'OFF');
  $('#hybridBadge').classList.toggle('on',s.hybrid_strict);
  const rows=(s.orders||[]).map(o=>{
    const lp=o.layer_pnl_pct==null?'—':pct(o.layer_pnl_pct);
    const st=o.status||o.rule||'';
    return `<tr><td>${o.kind}</td><td>${o.slot}</td><td>${money(o.target)}</td><td>${o.qty}주</td><td>${o.layer_id?'L'+o.layer_id:'—'}</td><td class="${o.layer_pnl_pct!=null?(o.layer_pnl_pct>=0?'good':'bad'):''}">${lp}</td><td>${st}</td></tr>`;
  }).join('');
  $('#ordersBody').innerHTML=rows||'<tr><td colspan="7" class="empty">주문 없음</td></tr>';
}

function renderLayers(layers,close){
  $('#layerSelect').innerHTML=layers.map(l=>`<option value="${l.id}">L${l.id} · ${l.remaining_qty}주 @ ${money(l.fill_price)}</option>`).join('');
  $('#layersBody').innerHTML=layers.length?layers.map(l=>{
    const pnl=close?close*(1-0.0002)/l.effective_cost-1:null;
    return `<tr><td>L${l.id}</td><td>${l.opened_at}</td><td>${money(l.fill_price)}</td><td>${money(l.effective_cost)}</td><td>${l.remaining_qty}주</td><td class="${pnl!=null?(pnl>=0?'good':'bad'):''}">${pct(pnl)}</td></tr>`;
  }).join(''):'<tr><td colspan="6" class="empty">열린 Layer가 없습니다.</td></tr>';
}

function renderFills(fills){
  $('#fillsBody').innerHTML=fills.length?fills.map(f=>`<tr><td>${f.trade_date}</td><td>${f.side}</td><td>${money(f.price)}</td><td>${f.qty}주</td><td>${f.layer_id?'L'+f.layer_id:'—'}</td><td class="${f.realized_pnl!=null?(f.realized_pnl>=0?'good':'bad'):''}">${f.realized_pnl==null?'—':money(f.realized_pnl)}</td></tr>`).join(''):'<tr><td colspan="6" class="empty">체결 기록이 없습니다.</td></tr>';
}

async function loadSignals(){
  const r=await fetch('/api/signals'); const arr=await r.json();
  $('#signalHistory').innerHTML=arr.length?arr.map(s=>`<div class="historyItem"><b>${s.market_date} · 종가 ${money(s.close)}</b><span>ADX ${s.adx14==null?'—':Number(s.adx14).toFixed(1)} · 20일 ${pct(s.ret20)} · Hybrid ${s.hybrid_strict?'ON':'OFF'} · 주문 ${(s.orders||[]).length}개</span></div>`).join(''):'<p>중계표 기록이 없습니다.</p>';
}

$('#genBtn').addEventListener('click',async()=>{
  $('#genBtn').disabled=true; $('#genBtn').textContent='생성 중...';
  try{
    const r=await fetch('/api/signals/generate',{method:'POST'}); const d=await r.json();
    if(!r.ok) throw new Error(d.error||'생성 실패');
    await loadAll();
  }catch(e){alert(e.message)}finally{$('#genBtn').disabled=false;$('#genBtn').textContent='중계표 지금 생성'}
});

$('#fillForm').addEventListener('submit',async e=>{
  e.preventDefault();
  const payload={
    side:$('#side').value, trade_date:$('#tradeDate').value,
    price:Number($('#fillPrice').value), qty:Number($('#fillQty').value),
    order_slot:$('#orderSlot').value, note:$('#fillNote').value
  };
  if(payload.side==='SELL') payload.layer_id=Number($('#layerSelect').value);
  const r=await fetch('/api/fills',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const d=await r.json();
  if(!r.ok){$('#formMsg').textContent=d.error||'저장 실패';return}
  $('#formMsg').textContent='체결 기록 완료';
  $('#fillPrice').value=''; $('#fillQty').value=''; $('#fillNote').value='';
  await loadAll();
});

loadAll().catch(e=>{console.error(e);});
