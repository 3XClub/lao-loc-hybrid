const KEY='laoLocHybridStateV05',OLD_KEY='laoLocHybridStateV04',FEE=0.0002,$=s=>document.querySelector(s),$$=s=>document.querySelectorAll(s);const money=n=>n==null?'—':'$'+Number(n).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2}),pct=n=>n==null?'—':(n*100).toFixed(2)+'%';function def(){return{initial_budget:10000,cash:10000,nextLayerId:1,layers:[],fills:[],signals:[],last_close:null}}function load(){
  try{
    const raw=localStorage.getItem(KEY)||localStorage.getItem(OLD_KEY)||'{}';
    return {...def(),...JSON.parse(raw)};
  }catch(e){return def()}
}let state=load();function save(){localStorage.setItem(KEY,JSON.stringify(state))}
function lineBudget(){return state.initial_budget/13}
function updateBudgetUI(){
  $('#budgetInput').value=Number(state.initial_budget||10000).toFixed(0);
  $('#lineBudget').textContent=money(lineBudget());
}function openLayers(){return state.layers.filter(l=>l.remaining_qty>0)}function account(mark=state.last_close){const ls=openLayers(),qty=ls.reduce((s,l)=>s+l.remaining_qty,0),cost=ls.reduce((s,l)=>s+l.effective_cost*l.remaining_qty,0),mv=mark==null?null:qty*mark,eq=mv==null?null:state.cash+mv;return{qty,cost,avg:qty?cost/qty:null,mv,eq,cash_ratio:eq?state.cash/eq:null,total_pnl:eq==null?null:eq-state.initial_budget}}function lastFill(){return state.fills.length?state.fills[state.fills.length-1]:null}$$('.tab').forEach(b=>b.addEventListener('click',()=>{$$('.tab').forEach(x=>x.classList.remove('active'));b.classList.add('active');$$('.tabPanel').forEach(x=>x.classList.remove('active'));$('#'+b.dataset.tab).classList.add('active')}));$('#side').addEventListener('change',()=>$('#layerField').classList.toggle('hidden',$('#side').value!=='SELL'));function renderAll(){updateBudgetUI();const a=account();$('#equity').textContent=money(a.eq);$('#cash').textContent=money(state.cash);$('#qty').textContent=a.qty+'주';$('#avg').textContent=money(a.avg);$('#cashRatio').textContent=pct(a.cash_ratio);$('#totalPnl').textContent=money(a.total_pnl);renderLayers();renderFills();renderHistory()}function renderLayers(){const ls=openLayers();$('#layerSelect').innerHTML=ls.slice().reverse().map(l=>`<option value="${l.id}">L${l.id} · ${l.remaining_qty}주 @ ${money(l.fill_price)}</option>`).join('');$('#layersBody').innerHTML=ls.length?ls.slice().reverse().map(l=>{const p=state.last_close==null?null:state.last_close*(1-FEE)/l.effective_cost-1;return`<tr><td>L${l.id}</td><td>${l.opened_at}</td><td>${money(l.fill_price)}</td><td>${money(l.effective_cost)}</td><td>${l.remaining_qty}주</td><td class="${p!=null?(p>=0?'good':'bad'):''}">${pct(p)}</td></tr>`}).join(''):'<tr><td colspan="6" class="empty">열린 Layer가 없습니다.</td></tr>'}function renderFills(){const arr=state.fills.slice().reverse();$('#fillsBody').innerHTML=arr.length?arr.map(f=>`<tr><td>${f.trade_date}</td><td>${f.side}</td><td>${money(f.price)}</td><td>${f.qty}주</td><td>${f.layer_id?'L'+f.layer_id:'—'}</td><td class="${f.realized_pnl!=null?(f.realized_pnl>=0?'good':'bad'):''}">${f.realized_pnl==null?'—':money(f.realized_pnl)}</td></tr>`).join(''):'<tr><td colspan="6" class="empty">체결 기록이 없습니다.</td></tr>'}function renderHistory(){const arr=state.signals.slice().reverse();$('#signalHistory').innerHTML=arr.length?arr.map(s=>`<div class="historyItem"><b>${s.market_date} · 종가 ${money(s.close)}</b><span>ADX ${s.adx14==null?'—':Number(s.adx14).toFixed(1)} · 20일 ${pct(s.ret20)} · Hybrid ${s.hybrid_strict?'ON':'OFF'} · 주문 ${s.orders.length}개</span></div>`).join(''):'<p>중계표 기록이 없습니다.</p>'}function renderSignal(s){$('#signalMeta').textContent=`기준일 ${s.market_date} · ${s.fallback_used?'내장 백업 시세':'실시간 시세'} · 새로고침 시 자동 계산`;$('#sigClose').textContent=money(s.close);$('#sigAdx').textContent=s.adx14==null?'—':Number(s.adx14).toFixed(1);$('#sigRet').textContent=pct(s.ret20);$('#hybridBadge').textContent='Hybrid Strict '+(s.hybrid_strict?'ON':'OFF');$('#hybridBadge').classList.toggle('on',s.hybrid_strict);$('#signalNote').textContent=s.note||'';$('#ordersBody').innerHTML=s.orders.map(o=>`<tr><td>${o.kind}</td><td>${o.slot}</td><td>${money(o.target)}</td><td>${o.qty}주</td><td>${o.layer_id?'L'+o.layer_id:'—'}</td><td class="${o.layer_pnl_pct!=null?(o.layer_pnl_pct>=0?'good':'bad'):''}">${o.layer_pnl_pct==null?'—':pct(o.layer_pnl_pct)}</td><td>${o.status||''}</td></tr>`).join('')}async function refreshSignal(){$('#wakeMsg').classList.remove('hidden');$('#refreshBtn').disabled=true;$('#refreshBtn').textContent='불러오는 중...';try{const body={initial_budget:state.initial_budget,cash:state.cash,line_count:13,layers:openLayers(),last_fill:lastFill()};const r=await fetch('/api/signal',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
const raw=await r.text();
let d;
try{d=JSON.parse(raw)}catch(err){throw new Error(`서버 응답 오류 (${r.status}). Render 최신 배포를 확인해 주세요.`)}
if(!r.ok)throw new Error(d.error||`중계표 생성 실패 (${r.status})`);state.last_close=d.close;const idx=state.signals.findIndex(x=>x.market_date===d.market_date);if(idx>=0)state.signals[idx]=d;else state.signals.push(d);if(state.signals.length>365)state.signals=state.signals.slice(-365);save();renderSignal(d);renderAll()}catch(e){$('#ordersBody').innerHTML=`<tr><td colspan="7" class="empty">${e.message}</td></tr>`}finally{$('#wakeMsg').classList.add('hidden');$('#refreshBtn').disabled=false;$('#refreshBtn').textContent='최신 중계표 새로고침'}}$('#refreshBtn').addEventListener('click',refreshSignal);$('#fillForm').addEventListener('submit',async e=>{e.preventDefault();const side=$('#side').value,date=$('#tradeDate').value,price=Number($('#fillPrice').value),qty=Math.floor(Number($('#fillQty').value)),slot=$('#orderSlot').value,note=$('#fillNote').value;if(!date||!Number.isFinite(price)||price<=0||!Number.isFinite(qty)||qty<1){$('#formMsg').textContent='입력값을 확인해 주세요.';return}if(side==='BUY'){const fee=price*qty*FEE,total=price*qty+fee;if(total>state.cash+1e-8){$('#formMsg').textContent='현금이 부족합니다.';return}const id=state.nextLayerId++;state.cash-=total;state.layers.push({id,opened_at:date,fill_price:price,effective_cost:price*(1+FEE),original_qty:qty,remaining_qty:qty,source_order:slot});state.fills.push({trade_date:date,side,price,qty,layer_id:id,order_slot:slot,fee,realized_pnl:null,note})}else{const id=Number($('#layerSelect').value),l=state.layers.find(x=>x.id===id&&x.remaining_qty>0);if(!l){$('#formMsg').textContent='매도 Layer를 선택해 주세요.';return}if(qty>l.remaining_qty){$('#formMsg').textContent='Layer 잔여수량보다 많습니다.';return}const fee=price*qty*FEE,proceeds=price*qty-fee,realized=proceeds-l.effective_cost*qty;state.cash+=proceeds;l.remaining_qty-=qty;state.fills.push({trade_date:date,side,price,qty,layer_id:id,order_slot:slot,fee,realized_pnl:realized,note})}save();$('#formMsg').textContent='체결 기록 완료';$('#fillPrice').value='';$('#fillQty').value='';$('#fillNote').value='';renderAll();await refreshSignal()});
$('#applyBudgetBtn').addEventListener('click',async()=>{
  const next=Number($('#budgetInput').value);
  if(!Number.isFinite(next)||next<100){
    alert('시작금은 $100 이상으로 입력해 주세요.');
    return;
  }
  const old=Number(state.initial_budget||10000);
  if(Math.abs(next-old)<0.01){
    updateBudgetUI();
    return;
  }

  const hasTrades=state.fills.length>0 || openLayers().length>0;
  if(!hasTrades){
    state.initial_budget=next;
    state.cash=next;
  }else{
    const delta=next-old;
    const msg = delta>=0
      ? `기존 거래기록이 있습니다.\n\n시작금을 ${money(old)} → ${money(next)}로 바꾸면 차액 ${money(delta)}를 추가 입금한 것으로 처리하고, 이후 매수수량은 새 시작금 기준으로 계산합니다.\n\n적용할까요?`
      : `기존 거래기록이 있습니다.\n\n시작금을 ${money(old)} → ${money(next)}로 바꾸면 차액 ${money(Math.abs(delta))}를 출금한 것으로 처리합니다.\n현재 현금이 부족하면 변경할 수 없습니다.\n\n적용할까요?`;
    if(!confirm(msg)){updateBudgetUI();return;}
    if(delta<0 && state.cash+delta<0){
      alert('출금 처리 후 현금이 음수가 되어 변경할 수 없습니다.');
      updateBudgetUI();
      return;
    }
    state.initial_budget=next;
    state.cash+=delta;
    state.fills.push({
      trade_date:new Date().toISOString().slice(0,10),
      side:delta>=0?'DEPOSIT':'WITHDRAW',
      price:Math.abs(delta),
      qty:1,
      layer_id:null,
      order_slot:'CAPITAL',
      fee:0,
      realized_pnl:null,
      note:`운용 시작금 변경 ${money(old)} → ${money(next)}`
    });
  }
  save();
  renderAll();
  await refreshSignal();
});

$('#exportBtn').addEventListener('click',()=>{const blob=new Blob([JSON.stringify(state,null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='lao-loc-backup-'+new Date().toISOString().slice(0,10)+'.json';a.click();URL.revokeObjectURL(a.href)});$('#importFile').addEventListener('change',e=>{const f=e.target.files[0];if(!f)return;const rd=new FileReader();rd.onload=()=>{try{state={...def(),...JSON.parse(rd.result)};save();renderAll();refreshSignal()}catch(err){alert('백업 파일을 읽을 수 없습니다.')}};rd.readAsText(f)});$('#tradeDate').value=new Date().toISOString().slice(0,10);renderAll();refreshSignal();