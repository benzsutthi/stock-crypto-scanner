const PORTFOLIO_COLORS = [
  '#a8f05f', '#60a5fa', '#f59e0b', '#c084fc', '#34d399',
  '#f472b6', '#38bdf8', '#fb7185', '#facc15', '#a78bfa'
];

function toBaseCurrency(amount, currency, baseCurrency, usdThbRate) {
  const rate = Number.isFinite(usdThbRate) && usdThbRate > 0 ? usdThbRate : 34.5;
  const normalized = currency === 'USDT' ? 'USD' : currency;
  if (normalized === baseCurrency) return amount;
  if (normalized === 'USD' && baseCurrency === 'THB') return amount * rate;
  if (normalized === 'THB' && baseCurrency === 'USD') return amount / rate;
  return amount;
}

function validateHoldingInput({ symbol, cost, quantity }) {
  const cleanSymbol = String(symbol || '').trim().toUpperCase();
  if (!cleanSymbol) throw new Error('กรุณาระบุชื่อสินทรัพย์หรือ Ticker');
  if (!Number.isFinite(cost) || cost <= 0) throw new Error('ต้นทุนต่อหน่วยต้องมากกว่า 0');
  if (!Number.isFinite(quantity) || quantity <= 0) throw new Error('จำนวนหุ้น/เหรียญต้องมากกว่า 0');
  return cleanSymbol;
}

function calculatePortfolio(holdings, options = {}) {
  const baseCurrency = options.baseCurrency === 'USD' ? 'USD' : 'THB';
  const usdThbRate = Number.isFinite(options.usdThbRate) && options.usdThbRate > 0 ? options.usdThbRate : 34.5;
  const priceMap = options.priceMap || {};
  const weightBy = options.weightBy === 'cost' ? 'cost' : 'value';

  const items = holdings.map((h, idx) => {
    const symbol = String(h.symbol || '').trim().toUpperCase();
    const market = h.market || 'Other';
    const currency = h.currency || (market === 'Thai' ? 'THB' : 'USD');
    const cost = Number(h.cost);
    const quantity = Number(h.quantity);
    if (!symbol || !Number.isFinite(cost) || cost <= 0 || !Number.isFinite(quantity) || quantity <= 0) {
      return null;
    }

    const totalCost = cost * quantity;
    const key = `${market}:${symbol}`;
    const quote = priceMap[key] ?? priceMap[symbol] ?? null;
    const marketPrice = quote && Number.isFinite(quote.price) && quote.price > 0 ? quote.price : null;
    const hasLivePrice = marketPrice !== null;
    const currentValue = hasLivePrice ? marketPrice * quantity : totalCost;
    const pnl = hasLivePrice ? currentValue - totalCost : 0;
    const pnlPct = hasLivePrice && totalCost > 0 ? (pnl / totalCost) * 100 : null;

    const costBase = toBaseCurrency(totalCost, currency, baseCurrency, usdThbRate);
    const valueBase = toBaseCurrency(currentValue, currency, baseCurrency, usdThbRate);
    const pnlBase = hasLivePrice ? valueBase - costBase : 0;

    return {
      id: h.id || `${key}-${idx}`,
      symbol,
      name: h.name || quote?.name || symbol,
      market,
      currency,
      cost,
      quantity,
      totalCost,
      marketPrice,
      hasLivePrice,
      currentValue,
      pnl,
      pnlPct,
      costBase,
      valueBase,
      pnlBase,
      color: PORTFOLIO_COLORS[idx % PORTFOLIO_COLORS.length],
    };
  }).filter(Boolean);

  const totalCostBase = items.reduce((sum, item) => sum + item.costBase, 0);
  const totalValueBase = items.reduce((sum, item) => sum + item.valueBase, 0);
  const totalPnlBase = items.reduce((sum, item) => sum + item.pnlBase, 0);
  const totalPnlPct = totalCostBase > 0 ? (totalPnlBase / totalCostBase) * 100 : 0;
  const weightDenominator = weightBy === 'cost' ? totalCostBase : totalValueBase;

  const enriched = items.map((item) => {
    const numerator = weightBy === 'cost' ? item.costBase : item.valueBase;
    const allocationPct = weightDenominator > 0 ? (numerator / weightDenominator) * 100 : 0;
    return { ...item, allocationPct };
  }).sort((a, b) => b.allocationPct - a.allocationPct);

  return {
    baseCurrency,
    usdThbRate,
    weightBy,
    items: enriched,
    totalCostBase,
    totalValueBase,
    totalPnlBase,
    totalPnlPct,
    liveCount: enriched.filter((i) => i.hasLivePrice).length,
  };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { calculatePortfolio, validateHoldingInput, toBaseCurrency };
}

