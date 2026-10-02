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
  let current=null;
  const format=n=>Number.isFinite(n)?new Intl.NumberFormat('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}).format(n):'—';
  function render(index,failed=false){
    document.querySelector('#set-value').innerHTML=`${format(index.value)} <small>จุด</small>`;
    const change=document.querySelector('#set-change');change.textContent=indexChangeText(index);
    change.className=`pulse-change ${index.changePoints<0?'change-down':Number.isFinite(index.changePoints)?'positive':''}`;
    for(const [id,key] of [['set-open','open'],['set-high','high'],['set-low','low'],['set-previous','previousClose']])document.querySelector('#'+id).textContent=format(index[key]);
    const points=indexChartPoints((index.chart||[]).map(p=>p.value));
    const chart=document.querySelector('#set-chart');chart.style.display=points?'block':'none';chart.classList.toggle('negative',index.changePoints<0);
    document.querySelector('#set-chart-line').setAttribute('points',points);
    document.querySelector('#set-chart-caption').textContent=points?`กราฟแท่ง 15 นาที · ${index.chartDate||''}`:'';
    chart.setAttribute('aria-label',`กราฟ SET Index จากแท่ง 15 นาที วันที่ ${index.chartDate||'ไม่ระบุ'}`);
    const date=new Date(index.quoteAt||'');
    const reference=Number.isFinite(date.getTime())?new Intl.DateTimeFormat('th-TH',{dateStyle:'short',timeStyle:'short',timeZone:'Asia/Bangkok'}).format(date):'ไม่ระบุเวลาราคา';
    const source=document.querySelector('#set-source');
    source.textContent=`${index.source||'Yahoo Finance (^SET.BK)'} · อ้างอิง ${reference} · อาจล่าช้า${failed||index.updateError?' · ใช้ข้อมูลรอบก่อน':''}`;
    source.classList.toggle('warning',Boolean(failed||index.updateError));
  }
  window.MarketIndices={async load(){
    try{
      const response=await fetch(`data/indices.json?updated=${Date.now()}`,{cache:'no-store',signal:AbortSignal.timeout(20000)});
      if(!response.ok)throw new Error(`HTTP ${response.status}`);
      const snapshot=await response.json(),index=snapshot.indices?.SET;
      if(!index||!Number.isFinite(index.value)||index.value<=0)throw new Error('SET unavailable');
      current=index;render(index);
      try{localStorage.setItem('ms-set-index',JSON.stringify(index));}catch{}
    }catch{
      if(!current){try{current=JSON.parse(localStorage.getItem('ms-set-index'));}catch{}}
      if(current&&Number.isFinite(current.value)&&current.value>0)render(current,true);
      else{document.querySelector('#set-change').textContent='ข้อมูลไม่พร้อม';document.querySelector('#set-source').textContent='ยังโหลดข้อมูล SET Index ไม่สำเร็จ · ลองรีเฟรชอีกครั้ง';}
    }
  }};
}
