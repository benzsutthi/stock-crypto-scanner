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
    const quoteMatchesCurrency = quote && (!quote.currency || quote.currency === currency || (quote.currency === 'USD' && currency === 'USDT'));
    const liveFromSnapshot = quoteMatchesCurrency && Number.isFinite(quote.price) && quote.price > 0 ? quote.price : null;
    const sheetPrice = Number.isFinite(Number(h.sheetPrice)) && Number(h.sheetPrice) > 0 ? Number(h.sheetPrice) : null;
    const marketPrice = liveFromSnapshot ?? sheetPrice;
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

function parseGoogleSheetUrl(inputUrl) {
  const raw = String(inputUrl || '').trim();
  const idMatch = raw.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
  if (!idMatch) throw new Error('ลิงก์ Google Sheets ไม่ถูกต้อง');
  const gidMatch = raw.match(/[?#&]gid=(\d+)/);
  const gid = gidMatch ? gidMatch[1] : '0';
  return `https://docs.google.com/spreadsheets/d/${idMatch[1]}/gviz/tq?tqx=out:csv&gid=${gid}`;
}

function parseCsvRows(text) {
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"' && text[i + 1] === '"') {
        field += '"';
        i++;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ',') {
      row.push(field.trim());
      field = '';
    } else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i++;
      row.push(field.trim());
      if (row.some((c) => c !== '')) rows.push(row);
      row = [];
      field = '';
    } else {
      field += ch;
    }
  }
  if (field !== '' || row.length) {
    row.push(field.trim());
    if (row.some((c) => c !== '')) rows.push(row);
  }
  return rows;
}

function parseNum(val) {
  if (val === undefined || val === null || val === '') return NaN;
  const n = Number(String(val).replace(/[,$\s฿]/g, ''));
  return Number.isFinite(n) ? n : NaN;
}

function parsePortfolioCsv(csvText) {
  const rows = parseCsvRows(csvText);
  if (rows.length < 2) throw new Error('ไม่พบข้อมูลใน Google Sheets');
  const headers = rows[0].map((h) => h.toLowerCase());
  const idx = {
    ticker: headers.findIndex((h) => h.includes('ticker') || h.includes('symbol')),
    assetClass: headers.findIndex((h) => h.includes('asset class') || h.includes('market')),
    qty: headers.findIndex((h) => h.includes('shares') || h.includes('units') || h.includes('qty') || h.includes('quantity')),
    cost: headers.findIndex((h) => h.includes('avg invest') || h.includes('cost')),
    price: headers.findIndex((h) => h.includes('current price') || h === 'price'),
    valueThb: headers.findIndex((h) => h.includes('current value thb')),
    costThb: headers.findIndex((h) => h.includes('total invest costthb') || h.includes('costthb')),
  };
  if (idx.ticker === -1 || idx.qty === -1 || idx.cost === -1) {
    throw new Error('ไม่พบคอลัมน์ Ticker, Shares/Units หรือ avg invest ในชีต');
  }

  const parsed = [];
  const inferredRates = [];

  for (let r = 1; r < rows.length; r++) {
    const cols = rows[r];
    const rawTicker = (cols[idx.ticker] || '').trim();
    if (!rawTicker) continue;

    const quantity = parseNum(cols[idx.qty]);
    const cost = parseNum(cols[idx.cost]);
    if (!Number.isFinite(quantity) || quantity <= 0 || !Number.isFinite(cost) || cost <= 0) continue;

    const assetClass = idx.assetClass >= 0 ? (cols[idx.assetClass] || '').trim() : '';
    const sheetPrice = idx.price >= 0 ? parseNum(cols[idx.price]) : NaN;
    const valueThb = idx.valueThb >= 0 ? parseNum(cols[idx.valueThb]) : NaN;
    const costThb = idx.costThb >= 0 ? parseNum(cols[idx.costThb]) : NaN;

    let market = 'Other';
    let currency = 'THB';
    let symbol = rawTicker.toUpperCase();

    if (/us/i.test(assetClass) || /\s+US$/i.test(rawTicker)) {
      market = 'US';
      currency = 'USD';
      symbol = symbol.replace(/\s+US$/i, '').trim();
    } else if (/th/i.test(assetClass)) {
      market = /fund/i.test(assetClass) ? 'Other' : 'Thai';
      currency = 'THB';
    } else if (/crypto/i.test(assetClass)) {
      market = 'Crypto';
      if (symbol.endsWith('THB') && symbol.length > 3) {
        currency = 'THB';
      } else if (Number.isFinite(valueThb) && Number.isFinite(sheetPrice) && sheetPrice > 0) {
        const ratio = valueThb / (quantity * sheetPrice);
        currency = ratio > 15 ? 'USD' : 'THB';
      } else if (Number.isFinite(costThb) && costThb > 0) {
        const ratio = costThb / (quantity * cost);
        currency = ratio > 15 ? 'USD' : 'THB';
      }
    }

    if (currency === 'USD' && Number.isFinite(costThb) && costThb > 0) {
      const rate = costThb / (quantity * cost);
      if (rate > 20 && rate < 60) inferredRates.push(rate);
    }

    parsed.push({
      id: `gs-${r}-${symbol}`,
      symbol,
      name: assetClass ? `${rawTicker} · ${assetClass}` : rawTicker,
      market,
      currency,
      cost,
      quantity,
      sheetPrice: Number.isFinite(sheetPrice) && sheetPrice > 0 ? sheetPrice : null,
    });
  }

  const usdThbRate = inferredRates.length
    ? Number((inferredRates.reduce((a, b) => a + b, 0) / inferredRates.length).toFixed(2))
    : null;

  return { holdings: parsed, inferredUsdThbRate: usdThbRate };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    calculatePortfolio,
    validateHoldingInput,
    toBaseCurrency,
    parseGoogleSheetUrl,
    parseCsvRows,
    parsePortfolioCsv,
  };
}