if (typeof document !== 'undefined') {
  const STORAGE_KEY = 'ms-portfolio-holdings';
  const SETTINGS_KEY = 'ms-portfolio-settings';
  const loadJson = (k, fallback) => { try { return JSON.parse(localStorage.getItem(k)) ?? fallback; } catch { return fallback; } };
  const saveJson = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} };

  let holdings = loadJson(STORAGE_KEY, []);
  let settings = loadJson(SETTINGS_KEY, { baseCurrency: 'THB', usdThbRate: 34.5, weightBy: 'value' });
  let priceMap = {};
  let catalog = [];
  let editingId = null;

  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmtMoney = (n, currency = 'THB') => {
    if (!Number.isFinite(n)) return '—';
    const cur = currency === 'USDT' ? 'USD' : currency;
    try {
      const formatted = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: cur,
        minimumFractionDigits: Math.abs(n) > 0 && Math.abs(n) < 1 ? 4 : 2,
        maximumFractionDigits: Math.abs(n) > 0 && Math.abs(n) < 1 ? 6 : 2,
      }).format(n);
      return currency === 'USDT' ? `${formatted.replace('$', '')} USDT` : formatted;
    } catch {
      return `${n.toLocaleString('en-US', { maximumFractionDigits: 4 })} ${currency}`;
    }
  };
  const fmtQty = (n) => new Intl.NumberFormat('en-US', { maximumFractionDigits: 8 }).format(n);

  function renderPortfolio() {
    const result = calculatePortfolio(holdings, { ...settings, priceMap });
    const base = result.baseCurrency;

    document.querySelector('#sum-cost').textContent = fmtMoney(result.totalCostBase, base);
    document.querySelector('#sum-value').textContent = fmtMoney(result.totalValueBase, base);
    const pnlEl = document.querySelector('#sum-pnl');
    const pnlPctEl = document.querySelector('#sum-pnl-pct');
    if (result.liveCount > 0) {
      const sign = result.totalPnlBase >= 0 ? '+' : '';
      pnlEl.textContent = `${sign}${fmtMoney(result.totalPnlBase, base)}`;
      pnlEl.className = result.totalPnlBase >= 0 ? 'pnl-up' : 'pnl-down';
      pnlPctEl.textContent = `${sign}${result.totalPnlPct.toFixed(2)}% เทียบต้นทุนรวม`;
      pnlPctEl.className = `sub-metric ${result.totalPnlBase >= 0 ? 'pnl-up' : 'pnl-down'}`;
    } else {
      pnlEl.textContent = '—';
      pnlEl.className = '';
      pnlPctEl.textContent = result.items.length ? 'ใช้ต้นทุนคำนวณสัดส่วน' : 'ยังไม่มีรายการ';
      pnlPctEl.className = 'sub-metric';
    }
    document.querySelector('#sum-count').textContent = `${result.items.length} รายการ`;
    document.querySelector('#sum-live').textContent = result.items.length
      ? `มีราคาตลาดล่าสุด ${result.liveCount}/${result.items.length} รายการ`
      : 'กรอกต้นทุนและจำนวนเพื่อเริ่มต้น';

    const bar = document.querySelector('#allocation-bar');
    const legend = document.querySelector('#allocation-legend');
    if (result.items.length) {
      bar.innerHTML = result.items.map((item) =>
        `<div class="allocation-segment" style="width:${item.allocationPct.toFixed(2)}%;background:${item.color}" title="${esc(item.symbol)}: ${item.allocationPct.toFixed(2)}%"></div>`
      ).join('');
      legend.innerHTML = result.items.map((item) =>
        `<span class="legend-item"><i class="legend-dot" style="background:${item.color}"></i><b>${esc(item.symbol)}</b> ${item.allocationPct.toFixed(2)}%</span>`
      ).join('');
    } else {
      bar.innerHTML = '';
      legend.innerHTML = '<small class="sub-metric">เพิ่มสินทรัพย์อย่างน้อย 1 รายการเพื่อแสดงกราฟสัดส่วน %</small>';
    }

    const tbody = document.querySelector('#portfolio-rows');
    if (!result.items.length) {
      tbody.innerHTML = '<tr><td colspan="9" class="loading-row">ยังไม่มีรายการในพอร์ต · กรอกข้อมูลทางซ้ายเพื่อเริ่มต้น</td></tr>';
      return;
    }

    tbody.innerHTML = result.items.map((item) => {
      const marketLabel = item.market === 'Thai' ? 'SET' : item.market === 'US' ? 'US' : item.market === 'Crypto' ? 'CRYPTO' : 'OTHER';
      const pnlText = item.hasLivePrice
        ? `<span class="${item.pnl >= 0 ? 'pnl-up' : 'pnl-down'}">${item.pnl >= 0 ? '+' : ''}${fmtMoney(item.pnl, item.currency)}<br><small>${item.pnlPct >= 0 ? '+' : ''}${item.pnlPct.toFixed(2)}%</small></span>`
        : '<span class="signal-empty">—</span>';
      const liveText = item.hasLivePrice ? fmtMoney(item.marketPrice, item.currency) : '<span class="signal-empty">ใช้ต้นทุน</span>';
      return `<tr>
        <td><span class="asset-name">${esc(item.symbol)}</span><small class="signal-empty">${esc(item.name !== item.symbol ? item.name : '')}</small></td>
        <td><span class="market-badge ${esc(item.market.toLowerCase())}">${marketLabel}</span></td>
        <td class="align-right">${fmtQty(item.quantity)}</td>
        <td class="align-right">${fmtMoney(item.cost, item.currency)}</td>
        <td class="align-right">${fmtMoney(item.totalCost, item.currency)}</td>
        <td class="align-right">${liveText}</td>
        <td class="align-right">${fmtMoney(item.currentValue, item.currency)}</td>
        <td class="align-right">${pnlText}</td>
        <td class="align-right pct-cell"><b>${item.allocationPct.toFixed(2)}%</b><div class="pct-bar-track"><div class="pct-bar-fill" style="width:${Math.min(100, item.allocationPct).toFixed(2)}%;background:${item.color}"></div></div></td>
        <td><div class="row-actions"><button type="button" class="row-btn" data-edit="${esc(item.id)}">แก้ไข</button><button type="button" class="row-btn danger" data-delete="${esc(item.id)}">ลบ</button></div></td>
      </tr>`;
    }).join('');
  }

  async function loadMarketPrices() {
    const status = document.querySelector('#price-sync-status');
    try {
      const [stocksRes, cryptoRes] = await Promise.allSettled([
        fetch(`data/stocks.json?updated=${Date.now()}`, { cache: 'no-store' }),
        fetch(`data/crypto.json?updated=${Date.now()}`, { cache: 'no-store' }),
      ]);
      const nextMap = {};
      const nextCatalog = [];
      for (const res of [stocksRes, cryptoRes]) {
        if (res.status === 'fulfilled' && res.value.ok) {
          const snap = await res.value.json();
          for (const a of (snap.assets || [])) {
            const key = `${a.market}:${a.symbol}`;
            const cur = a.currency || (a.market === 'Thai' ? 'THB' : 'USD');
            if (Number.isFinite(a.price) && a.price > 0) {
              nextMap[key] = { price: a.price, name: a.name, currency: cur };
              if (!nextMap[a.symbol]) nextMap[a.symbol] = nextMap[key];
            }
            nextCatalog.push({ symbol: a.symbol, name: a.name, market: a.market, currency: cur });
          }
        }
      }
      priceMap = nextMap;
      catalog = nextCatalog;
      const datalist = document.querySelector('#asset-suggestions');
      if (datalist && catalog.length) {
        datalist.innerHTML = catalog.slice(0, 400).map((a) =>
          `<option value="${esc(a.symbol)}">${esc(a.name)} (${esc(a.market)})</option>`
        ).join('');
      }
      if (status) status.textContent = `ซิงก์ราคาตลาดแล้ว (${Object.keys(nextMap).length} รายการ)`;
    } catch {
      if (status) status.textContent = 'โหมดออฟไลน์ · ใช้ต้นทุนคำนวณสัดส่วน';
    }
    renderPortfolio();
  }

  const form = document.querySelector('#portfolio-form');
  const symbolInput = document.querySelector('#pf-symbol');
  const marketInput = document.querySelector('#pf-market');
  const currencyInput = document.querySelector('#pf-currency');
  const costInput = document.querySelector('#pf-cost');
  const qtyInput = document.querySelector('#pf-quantity');
  const errorEl = document.querySelector('#pf-error');
  const submitBtn = document.querySelector('#pf-submit');
  const cancelEditBtn = document.querySelector('#pf-cancel-edit');

  function resetForm() {
    editingId = null;
    form.reset();
    submitBtn.textContent = '+ เพิ่มเข้าพอร์ต';
    cancelEditBtn.hidden = true;
    errorEl.textContent = '';
  }

  symbolInput.addEventListener('input', () => {
    const sym = symbolInput.value.trim().toUpperCase();
    const match = catalog.find((c) => c.symbol === sym);
    if (match) {
      marketInput.value = match.market;
      currencyInput.value = match.currency;
    }
  });

  marketInput.addEventListener('change', () => {
    if (marketInput.value === 'Thai') currencyInput.value = 'THB';
    else if (marketInput.value === 'US' || marketInput.value === 'Crypto') currencyInput.value = 'USD';
  });

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    errorEl.textContent = '';
    try {
      const symbol = validateHoldingInput({
        symbol: symbolInput.value,
        cost: Number(costInput.value),
        quantity: Number(qtyInput.value),
      });
      const entry = {
        id: editingId || `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        symbol,
        market: marketInput.value,
        currency: currencyInput.value,
        cost: Number(costInput.value),
        quantity: Number(qtyInput.value),
      };
      if (editingId) {
        holdings = holdings.map((h) => (h.id === editingId ? entry : h));
      } else {
        holdings = [...holdings, entry];
      }
      saveJson(STORAGE_KEY, holdings);
      resetForm();
      renderPortfolio();
    } catch (err) {
      errorEl.textContent = err.message;
    }
  });

  cancelEditBtn.addEventListener('click', resetForm);

  document.querySelector('#portfolio-rows').addEventListener('click', (e) => {
    const editBtn = e.target.closest('[data-edit]');
    if (editBtn) {
      const item = holdings.find((h) => h.id === editBtn.dataset.edit);
      if (!item) return;
      editingId = item.id;
      symbolInput.value = item.symbol;
      marketInput.value = item.market;
      currencyInput.value = item.currency;
      costInput.value = item.cost;
      qtyInput.value = item.quantity;
      submitBtn.textContent = 'บันทึกการแก้ไข';
      cancelEditBtn.hidden = false;
      symbolInput.focus();
      return;
    }
    const delBtn = e.target.closest('[data-delete]');
    if (delBtn) {
      holdings = holdings.filter((h) => h.id !== delBtn.dataset.delete);
      saveJson(STORAGE_KEY, holdings);
      if (editingId === delBtn.dataset.delete) resetForm();
      renderPortfolio();
    }
  });

  const baseSelect = document.querySelector('#base-currency');
  const rateInput = document.querySelector('#usd-thb-rate');
  const weightSelect = document.querySelector('#weight-by');
  baseSelect.value = settings.baseCurrency;
  rateInput.value = settings.usdThbRate;
  weightSelect.value = settings.weightBy;

  for (const el of [baseSelect, rateInput, weightSelect]) {
    el.addEventListener('change', () => {
      settings = {
        baseCurrency: baseSelect.value,
        usdThbRate: Number(rateInput.value) > 0 ? Number(rateInput.value) : 34.5,
        weightBy: weightSelect.value,
      };
      saveJson(SETTINGS_KEY, settings);
      renderPortfolio();
    });
  }

  document.querySelector('#load-sample').addEventListener('click', () => {
    holdings = [
      { id: 'sample-1', symbol: 'PTT', market: 'Thai', currency: 'THB', cost: 32.5, quantity: 2000 },
      { id: 'sample-2', symbol: 'NVDA', market: 'US', currency: 'USD', cost: 118.0, quantity: 15 },
      { id: 'sample-3', symbol: 'BTC', market: 'Crypto', currency: 'USD', cost: 68000, quantity: 0.04 },
    ];
    saveJson(STORAGE_KEY, holdings);
    resetForm();
    renderPortfolio();
  });

  document.querySelector('#clear-portfolio').addEventListener('click', () => {
    holdings = [];
    saveJson(STORAGE_KEY, holdings);
    resetForm();
    renderPortfolio();
  });

  document.querySelector('#export-portfolio').addEventListener('click', () => {
    const blob = new Blob([JSON.stringify(holdings, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'marketscope-portfolio.json';
    a.click();
    URL.revokeObjectURL(url);
  });

  // Support pre-filling from Screener via ?symbol=...&market=...&currency=...
  const params = new URLSearchParams(window.location.search);
  if (params.get('symbol')) {
    symbolInput.value = params.get('symbol').toUpperCase();
    if (params.get('market')) marketInput.value = params.get('market');
    if (params.get('currency')) currencyInput.value = params.get('currency');
    costInput.focus();
  }

  renderPortfolio();
  loadMarketPrices();
}
