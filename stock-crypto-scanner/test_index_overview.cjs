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
  fetch:async url=>{assert.ok(url.startsWith('data/indices.json?'));return {ok:true,json:async()=>({indices:{SET:index}})};}});
vm.runInContext(fs.readFileSync('index-overview.js','utf8'),context);
(async()=>{await context.window.MarketIndices.load();assert.match(node('#set-value').innerHTML,/1,570.62/);assert.equal(node('#set-change').textContent,'+6.71 (+0.43%)');assert.equal(node('#set-chart').style.display,'block');context.fetch=async()=>{throw new Error('offline');};await context.window.MarketIndices.load();assert.match(node('#set-value').innerHTML,/1,570.62/);assert.match(node('#set-source').textContent,/รอบก่อน/);console.log('SET chart, change formatting, snapshot rendering and retained data passed');})().catch(error=>{console.error(error);process.exitCode=1;});
