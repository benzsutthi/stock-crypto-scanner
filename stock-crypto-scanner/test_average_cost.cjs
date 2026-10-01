const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {calculateAverageCost} = require('./average-cost.js');
const approx=(actual,expected)=>assert.ok(Math.abs(actual-expected)<=Math.max(1,Math.abs(expected))*1e-12);
let result=calculateAverageCost({oldPrice:100,oldQuantity:1000,newPrice:80,newQuantity:1000});
assert.equal(result.average,90);
assert.equal(result.totalCost,180000);
assert.equal(result.totalQuantity,2000);
assert.equal(result.differencePercent,-10);
result=calculateAverageCost({oldPrice:100,oldQuantity:100,newPrice:50,newQuantity:300,fees:200});
assert.equal(result.average,63);
assert.equal(result.newCost,15200);
result=calculateAverageCost({oldPrice:60000,oldQuantity:.01,newPrice:50000,newQuantity:.02});
approx(result.average,1600/.03);
approx(result.totalQuantity,.03);
assert.throws(()=>calculateAverageCost({oldPrice:100,oldQuantity:0,newPrice:80,newQuantity:1000}));
assert.throws(()=>calculateAverageCost({oldPrice:100,oldQuantity:1,newPrice:80,newQuantity:1,fees:-1}));
assert.throws(()=>calculateAverageCost({oldPrice:NaN,oldQuantity:1,newPrice:80,newQuantity:1}));
assert.throws(()=>calculateAverageCost({oldPrice:1e308,oldQuantity:1e308,newPrice:80,newQuantity:1}));

// Exercise real form handlers: example, live editing, invalid input and reset.
const elements=new Map();
function element(id){if(!elements.has(id))elements.set(id,{value:id==='currency'?'THB':'',textContent:'',className:'',listeners:{},attributes:{},addEventListener(type,fn){this.listeners[type]=fn;},setAttribute(k,v){this.attributes[k]=v;},removeAttribute(k){delete this.attributes[k];}});return elements.get(id);}
const context=vm.createContext({document:{querySelector:selector=>element(selector.slice(1))},Intl,setTimeout:fn=>fn()});
vm.runInContext(fs.readFileSync('average-cost.js','utf8'),context);
element('example').listeners.click();
assert.equal(element('average').textContent,'90.00 THB');
element('new-price').value='120';
element('average-form').listeners.input();
assert.equal(element('average').textContent,'110.00 THB');
assert.match(element('average-change').textContent,/เพิ่มขึ้น/);
element('new-quantity').value='0';
element('average-form').listeners.submit({preventDefault(){}});
assert.equal(element('average').textContent,'—');
assert.match(element('input-error').textContent,/มากกว่า 0/);
element('average-form').listeners.reset();
assert.equal(element('input-error').textContent,'');
console.log('Average cost: weighted quantities, fees, fractions, invalid inputs and form interaction passed');
