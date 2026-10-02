const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {nextScheduledRefresh,marketSessionLabel}=require('./updates.js');
assert.equal(nextScheduledRefresh(new Date('2026-10-01T23:50:00Z')).toISOString(),'2026-10-02T00:17:00.000Z');
assert.equal(nextScheduledRefresh(new Date('2026-10-01T10:17:00Z')).toISOString(),'2026-10-01T10:47:00.000Z');
assert.match(marketSessionLabel('US',new Date('2026-11-02T13:30:00Z')),/นอกเวลา/);
assert.match(marketSessionLabel('US',new Date('2026-11-02T14:30:00Z')),/^ช่วงเวลา/);
assert.equal(marketSessionLabel('Crypto'),'ตลาด 24/7');

let now=Date.parse('2026-10-01T10:00:00Z');
class Clock extends Date{constructor(...args){super(...(args.length?args:[now]));}static now(){return now;}}
const nodes=new Map(),intervals=[],events={};
const makeNode=()=>({textContent:'',innerHTML:'',append(){},addEventListener(type,fn){this[type]=fn;}});
const document={hidden:false,createElement:makeNode,querySelector(key){if(!nodes.has(key))nodes.set(key,makeNode());return nodes.get(key);},addEventListener(type,fn){events[type]=fn;}};
const window={addEventListener(type,fn){events[type]=fn;}};
const context=vm.createContext({window,document,navigator:{onLine:true},Date:Clock,Intl,localStorage:{getItem:()=>null,setItem(){}},setInterval:fn=>intervals.push(fn)});
vm.runInContext(fs.readFileSync('updates.js','utf8'),context);
let polls=0;window.MarketUpdates.start(()=>{polls++;window.MarketUpdates.checked();});
now+=301000;intervals[0]();assert.equal(polls,1);
document.hidden=true;now+=301000;intervals[0]();assert.equal(polls,1);
document.hidden=false;events.visibilitychange();assert.equal(polls,2);
nodes.get('#auto-refresh').checked=false;nodes.get('#auto-refresh').change();now+=301000;intervals[0]();assert.equal(polls,2);

const app=fs.readFileSync('app.js','utf8');
let resolveCrypto,resolveStocks,calls=0;
const button={};
const refresh=vm.createContext({Promise,document:{querySelector:()=>button},loadCrypto:()=>{calls++;return new Promise(r=>resolveCrypto=r);},loadStockSnapshot:()=>{calls++;return new Promise(r=>resolveStocks=r);}});
vm.runInContext(app.slice(app.indexOf('let refreshInFlight'),app.indexOf("document.querySelector('#today')")),refresh);
const first=refresh.refreshMarketData(),second=refresh.refreshMarketData();
assert.equal(first,second);assert.equal(calls,2);assert.equal(button.disabled,true);
resolveCrypto();resolveStocks();first.then(()=>{assert.equal(button.disabled,false);console.log('Schedules, DST, automatic polling, tab pause, toggle and overlapping refresh checks passed');}).catch(error=>{console.error(error);process.exitCode=1;});
