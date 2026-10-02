const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {indexChartPoints,indexChangeText}=require('./index-overview.js');
assert.equal(indexChartPoints([100]),'');
assert.equal(indexChartPoints([100,100]),'0.00,20.00 200.00,20.00');
assert.equal(indexChangeText({changePoints:-5,changePercent:-.5}),'-5.00 (-0.50%)');
assert.equal(indexChangeText({changePoints:null,changePercent:null}),'—');
assert.equal(indexChartPoints([NaN,Infinity]),'');
const nodes=new Map(),storage=new Map();
const node=key=>{if(!nodes.has(key))nodes.set(key,{textContent:'',innerHTML:'',className:'',style:{},attrs:{},classes:{},setAttribute(k,v){this.attrs[k]=v;},classList:{toggle(k,v){nodes.get(key).classes[k]=v;}}});return nodes.get(key);};
const index={value:1570.62,changePoints:6.71,changePercent:.43,open:1567.2,previousClose:1563.91,high:1575.75,low:1564.97,quoteAt:'2026-10-02T05:30:00Z',chartDate:'2026-10-02',chart:[{value:1572},{value:1570.62}],source:'Yahoo Finance (^SET.BK)'};
const context=vm.createContext({window:{},document:{querySelector:node},Intl,Date,AbortSignal,
  localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},
  fetch:async url=>{assert.ok(url.startsWith('data/indices.json?'));return {ok:true,json:async()=>({indices:{SET:index,SP500:{...index,value:7666.45,changePoints:14.91,changePercent:.19,name:'S&P 500'}},bitcoin:{...index,value:85886.21,changePercent:2.9,changeBasis:'24h',volume24h:2.67e10,marketCap:1.73e12,rank:1,rsi:60.,closedPrice:84000,closedCurrency:'USDT',chartWindow:'24h',technicalDate:'2026-10-01',technicalSource:'Binance (USDT)'}})};}});
vm.runInContext(fs.readFileSync('index-overview.js','utf8'),context);
(async()=>{await context.window.MarketIndices.load();assert.match(node('#set-value').innerHTML,/1,570.62/);assert.equal(node('#set-change').textContent,'+6.71 (+0.43%)');assert.equal(node('#set-chart').style.display,'block');assert.match(node('#sp-value').innerHTML,/7,666.45/);assert.match(node('#btc-price').innerHTML,/85,886.21/);assert.equal(node('#btc-change').textContent,'+2.90%');assert.equal(node('#btc-chart').style.display,'block');assert.match(node('#btc-volume').textContent,/B/);assert.equal(node('#btc-rsi').textContent,'60.0');assert.match(node('#btc-closed').textContent,/USDT/);context.fetch=async()=>{throw new Error('offline');};await context.window.MarketIndices.load();assert.match(node('#set-value').innerHTML,/1,570.62/);assert.match(node('#set-source').textContent,/รอบก่อน/);assert.match(node('#sp-source').textContent,/รอบก่อน/);assert.match(node('#btc-source').textContent,/รอบก่อน/);console.log('SET/S&P/BTC charts, 24h fields, analysis currency and retained data passed');})().catch(error=>{console.error(error);process.exitCode=1;});
