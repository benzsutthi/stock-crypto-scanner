const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const code = fs.readFileSync('app.js', 'utf8');
const values = {'filter-mode':'and','rsi-min':'55','rsi-max':'70','volume-min':'1.5','score-min':'35'};
const document = {
  querySelector: id => ({value:values[id.slice(1)]??'',checked:false}),
  querySelectorAll: () => [{value:'breakout'},{value:'volume'}]
};
const context = vm.createContext({document, money: String, watchlist:new Set(), assetKey:a=>`${a.market}:${a.symbol}`});
vm.runInContext(code.slice(code.indexOf('function matchesFilters'),code.indexOf('function render')),context);
const asset = {rsi:60,volumeRatio:2,score:55,signals:[{type:'breakout'},{type:'volume'}]};
assert.equal(context.matchesFilters(asset),true);
assert.equal(context.matchesFilters({...asset,rsi:null}),false);
assert.equal(context.matchesFilters({...asset,signals:[{type:'volume'}]}),false);
values['filter-mode']='or';
assert.equal(context.matchesFilters({...asset,signals:[{type:'volume'}]}),true);
assert.equal(context.matchesFilters({...asset,volumeRatio:1.49}),false);
vm.runInContext(code.slice(code.indexOf('function ema'),code.indexOf('async function loadCryptoHistory')),context);
const candles=Array.from({length:60},()=>({close:100,high:101,volume:100}));
const flat={};context.analyzeHistory(flat,candles);assert.equal(flat.rsi,50);
candles[59]={close:102,high:105,volume:200};
const breakout={};context.analyzeHistory(breakout,candles);
assert.equal(breakout.volumeRatio,2);
assert.ok(breakout.signals.some(s=>s.type==='breakout'));
console.log('AND/OR, numeric boundaries, missing data, RSI and breakout checks passed');
