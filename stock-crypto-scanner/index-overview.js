function indexChartPoints(values,width=200,height=40){
  const prices=values.filter(v=>Number.isFinite(v)&&v>0);
  if(prices.length<2)return '';
  const min=Math.min(...prices),max=Math.max(...prices),range=max-min;
  return prices.map((v,i)=>`${(i/(prices.length-1)*width).toFixed(2)},${(range?height-((v-min)/range)*(height-4)-2:height/2).toFixed(2)}`).join(' ');
}
function indexChangeText(index){
  const signed=n=>`${n>=0?'+':''}${n.toFixed(2)}`;
  const points=Number.isFinite(index.changePoints)?signed(index.changePoints):null;
  const percent=Number.isFinite(index.changePercent)?signed(index.changePercent)+'%':null;
  return points&&percent?`${points} (${percent})`:points?`${points} จุด`:percent||'—';
}
if(typeof module!=='undefined'&&module.exports)module.exports={indexChartPoints,indexChangeText};
if(typeof window!=='undefined'&&typeof document!=='undefined'){
  const current={};
  const cards=[{key:'SET',prefix:'set',name:'SET Index',cache:'ms-set-index'},
    {key:'SP500',prefix:'sp',name:'S&P 500',cache:'ms-sp500-index'},
    {key:'BTC',prefix:'btc',name:'Bitcoin',cache:'ms-bitcoin-overview'}];
  const format=n=>Number.isFinite(n)?new Intl.NumberFormat('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}).format(n):'—';
  const compactUSD=n=>Number.isFinite(n)?'$'+new Intl.NumberFormat('en-US',{notation:'compact',maximumFractionDigits:2}).format(n):'—';
  const referenceTime=value=>{const date=new Date(value||'');return Number.isFinite(date.getTime())?new Intl.DateTimeFormat('th-TH',{dateStyle:'short',timeStyle:'short',timeZone:'Asia/Bangkok'}).format(date):'ไม่ระบุเวลา';};
  function render(index,card,failed=false){
    const prefix=card.prefix,btc=card.key==='BTC';
    document.querySelector(btc?'#btc-price':`#${prefix}-value`).innerHTML=`${btc?'$':''}${format(index.value)} <small>${btc?'USD':'จุด'}</small>`;
    const change=document.querySelector(`#${prefix}-change`);
    change.textContent=btc?Number.isFinite(index.changePercent)?`${index.changePercent>=0?'+':''}${index.changePercent.toFixed(2)}%`:'—':indexChangeText(index);
    const direction=btc?index.changePercent:index.changePoints;
    change.className=`pulse-change ${direction<0?'change-down':Number.isFinite(direction)?'positive':''}`;
    for(const [id,key] of [[`${prefix}-open`,'open'],[`${prefix}-high`,'high'],[`${prefix}-low`,'low']])document.querySelector('#'+id).textContent=format(index[key]);
    if(!btc)document.querySelector(`#${prefix}-previous`).textContent=format(index.previousClose);
    else{
      document.querySelector('#btc-basis').textContent=index.changeBasis==='24h'?'เปลี่ยนแปลง 24 ชม.':index.changeBasis==='utc-close'?'เปลี่ยนแปลงเทียบปิด UTC ก่อนหน้า':'เปลี่ยนแปลงเทียบปิดก่อนหน้า (Yahoo)';
      document.querySelector('#btc-volume').textContent=compactUSD(index.volume24h);
      document.querySelector('#btc-marketcap').textContent=compactUSD(index.marketCap);
      document.querySelector('#btc-rank').textContent=Number.isFinite(index.rank)?'#'+index.rank:'—';
      document.querySelector('#btc-rsi').textContent=Number.isFinite(index.rsi)?index.rsi.toFixed(1):'—';
      document.querySelector('#btc-closed').textContent=Number.isFinite(index.closedPrice)?`${format(index.closedPrice)} ${index.closedCurrency||'USD'}`:'—';
    }
    const points=indexChartPoints((Array.isArray(index.chart)?index.chart:[]).map(p=>p.value));
    const chart=document.querySelector(`#${prefix}-chart`);chart.style.display=points?'block':'none';chart.classList.toggle('negative',direction<0);
    document.querySelector(`#${prefix}-chart-line`).setAttribute('points',points);
    const caption=btc?'กราฟ 24 ชม. · แท่ง 15 นาที (UTC)':`กราฟแท่ง 15 นาที · ${index.chartDate||''}${card.key==='SP500'?' (นิวยอร์ก)':''}`;
    document.querySelector(`#${prefix}-chart-caption`).textContent=points?caption:'กราฟยังไม่พร้อม';
    chart.setAttribute('aria-label',`${card.name} · ${caption}`);
    const source=document.querySelector(`#${prefix}-source`);
    const staleQuote=btc&&Number.isFinite(Date.parse(index.quoteAt))&&Date.now()-Date.parse(index.quoteAt)>2*3600000;
    source.textContent=`${index.source||'Yahoo Finance'} · อ้างอิง ${referenceTime(index.quoteAt)} (เวลาไทย) · อาจล่าช้า${failed||index.updateError?' · ใช้ข้อมูลรอบก่อน':''}${staleQuote?' · ราคาเกิน 2 ชั่วโมง':''}`;
    source.classList.toggle('warning',Boolean(failed||index.updateError||staleQuote));
    if(btc){
      document.querySelector('#btc-range-source').textContent=points?`${index.chartSource||'Yahoo Finance (BTC-USD)'} · ช่วงวัน UTC ${index.rangeDate||'—'} · แท่งล่าสุด ${referenceTime(index.rangeAt)} (เวลาไทย)`:'กราฟและช่วงวัน UTC ยังไม่พร้อม';
      const technical=document.querySelector('#btc-technical-source');
      technical.textContent=Number.isFinite(index.rsi)?`RSI/ปิดวิเคราะห์: ${index.technicalDate||'—'} UTC · ${index.technicalSource||'—'}${index.technicalWarning?' · ข้อมูลวิเคราะห์รอบก่อน':''}`:'ข้อมูล RSI จากแท่งปิดยังไม่พร้อม';
      technical.classList.toggle('warning',Boolean(index.technicalWarning));
    }
  }
  function keepPrevious(card){
    if(!current[card.key]){try{current[card.key]=JSON.parse(localStorage.getItem(card.cache));}catch{}}
    const index=current[card.key];
    if(index&&Number.isFinite(index.value)&&index.value>0)render(index,card,true);
    else{document.querySelector(`#${card.prefix}-change`).textContent='ข้อมูลไม่พร้อม';document.querySelector(`#${card.prefix}-source`).textContent=`ยังโหลดข้อมูล ${card.name} ไม่สำเร็จ · ลองรีเฟรชอีกครั้ง`;}
  }
  window.MarketIndices={async load(){
    try{
      const response=await fetch(`data/indices.json?updated=${Date.now()}`,{cache:'no-store',signal:AbortSignal.timeout(20000)});
      if(!response.ok)throw new Error(`HTTP ${response.status}`);
      const snapshot=await response.json();
      if(!snapshot.indices&&!snapshot.bitcoin)throw new Error('Overview unavailable');
      for(const card of cards){
        const index=card.key==='BTC'?snapshot.bitcoin:snapshot.indices?.[card.key];
        if(!index||!Number.isFinite(index.value)||index.value<=0){keepPrevious(card);continue;}
        current[card.key]=index;render(index,card);
        try{localStorage.setItem(card.cache,JSON.stringify(index));}catch{}
      }
    }catch{
      for(const card of cards)keepPrevious(card);
    }
  }};
}
