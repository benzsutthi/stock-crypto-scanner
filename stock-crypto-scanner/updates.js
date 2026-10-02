function nextScheduledRefresh(now=new Date()) {
  const next=new Date(now);next.setUTCSeconds(0,0);
  if(now.getUTCMinutes()<17)next.setUTCMinutes(17);
  else if(now.getUTCMinutes()<47)next.setUTCMinutes(47);
  else{next.setUTCHours(next.getUTCHours()+1);next.setUTCMinutes(17);}
  return next;
}

function marketSessionLabel(market,now=new Date()) {
  if(market==='Crypto')return 'ตลาด 24/7';
  const zone=market==='Thai'?'Asia/Bangkok':'America/New_York';
  const parts=new Intl.DateTimeFormat('en-US',{timeZone:zone,weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(now);
  const get=t=>parts.find(p=>p.type===t).value;
  const minutes=Number(get('hour'))*60+Number(get('minute'));
  if(['Sat','Sun'].includes(get('weekday')))return 'นอกเวลาตลาดปกติ';
  const open=market==='Thai'?(minutes>=600&&minutes<=750)||(minutes>=840&&minutes<=990):minutes>=570&&minutes<=960;
  return open?'ช่วงเวลาตลาดปกติ (ไม่รวมวันหยุด)':'นอกเวลาตลาดปกติ';
}

if(typeof module!=='undefined'&&module.exports)module.exports={nextScheduledRefresh,marketSessionLabel};
if(typeof window!=='undefined'&&typeof document!=='undefined'){
  const snapshots={};
  let nextCheck=Date.now()+300000;
  let auto=true;
  try{auto=JSON.parse(localStorage.getItem('ms-auto-refresh'))!==false;}catch{}
  const format=value=>{const date=new Date(value);return Number.isFinite(date.getTime())?new Intl.DateTimeFormat('th-TH',{dateStyle:'short',timeStyle:'medium',timeZone:'Asia/Bangkok'}).format(date):'—';};
  function renderStatus(){
    const root=document.querySelector('#market-update-cards');
    if(!root)return;
    root.innerHTML='';
    for(const [market,title] of [['Thai','หุ้นไทย'],['US','หุ้นสหรัฐ'],['Crypto','Crypto Top 100']]){
      const state=snapshots[market];
      const assetList=state?.assets||[];
      const generated=state?.snapshot?.generatedAt;
      const age=generated?(Date.now()-Date.parse(generated))/60000:Infinity;
      const marketInfo=state?.snapshot?.marketRefresh?.[market];
      const problem=state?.error||state?.snapshot?.keptPreviousSnapshot||(marketInfo?(marketInfo.failedHistory||marketInfo.failedQuotes):state?.snapshot?.updateError)||assetList.some(a=>a.historyUpdateError);
      const label=!state?'รอข้อมูล':state.error&&!assetList.length?'โหลดข้อมูลไม่สำเร็จ':problem?'ใช้ข้อมูลเดิม / บางส่วนไม่พร้อม':age>90?'ชุดข้อมูลเกิน 90 นาที':'โหลดชุดข้อมูลสำเร็จ';
      const dates=assetList.map(a=>a.priceDate).filter(Boolean).sort();
      const quoted=assetList.map(a=>a.quoteAt).filter(Boolean).sort((a,b)=>Date.parse(a)-Date.parse(b));
      const history=dates.length?(dates[0]===dates.at(-1)?dates[0]:`${dates[0]} – ${dates.at(-1)}`):'—';
      const card=document.createElement('article');card.className='update-card';
      const heading=document.createElement('h3');heading.textContent=title;card.append(heading);
      const badge=document.createElement('span');badge.className=`update-badge ${problem||age>90?'update-warning':''}`;badge.textContent=label;card.append(badge);
      const dl=document.createElement('dl');
      const rows=[['ชุดข้อมูลจากระบบ',generated?format(generated):'—'],['ตรวจบนเว็บล่าสุด',state?format(state.checkedAt):'—'],['อ้างอิงราคาล่าสุด',quoted.length?format(quoted.at(-1)):dates.at(-1)||'—'],['วันแท่งสัญญาณ',history],['จำนวนข้อมูล',`${assetList.length} รายการ · วิเคราะห์ ${assetList.filter(a=>Number.isFinite(a.rsi)).length}`]];
      for(const [key,value] of rows){const row=document.createElement('div');const dt=document.createElement('dt');dt.textContent=key;const dd=document.createElement('dd');dd.textContent=value;row.append(dt,dd);dl.append(row);}card.append(dl);
      const method=document.createElement('p');method.textContent=market==='Crypto'?`${state?.snapshot?.source||'CoinPaprika / CoinGecko'} · ราคาและ % 24 ชม. ทุก 30 นาที · สัญญาณแท่งปิด UTC`: 'Yahoo Finance · ดึงราคาจากแท่ง 15 นาทีช่วงตลาดเปิด (อาจล่าช้า) · สัญญาณใช้แท่งปิดรายวัน';card.append(method);
      const session=document.createElement('small');session.textContent=marketSessionLabel(market);card.append(session);root.append(card);
    }
    document.querySelector('#next-publish').textContent=`รอบสร้างข้อมูลตามแผนถัดไป: ${format(nextScheduledRefresh())} (เวลาไทย) · GitHub Actions อาจเริ่มล่าช้า`;
  }
  let runRefresh;
  const checkbox=document.querySelector('#auto-refresh');
  if(checkbox){checkbox.checked=auto;checkbox.addEventListener('change',()=>{auto=checkbox.checked;try{localStorage.setItem('ms-auto-refresh',JSON.stringify(auto));}catch{}nextCheck=Date.now()+300000;tick();});}
  function tick(){
    const label=document.querySelector('#browser-refresh-status');
    if(label){const seconds=Math.max(0,Math.ceil((nextCheck-Date.now())/1000));label.textContent=!auto?'รีเฟรชอัตโนมัติปิดอยู่':navigator.onLine===false?'ออฟไลน์ · คงข้อมูลล่าสุดไว้':document.hidden?'พักการตรวจขณะไม่เปิดแท็บ':`เว็บตรวจข้อมูลใหม่ทุก 5 นาที · อีกประมาณ ${Math.ceil(seconds/60)} นาที`;}
    if(auto&&runRefresh&&!document.hidden&&navigator.onLine!==false&&Date.now()>=nextCheck){nextCheck=Date.now()+300000;runRefresh();}
  }
  window.MarketUpdates={
    update(market,snapshot,assets){snapshots[market]={snapshot,assets,checkedAt:new Date().toISOString(),error:false};renderStatus();},
    failed(market){if(snapshots[market]){snapshots[market].error=true;snapshots[market].checkedAt=new Date().toISOString();}else snapshots[market]={assets:[],error:true,checkedAt:new Date().toISOString()};renderStatus();},
    checked(){nextCheck=Date.now()+300000;tick();},
    start(refresh){runRefresh=refresh;renderStatus();tick();setInterval(tick,15000);setInterval(renderStatus,60000);document.addEventListener('visibilitychange',tick);window.addEventListener('focus',tick);window.addEventListener('online',tick);}
  };
}
