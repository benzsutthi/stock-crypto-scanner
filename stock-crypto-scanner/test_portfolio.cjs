const assert = require('node:assert');
const { calculatePortfolio, validateHoldingInput } = require('./portfolio.js');

// 1. Multi-asset allocation with mixed THB & USD currencies
const result = calculatePortfolio(
  [
    { id: '1', symbol: 'PTT', market: 'Thai', currency: 'THB', cost: 30, quantity: 1000 }, // 30,000 THB
    { id: '2', symbol: 'NVDA', market: 'US', currency: 'USD', cost: 100, quantity: 10 }, // 1,000 USD = 35,000 THB
    { id: '3', symbol: 'BTC', market: 'Crypto', currency: 'USD', cost: 50000, quantity: 0.02 }, // 1,000 USD = 35,000 THB
  ],
  {
    baseCurrency: 'THB',
    usdThbRate: 35,
    weightBy: 'value',
    priceMap: {
      'Thai:PTT': { price: 33 }, // 33,000 THB (+10%)
      'US:NVDA': { price: 120 }, // 1,200 USD = 42,000 THB (+20%)
      // BTC has no live price -> falls back to cost 35,000 THB
    },
  }
);

assert.strictEqual(result.items.length, 3);
assert.strictEqual(result.totalCostBase, 100000);
assert.strictEqual(result.totalValueBase, 110000);
assert.strictEqual(result.totalPnlBase, 10000);
assert.strictEqual(result.liveCount, 2);

const totalPct = result.items.reduce((s, i) => s + i.allocationPct, 0);
assert.ok(Math.abs(totalPct - 100) < 1e-6, 'Allocations must sum to 100%');
const nvda = result.items.find((i) => i.symbol === 'NVDA');
assert.ok(Math.abs(nvda.allocationPct - (42000 / 110000) * 100) < 1e-6);
assert.strictEqual(nvda.pnlPct, 20);

// 2. Weight by cost mode
const costMode = calculatePortfolio(
  [
    { symbol: 'A', market: 'Thai', currency: 'THB', cost: 10, quantity: 100 },
    { symbol: 'B', market: 'Thai', currency: 'THB', cost: 30, quantity: 100 },
  ],
  { baseCurrency: 'THB', weightBy: 'cost', priceMap: { 'Thai:A': { price: 50 } } }
);
assert.strictEqual(costMode.items.find((i) => i.symbol === 'A').allocationPct, 25);
assert.strictEqual(costMode.items.find((i) => i.symbol === 'B').allocationPct, 75);

// 3. Validation
assert.throws(() => validateHoldingInput({ symbol: '', cost: 10, quantity: 1 }));
assert.throws(() => validateHoldingInput({ symbol: 'PTT', cost: 0, quantity: 10 }));
assert.throws(() => validateHoldingInput({ symbol: 'PTT', cost: 10, quantity: -5 }));

console.log('Portfolio: multi-currency allocation, live P&L fallback and validation passed');
