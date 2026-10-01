const thaiStocks = [
  ['PTT','ปตท.','พลังงาน'],['AOT','ท่าอากาศยานไทย','ขนส่ง'],['CPALL','ซีพี ออลล์','ค้าปลีก'],['DELTA','เดลต้า อีเลคโทรนิคส์','เทคโนโลยี'],['ADVANC','แอดวานซ์ อินโฟร์ฯ','สื่อสาร'],['GULF','กัลฟ์ เอ็นเนอร์จีฯ','พลังงาน'],['KBANK','ธนาคารกสิกรไทย','ธนาคาร'],['SCB','เอสซีบี เอกซ์','ธนาคาร'],['BDMS','กรุงเทพดุสิตเวชการ','การแพทย์'],['TRUE','ทรู คอร์ปอเรชั่น','สื่อสาร'],['CRC','เซ็นทรัล รีเทล','ค้าปลีก'],['PTTEP','ปตท.สำรวจและผลิต','พลังงาน'],['BBL','ธนาคารกรุงเทพ','ธนาคาร'],['KTB','ธนาคารกรุงไทย','ธนาคาร'],['OR','ปตท. น้ำมันและการค้าปลีก','พลังงาน']
];
const usStocks = [
  ['NVDA','NVIDIA','Technology'],['AAPL','Apple','Technology'],['MSFT','Microsoft','Technology'],['AMZN','Amazon','Consumer'],['GOOGL','Alphabet','Technology'],['META','Meta Platforms','Technology'],['TSLA','Tesla','Automotive'],['AVGO','Broadcom','Technology'],['LLY','Eli Lilly','Healthcare'],['JPM','JPMorgan Chase','Finance'],['V','Visa','Finance'],['WMT','Walmart','Retail'],['COST','Costco','Retail'],['NFLX','Netflix','Media'],['AMD','Advanced Micro Devices','Technology']
];
const cryptoFallback = [
  ['bitcoin','Bitcoin','BTC'],['ethereum','Ethereum','ETH'],['tether','Tether','USDT'],['ripple','XRP','XRP'],['binancecoin','BNB','BNB'],['solana','Solana','SOL'],['usd-coin','USDC','USDC'],['tron','TRON','TRX'],['dogecoin','Dogecoin','DOGE'],['the-open-network','Toncoin','TON'],['cardano','Cardano','ADA'],['bitcoin-cash','Bitcoin Cash','BCH'],['avalanche-2','Avalanche','AVAX'],['chainlink','Chainlink','LINK'],['shiba-inu','Shiba Inu','SHIB']
];
let cryptoAssets = [];
let selectedMarket = 'All';
let historyPending = false;
const stored = (key, fallback) => { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } };
let watchlist = new Set(stored('ms-watchlist', []));
let page = 1;
const pageSize = 25;
const assetKey = a => `${a.market}:${a.symbol}`;
const money = (n, currency='USD') => new Intl.NumberFormat('en-US',{style:'currency',currency,minimumFractionDigits:n<1?4:2,maximumFractionDigits:n<1?6:2}).format(n);
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function makeStock(items, market) { return items.map(([symbol,name,sector])=>({symbol,name,sector,market,price:null,change:null,trend:'รอข้อมูล',signal:'รายการติดตาม'})); }
let stocks=[...makeStock(thaiStocks,'Thai'),...makeStock(usStocks,'US')];
function row(asset) {
  const crypto=asset.market==='Crypto', type=asset.market.toLowerCase(), symbol=asset.symbol;
  const logo=crypto?(symbol.slice(0,1)):asset.market==='Thai'?'฿':symbol.slice(0,1);
  const price=asset.price!==null&&Number.isFinite(asset.price)?money(asset.price,asset.currency||(asset.market==='Thai'?'THB':'USD')):'—';
  const isUp=asset.change!==null&&asset.change>=0;
  const changeText=asset.change===null?'—':`${isUp?'+':''}${asset.change.toFixed(2)}%`;
  const badge=asset.market==='Thai'?'SET':asset.market==='US'?'US STOCK':'CRYPTO';
  const signals=asset.signals||[];
  const rsiText=Number.isFinite(asset.rsi)?asset.rsi.toFixed(1):'—';
  const rsiClass=asset.rsi>=70?'rsi-hot':asset.rsi>=55?'rsi-strong':Number.isFinite(asset.rsi)&&asset.rsi<30?'rsi-low':'';
  const badges=signals.length?signals.map(s=>`<span class="signal-badge ${s.type}" title="${esc(s.description)}">${s.type==='breakout'?'↗ ':s.type==='volume'?'▴ ':s.type==='macd'?'✦ ':s.type==='rsi-high'?'! ':''}${esc(s.label)}</span>`).join(' '):`<span class="signal-empty">${crypto?(asset.historyUnavailable?'ข้อมูลกราฟไม่พร้อม':historyPending?'กำลังวิเคราะห์':'ยังไม่พบสัญญาณ'):asset.hasMarketData?'ยังไม่พบสัญญาณ':'รอข้อมูลตลาด'}</span>`;
  const age=asset.priceDate?Math.floor((Date.now()-Date.parse(asset.priceDate))/86400000):null;
  const metadata=asset.priceDate?`<small class="signal-empty">ปิด ${esc(asset.priceDate)}${age>4?' · ข้อมูลเก่า':''}</small>`:'';
  return `<tr><td><div class="asset-cell"><button class="watch-star" data-watch="${esc(assetKey(asset))}" aria-label="ติดตาม ${esc(symbol)}" aria-pressed="${watchlist.has(assetKey(asset))}">${watchlist.has(assetKey(asset))?'★':'☆'}</button><span class="coin-logo ${type}">${esc(logo)}</span><span><span class="asset-name">${esc(asset.name)}</span><span class="asset-symbol">${esc(symbol)}${asset.sector?` · ${esc(asset.sector)}`:''}</span>${metadata}</span></div></td><td><span class="market-badge ${type}">${badge}</span></td><td class="align-right price">${price}</td><td class="align-right ${asset.change===null?'':isUp?'change-up':'change-down'}">${changeText}</td><td class="align-right ${rsiClass}">${rsiText}</td><td class="signals-cell">${badges}${asset.score?`<span class="score-pill">${asset.score} pts</span>`:''}<small class="signal-empty metric-detail">Volume ${Number.isFinite(asset.volumeRatio)?asset.volumeRatio.toFixed(2)+'×':'—'} · ระยะจาก High20 ${Number.isFinite(asset.breakoutDistance)?asset.breakoutDistance.toFixed(2)+'%':'—'}</small></td></tr>`;
}
function matchesFilters(a){
  const types=[...document.querySelectorAll('[data-condition]:checked')].map(e=>e.value);
  const checks=types.map(t=>(a.signals||[]).some(s=>s.type===t));
  const mode=document.querySelector('#filter-mode').value;
  if(checks.length && !(mode==='and'?checks.every(Boolean):checks.some(Boolean)))return false;
  for(const [id,field,op] of [['rsi-min','rsi','min'],['rsi-max','rsi','max'],['volume-min','volumeRatio','min'],['score-min','score','min']]){
    const raw=document.querySelector('#'+id).value;
    if(raw!==''&&(!Number.isFinite(a[field])||(op==='min'?a[field]<Number(raw):a[field]>Number(raw))))return false;
  }
  return !document.querySelector('#watch-only').checked||watchlist.has(assetKey(a));
}
function render(){
  const q=document.querySelector('#search').value.trim().toLowerCase();
  const signalFilter=document.querySelector('#signal-filter').value;
  const all=[...cryptoAssets,...stocks];
  const filtered=all.filter(a=>(selectedMarket==='All'||a.market===selectedMarket)&&(!q||`${a.symbol} ${a.name} ${a.sector||''}`.toLowerCase().includes(q))&&(signalFilter==='all'||(a.signals||[]).some(s=>s.type===signalFilter))&&matchesFilters(a));
  filtered.sort((a,b)=>(b.score||0)-(a.score||0)||(b.change??-Infinity)-(a.change??-Infinity));
  const pages=Math.max(1,Math.ceil(filtered.length/pageSize));page=Math.min(page,pages);
  const visible=filtered.slice((page-1)*pageSize,page*pageSize);
  document.querySelector('#asset-rows').innerHTML=visible.length?visible.map(row).join(''):'<tr><td colspan="6" class="loading-row">ไม่พบสินทรัพย์ที่ค้นหา</td></tr>';
  document.querySelector('#asset-count').textContent=all.length.toLocaleString('en-US');
  document.querySelector('#up-count').textContent=all.filter(a=>a.change>0).length.toLocaleString('en-US');
  document.querySelector('#showing').textContent=`แสดง ${visible.length} จาก ${filtered.length} รายการ`;
  document.querySelector('#page-label').textContent=`หน้า ${page} / ${pages}`;
  document.querySelector('#page-prev').disabled=page===1;
  document.querySelector('#page-next').disabled=page===pages;
  document.querySelectorAll('[data-market]').forEach(el=>el.classList.toggle('active',el.dataset.market===selectedMarket&&el.classList.contains('tab')));
  document.querySelectorAll('.market-link').forEach(el=>el.classList.toggle('selected',el.dataset.market===selectedMarket));
}
async function loadStockSnapshot(){
  const note=document.querySelector('#data-note');
  try{
    const response=await fetch(`data/stocks.json?updated=${Date.now()}`,{cache:'no-store'});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const snapshot=await response.json();
    if(!Array.isArray(snapshot.assets)||snapshot.assets.length===0)throw new Error('Empty stock snapshot');
    stocks=snapshot.assets.map(asset=>({...asset,hasMarketData:true}));
    const generated=snapshot.generatedAt?new Intl.DateTimeFormat('th-TH',{dateStyle:'medium',timeStyle:'short',timeZone:'Asia/Bangkok'}).format(new Date(snapshot.generatedAt)):'—';
    note.textContent=`หุ้นอัปเดต ${generated} จาก Yahoo Finance · คริปโท CoinGecko/Binance · ข้อมูลหุ้นรายวัน`;
    render();
  }catch(error){
    note.textContent='ยังโหลด snapshot หุ้นไม่สำเร็จ · ข้อมูลหุ้นจะแสดงหลัง workflow อัปเดต';
  }
}
function ema(values,period){
  if(values.length<period)return [];
  const alpha=2/(period+1), out=Array(values.length).fill(null);
  let seed=values.slice(0,period).reduce((sum,v)=>sum+v,0)/period;
  out[period-1]=seed;
  for(let i=period;i<values.length;i++){seed=values[i]*alpha+seed*(1-alpha);out[i]=seed;}
  return out;
}
function rsiSeries(values,period=14){
  const out=Array(values.length).fill(null);
  if(values.length<=period)return out;
  let gain=0,loss=0;
  for(let i=1;i<=period;i++){const delta=values[i]-values[i-1];gain+=Math.max(delta,0);loss+=Math.max(-delta,0);}
  gain/=period;loss/=period;
  const value=()=>gain===0&&loss===0?50:loss===0?100:100-(100/(1+gain/loss));
  out[period]=value();
  for(let i=period+1;i<values.length;i++){const delta=values[i]-values[i-1];gain=(gain*(period-1)+Math.max(delta,0))/period;loss=(loss*(period-1)+Math.max(-delta,0))/period;out[i]=value();}
  return out;
}
function analyzeHistory(asset,candles){
  if(candles.length<27)return;
  const closes=candles.map(c=>c.close), highs=candles.map(c=>c.high), volumes=candles.map(c=>c.volume);
  const i=closes.length-1, rsi=rsiSeries(closes), fast=ema(closes,12), slow=ema(closes,26);
  const macd=closes.map((_,n)=>fast[n]!==null&&slow[n]!==null?fast[n]-slow[n]:null);
  const macdSignalInput=macd.filter(Number.isFinite), macdSignal=ema(macdSignalInput,9);
  const currentMacdSignal=macdSignal.at(-1), previousMacdSignal=macdSignal.at(-2);
  const currentMacd=macd.at(-1), previousMacd=macd.at(-2);
  const ema20=ema(closes,20).at(-1), ema50=ema(closes,50).at(-1);
  const previous20High=Math.max(...highs.slice(-21,-1));
  const averageVolume=volumes.slice(-21,-1).reduce((a,b)=>a+b,0)/20;
  const volumeRatio=averageVolume?volumes[i]/averageVolume:0;
  asset.rsi=rsi[i];asset.volumeRatio=volumeRatio;asset.signals=[];asset.score=0;
  const add=(type,label,description,score)=>{asset.signals.push({type,label,description});asset.score+=score;};
  if(closes[i]>previous20High){add('breakout','20D Breakout',`ราคาปิด ${money(closes[i])} ทะลุจุดสูงสุด 20 วันก่อนหน้า ${money(previous20High)}`,35);}
  if(asset.rsi>=70){add('rsi-high',`RSI ${asset.rsi.toFixed(0)} · ร้อนแรง`,'RSI มากกว่า 70: โมเมนตัมสูง แต่อาจเข้าเขตซื้อมากเกินไป',0);}
  else if(asset.rsi>=55){add('rsi-momentum',`RSI ${asset.rsi.toFixed(0)} · โมเมนตัม`,'RSI อยู่ระหว่าง 55–70 แสดงโมเมนตัมเชิงบวก',15);}
  else if(asset.rsi<30){add('rsi-low',`RSI ${asset.rsi.toFixed(0)} · Oversold`,'RSI ต่ำกว่า 30 อาจอยู่ในเขตขายมากเกินไป ไม่ใช่สัญญาณซื้อโดยลำพัง',10);}
  if(volumeRatio>=1.5){add('volume',`Volume ${volumeRatio.toFixed(1)}×`,'ปริมาณซื้อขายรายวันมากกว่าค่าเฉลี่ย 20 วันอย่างน้อย 1.5 เท่า',20);}
  if(Number.isFinite(currentMacdSignal)&&Number.isFinite(previousMacdSignal)&&previousMacd<=previousMacdSignal&&currentMacd>currentMacdSignal){add('macd','MACD Golden Cross','เส้น MACD ตัดขึ้นเหนือเส้น Signal',20);}
  if(ema20&&ema50&&closes[i]>ema20&&ema20>ema50){add('trend','ขาขึ้น EMA20/50','ราคายืนเหนือ EMA20 และ EMA20 อยู่เหนือ EMA50',10);}
  asset.techPrice=closes[i];asset.historyUnavailable=false;
  asset.breakoutDistance=(closes[i]/previous20High-1)*100;
}
async function loadCryptoHistory(){
  historyPending=true;render();
  let cursor=0;
  const worker=async()=>{while(cursor<cryptoAssets.length){const asset=cryptoAssets[cursor++];try{
    const response=await fetch(`https://api.binance.com/api/v3/klines?symbol=${encodeURIComponent(asset.symbol)}USDT&interval=1d&limit=250`,{signal:AbortSignal.timeout(15000)});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const raw=await response.json();
    const closed=raw.filter(k=>Number(k[6])<Date.now());
    if(closed.length<50)throw new Error('Insufficient closed history');
    asset.priceDate=new Date(Number(closed.at(-1)[0])).toISOString().slice(0,10);
    analyzeHistory(asset,closed.map(k=>({high:Number(k[2]),close:Number(k[4]),volume:Number(k[5])})));
  }catch{asset.signals=[];asset.rsi=null;asset.score=0;asset.historyUnavailable=true;}}};
  await Promise.all(Array.from({length:5},worker));
  historyPending=false;render();
}
async function loadCrypto(){
  const count=document.querySelector('#crypto-count');
  try {
    const response=await fetch('https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1&sparkline=false&price_change_percentage=24h',{headers:{accept:'application/json'}});
    if(!response.ok) throw new Error(`HTTP ${response.status}`);
    const data=await response.json();
    cryptoAssets=data.map(c=>({id:c.id,symbol:c.symbol.toUpperCase(),name:c.name,market:'Crypto',price:Number(c.current_price)||0,change:Number(c.price_change_percentage_24h)||0,rsi:null,signals:[],score:0}));
    const btc=data.find(c=>c.id==='bitcoin');
    if(btc){document.querySelector('#btc-price').innerHTML=`${money(btc.current_price)} <small>USD</small>`;document.querySelector('#btc-change').textContent=`${btc.price_change_percentage_24h>=0?'+':''}${Number(btc.price_change_percentage_24h).toFixed(2)}%`;document.querySelector('#btc-change').className=`pulse-change ${btc.price_change_percentage_24h>=0?'positive':'change-down'}`;}
    count.textContent=cryptoAssets.length;
  } catch(error) {
    cryptoAssets=cryptoFallback.map(([id,name,symbol])=>({symbol,name,market:'Crypto',price:0,change:null,fallback:true}));
    count.textContent=cryptoAssets.length;
    document.querySelector('#showing').title='เชื่อมต่อ CoinGecko ไม่สำเร็จ แสดงรายการตัวอย่าง';
  }
  render();
  if(cryptoAssets.length) await loadCryptoHistory();
}
document.querySelector('#today').textContent=new Intl.DateTimeFormat('th-TH',{dateStyle:'medium'}).format(new Date());
document.querySelector('#year').textContent=new Date().getFullYear();
document.querySelectorAll('[data-market]').forEach(el=>el.addEventListener('click',()=>{selectedMarket=el.dataset.market;page=1;render();if(el.classList.contains('market-link'))document.querySelector('#screener').scrollIntoView({behavior:'smooth'});}));
document.querySelector('#search').addEventListener('input',()=>{page=1;render();});
document.querySelector('#signal-filter').addEventListener('change',()=>{page=1;render();});
document.querySelector('#refresh').addEventListener('click',async()=>{const b=document.querySelector('#refresh');b.disabled=true;try{await Promise.all([loadCrypto(),loadStockSnapshot()]);}finally{b.disabled=false;}});
const filters=document.createElement('section');
filters.className='advanced-filters';
filters.innerHTML=`<h3>เงื่อนไขคัดกรอง</h3><div class="filter-grid"><label>รูปแบบ <select id="filter-mode"><option value="and">ตรงทุกข้อ (AND)</option><option value="or">อย่างน้อยหนึ่งข้อ (OR)</option></select></label><label>Preset <select id="preset"><option value="">เลือกชุดเงื่อนไข</option><option value="breakout">Breakout แข็งแรง</option><option value="momentum">โมเมนตัมขาขึ้น</option><option value="oversold">Oversold</option></select></label><label>RSI ต่ำสุด <input id="rsi-min" type="number" min="0" max="100"></label><label>RSI สูงสุด <input id="rsi-max" type="number" min="0" max="100"></label><label>Volume ขั้นต่ำ (×) <input id="volume-min" type="number" min="0" step="0.1"></label><label>คะแนนขั้นต่ำ <input id="score-min" type="number" min="0"></label></div><div class="condition-list">${[['breakout','Breakout 20D'],['rsi-high','RSI ≥70'],['rsi-momentum','RSI 55–70'],['volume','Volume Spike'],['macd','MACD Cross'],['trend','EMA ขาขึ้น'],['rsi-low','Oversold']].map(([v,l])=>`<label><input data-condition type="checkbox" value="${v}"> ${l}</label>`).join('')}</div><div class="filter-actions"><button id="save-filters">บันทึกตัวกรอง</button><button id="reset-filters">ล้างเงื่อนไข</button><label><input id="watch-only" type="checkbox"> เฉพาะ Watchlist</label><button id="export-watch">ส่งออก Watchlist สำหรับ LINE</button><span id="filter-message" role="status"></span></div><small>Watchlist บันทึกในเบราว์เซอร์นี้ · LINE ใช้รายการที่ส่งออกไปตั้งค่าใน GitHub Secrets</small>`;
document.querySelector('.table-wrap').before(filters);
const pagination=document.createElement('div');pagination.className='pagination';
pagination.innerHTML='<button id="page-prev">← ก่อนหน้า</button><span id="page-label"></span><button id="page-next">ถัดไป →</button>';
document.querySelector('.table-wrap').after(pagination);
const filterState=()=>({mode:document.querySelector('#filter-mode').value,market:selectedMarket,types:[...document.querySelectorAll('[data-condition]:checked')].map(e=>e.value),values:Object.fromEntries(['rsi-min','rsi-max','volume-min','score-min'].map(id=>[id,document.querySelector('#'+id).value]))});
function applyFilterState(s){document.querySelector('#filter-mode').value=s.mode||'and';selectedMarket=s.market||'All';document.querySelectorAll('[data-condition]').forEach(e=>e.checked=(s.types||[]).includes(e.value));for(const id of ['rsi-min','rsi-max','volume-min','score-min'])document.querySelector('#'+id).value=s.values?.[id]??'';document.querySelector('#signal-filter').value='all';page=1;render();}
filters.addEventListener('change',()=>{page=1;render();});
document.querySelector('#preset').addEventListener('change',e=>{const presets={breakout:{types:['breakout','volume'],values:{'rsi-min':55,'rsi-max':70,'volume-min':1.5}},momentum:{types:['trend','rsi-momentum'],values:{'rsi-min':55,'rsi-max':69.9}},oversold:{types:['rsi-low'],values:{'rsi-max':29.9}}};if(presets[e.target.value])applyFilterState({...presets[e.target.value],market:selectedMarket});});
document.querySelector('#save-filters').addEventListener('click',()=>{try{localStorage.setItem('ms-filters',JSON.stringify(filterState()));document.querySelector('#filter-message').textContent='บันทึกแล้ว';}catch{document.querySelector('#filter-message').textContent='เบราว์เซอร์ไม่อนุญาตให้บันทึก';}});
document.querySelector('#reset-filters').addEventListener('click',()=>{document.querySelector('#preset').value='';applyFilterState({});});
document.querySelector('#page-prev').addEventListener('click',()=>{page--;render();});
document.querySelector('#page-next').addEventListener('click',()=>{page++;render();});
document.querySelector('#asset-rows').addEventListener('click',e=>{const button=e.target.closest('[data-watch]');if(!button)return;const key=button.dataset.watch;watchlist.has(key)?watchlist.delete(key):watchlist.add(key);try{localStorage.setItem('ms-watchlist',JSON.stringify([...watchlist]));}catch{}render();});
document.querySelector('#export-watch').addEventListener('click',()=>{const blob=new Blob([JSON.stringify([...watchlist],null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='watchlist.json';a.click();URL.revokeObjectURL(url);});
applyFilterState(stored('ms-filters',{}));
document.querySelector('thead th:nth-child(4)').textContent='เปลี่ยนแปลง หุ้น 1D / Crypto 24h';
loadCrypto();
loadStockSnapshot();
