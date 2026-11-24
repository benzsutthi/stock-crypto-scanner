const assert = require('node:assert');
const { calculatePortfolio, validateHoldingInput, parseGoogleSheetUrl, parsePortfolioCsv } = require('./portfolio.js');

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

// 4. Google Sheets URL & CSV import
const csvUrl = parseGoogleSheetUrl('https://docs.google.com/spreadsheets/d/1XJjMCBopfrYrxYYQLa7AxXb6-vAFL3VnlcC7T9VxrD4/edit?gid=146811986#gid=146811986');
assert.strictEqual(
  csvUrl,
  'https://docs.google.com/spreadsheets/d/1XJjMCBopfrYrxYYQLa7AxXb6-vAFL3VnlcC7T9VxrD4/gviz/tq?tqx=out:csv&gid=146811986'
);
assert.strictEqual(
  parseGoogleSheetUrl('https://docs.google.com/spreadsheets/d/1XJjMCBopfrYrxYYQLa7AxXb6-vAFL3VnlcC7T9VxrD4/edit?usp=drivesdk'),
  'https://docs.google.com/spreadsheets/d/1XJjMCBopfrYrxYYQLa7AxXb6-vAFL3VnlcC7T9VxrD4/gviz/tq?tqx=out:csv&gid=146811986'
);

const sampleCsv = [
  'Ticker,Asset Class,Shares/Units,avg invest,Current Price,Current Value THB,Total invest CostTHB',
  'JEPQ US,ETF (US),29.0124110,56.457,54.0300,53280.70,55673.5806',
  'SCB,Stock (TH),,,153.5000,0.00,',
  'BTCTHB,Crypto,0.0546437,5313893.611,2053747.8580,112224.38,290370.8083',
  'ondo,Crypto,1351.769884,21.918,10.6540,14401.76,29627.61',
  'KT-JEPQ,THFund,492.1125,10.000,9.5786,4713.75,4921.13',
  ',,,,,660317.97,1395789.263',
].join('\n');

const imported = parsePortfolioCsv(sampleCsv);
assert.strictEqual(imported.holdings.length, 4);
assert.strictEqual(imported.holdings[0].symbol, 'JEPQ');
assert.strictEqual(imported.holdings[0].currency, 'USD');
assert.strictEqual(imported.holdings[1].symbol, 'BTCTHB');
assert.strictEqual(imported.holdings[1].currency, 'THB');
assert.strictEqual(imported.holdings[2].symbol, 'ONDO');
assert.strictEqual(imported.holdings[2].currency, 'THB');
assert.strictEqual(imported.holdings[3].symbol, 'KT-JEPQ');
assert.strictEqual(imported.holdings[3].currency, 'THB');
assert.ok(imported.inferredUsdThbRate > 33 && imported.inferredUsdThbRate < 35);

const sheetCalc = calculatePortfolio(imported.holdings, {
  baseCurrency: 'THB',
  usdThbRate: imported.inferredUsdThbRate,
});
assert.strictEqual(sheetCalc.liveCount, 4);

console.log('Portfolio: multi-currency allocation, live P&L fallback, Google Sheets CSV and validation passed');