if (typeof document !== 'undefined') {
  const STORAGE_KEY = 'ms-portfolio-holdings';
  const SETTINGS_KEY = 'ms-portfolio-settings';
  const SHEET_URL_KEY = 'ms-portfolio-gsheet-url';
  const SHEET_AUTO_KEY = 'ms-portfolio-gsheet-auto';
  const loadJson = (k, fallback) => { try { return JSON.parse(localStorage.getItem(k)) ?? fallback; } catch { return fallback; } };
  const saveJson = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} };

  let holdings = loadJson(STORAGE_KEY, []);
  let settings = loadJson(SETTINGS_KEY, { baseCurrency: 'THB', usdThbRate: 34.5, weightBy: 'value', privacyMode: false });
  let sheetConfig = loadJson(SHEET_AUTO_KEY, { enabled: true, intervalMs: 300000 });
  let priceMap = {};
  let catalog = [];
  let editingId = null;

  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmtMoney = (n, currency = 'THB') => {
    if (!Number.isFinite(n)) return '—';
    if (settings.privacyMode) return currency === 'THB' ? '฿••••••' : '$••••••';
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
  const fmtQty = (n) => (settings.privacyMode ? '••••' : new Intl.NumberFormat('en-US', { maximumFractionDigits: 8 }).format(n));

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
      tbody.innerHTML = '<tr><td colspan="9" class="loading-row">ยังไม่มีรายการในพอร์ต · วางลิงก์ Google Sheets ด้านบนแล้วกดซิงก์ได้เลย</td></tr>';
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

  const baseSelect = document.querySelector('#base-currency');
  const rateInput = document.querySelector('#usd-thb-rate');
  const weightSelect = document.querySelector('#weight-by');
  const privacyToggleBtn = document.querySelector('#toggle-privacy');
  baseSelect.value = settings.baseCurrency;
  rateInput.value = settings.usdThbRate;
  weightSelect.value = settings.weightBy;

  function updatePrivacyButton() {
    if (!privacyToggleBtn) return;
    privacyToggleBtn.textContent = settings.privacyMode ? '👁 แสดงยอดเงิน' : '🙈 ซ่อนยอดเงิน';
    privacyToggleBtn.setAttribute('aria-pressed', String(Boolean(settings.privacyMode)));
  }
  updatePrivacyButton();

  privacyToggleBtn?.addEventListener('click', () => {
    settings.privacyMode = !settings.privacyMode;
    saveJson(SETTINGS_KEY, settings);
    updatePrivacyButton();
    renderPortfolio();
  });

  for (const el of [baseSelect, rateInput, weightSelect]) {
    el.addEventListener('change', () => {
      settings = {
        ...settings,
        baseCurrency: baseSelect.value,
        usdThbRate: Number(rateInput.value) > 0 ? Number(rateInput.value) : 34.5,
        weightBy: weightSelect.value,
      };
      saveJson(SETTINGS_KEY, settings);
      renderPortfolio();
    });
  }

  document.querySelector('#clear-portfolio').addEventListener('click', () => {
    holdings = [];
    try {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(SHEET_URL_KEY);
      localStorage.removeItem(SHEET_AUTO_KEY);
    } catch {}
    if (sheetUrlInput) sheetUrlInput.value = '';
    if (sheetStatus) sheetStatus.textContent = 'ล้างข้อมูลพอร์ตและลิงก์ส่วนตัวในเบราว์เซอร์แล้ว';
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

  const sheetUrlInput = document.querySelector('#gsheet-url');
  const sheetStatus = document.querySelector('#gsheet-status');
  const syncSheetBtn = document.querySelector('#sync-gsheet');
  const sheetAutoCheck = document.querySelector('#gsheet-auto');
  const sheetIntervalSelect = document.querySelector('#gsheet-interval');

  if (sheetUrlInput) {
    sheetUrlInput.value = loadJson(SHEET_URL_KEY, '');
  }
  if (sheetAutoCheck) sheetAutoCheck.checked = Boolean(sheetConfig.enabled);
  if (sheetIntervalSelect) sheetIntervalSelect.value = String(sheetConfig.intervalMs || 300000);

  let sheetSyncInFlight = null;
  let lastSheetSyncAt = 0;
  let sheetTimer = null;

  async function syncFromGoogleSheet() {
    if (!sheetUrlInput || !syncSheetBtn) return;
    if (sheetSyncInFlight) return sheetSyncInFlight;
    const rawUrl = sheetUrlInput.value.trim();
    if (!rawUrl) {
      if (sheetStatus) sheetStatus.textContent = 'กรุณาวางลิงก์ Google Sheets ของคุณ (เก็บเฉพาะในเบราว์เซอร์นี้)';
      return;
    }
    syncSheetBtn.disabled = true;
    if (sheetStatus) sheetStatus.textContent = 'กำลังดึงข้อมูลจาก Google Sheets...';
    sheetSyncInFlight = (async () => {
      try {
        const csvUrl = parseGoogleSheetUrl(rawUrl);
        saveJson(SHEET_URL_KEY, rawUrl);
        const response = await fetch(csvUrl, { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status} (ตรวจสอบว่าเปิดแชร์ลิงก์แบบ Anyone with the link)`);
        const csvText = await response.text();
        const { holdings: imported, inferredUsdThbRate } = parsePortfolioCsv(csvText);
        if (!imported.length) throw new Error('ไม่พบรายการที่มีจำนวนและต้นทุน > 0');
        holdings = imported;
        saveJson(STORAGE_KEY, holdings);
        if (inferredUsdThbRate) {
          settings.usdThbRate = inferredUsdThbRate;
          rateInput.value = inferredUsdThbRate;
          saveJson(SETTINGS_KEY, settings);
        }
        lastSheetSyncAt = Date.now();
        renderPortfolio();
        const nextMins = Math.round((sheetConfig.intervalMs || 300000) / 60000);
        if (sheetStatus) {
          sheetStatus.textContent = `ซิงก์สำเร็จ ${imported.length} สินทรัพย์ (${new Date().toLocaleTimeString('th-TH')})${sheetConfig.enabled ? ` · รีเฟรชอัตโนมัติทุก ${nextMins} นาที` : ''}`;
        }
      } catch (err) {
        if (sheetStatus) sheetStatus.textContent = `ดึงข้อมูลไม่สำเร็จ: ${err.message}`;
      } finally {
        syncSheetBtn.disabled = false;
        sheetSyncInFlight = null;
      }
    })();
    return sheetSyncInFlight;
  }

  function scheduleSheetRefresh() {
    if (sheetTimer) clearInterval(sheetTimer);
    sheetTimer = null;
    if (!sheetConfig.enabled || !sheetUrlInput?.value.trim()) return;
    const interval = Number(sheetConfig.intervalMs) || 300000;
    sheetTimer = setInterval(() => {
      if (document.visibilityState === 'visible' && navigator.onLine !== false) {
        syncFromGoogleSheet();
      }
    }, interval);
  }

  function saveSheetConfig() {
    sheetConfig = {
      enabled: Boolean(sheetAutoCheck?.checked),
      intervalMs: Number(sheetIntervalSelect?.value) || 300000,
    };
    saveJson(SHEET_AUTO_KEY, sheetConfig);
    scheduleSheetRefresh();
  }

  syncSheetBtn?.addEventListener('click', () => {
    syncFromGoogleSheet();
    scheduleSheetRefresh();
  });
  sheetAutoCheck?.addEventListener('change', saveSheetConfig);
  sheetIntervalSelect?.addEventListener('change', saveSheetConfig);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && sheetConfig.enabled && sheetUrlInput?.value.trim()) {
      if (Date.now() - lastSheetSyncAt >= (Number(sheetConfig.intervalMs) || 300000)) {
        syncFromGoogleSheet();
      }
    }
  });

  renderPortfolio();
  loadMarketPrices();
  if (sheetConfig.enabled && sheetUrlInput?.value.trim()) {
    syncFromGoogleSheet();
    scheduleSheetRefresh();
  }
}
