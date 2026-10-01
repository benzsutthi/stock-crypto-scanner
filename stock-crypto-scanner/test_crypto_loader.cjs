const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const code = fs.readFileSync('app.js','utf8');
const loader = code.slice(code.indexOf('async function loadCrypto(){'),code.indexOf("document.querySelector('#today')"));
const nodes = new Map();
const storage = new Map();
const snapshot = {generatedAt:new Date().toISOString(),source:'CoinPaprika',assets:[
  {symbol:'BTC',price:100,change:2,rsi:60,signals:[{type:'breakout'}],historyUnavailable:false}
]};
const context = vm.createContext({
  Date, Intl, AbortSignal,
  document:{querySelector: key=>{if(!nodes.has(key))nodes.set(key,{});return nodes.get(key);}},
  localStorage:{setItem:(key,value)=>storage.set(key,value)},
  stored:(key,fallback)=>storage.has(key)?JSON.parse(storage.get(key)):fallback,
  render:()=>{},
  fetch:async url=>{assert.ok(url.startsWith('data/crypto.json?'));return {ok:true,json:async()=>snapshot};}
});
vm.runInContext('let cryptoAssets=[]; const money=String;'+loader,context);
(async()=>{
  await context.loadCrypto();
  assert.equal(vm.runInContext('cryptoAssets[0].rsi',context),60);
  assert.match(nodes.get('#crypto-data-status').textContent,/วิเคราะห์ได้ 1\/1/);
  context.fetch=async()=>{throw new Error('offline');};
  vm.runInContext('cryptoAssets=[]',context);
  await context.loadCrypto();
  assert.equal(vm.runInContext('cryptoAssets[0].rsi',context),60);
  assert.match(nodes.get('#crypto-data-status').textContent,/ครั้งก่อน/);
  console.log('Same-origin snapshot loading and offline analysis cache passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
