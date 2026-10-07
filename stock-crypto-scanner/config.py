# config.py
import os
from dotenv import load_dotenv

load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

# การตั้งค่าการสแกน
MAX_PICKS_PER_CATEGORY = 3       # จำนวนตัวเลือกเด่นที่สุดที่จะส่งเข้า LINE ต่อหมวด (Top 3)
USE_DYNAMIC_BINANCE = True       # ดึงเหรียญคริปโตแบบ Dynamic Real-time จาก Binance
BINANCE_MIN_VOL_USD = 8000000    # กรองเฉพาะเหรียญที่มี Volume ซื้อขาย 24 ชม. เกิน 8 ล้านดอลลาร์
CRYPTO_TOP_LIMIT = 150           # จำนวนคริปโทในหน้าเว็บ จัดอันดับตาม Market Cap
BINANCE_TOP_LIMIT = CRYPTO_TOP_LIMIT  # จำนวนเหรียญสูงสุดของสแกนเนอร์ Binance

# รายชื่อหุ้น/ETF ที่จดทะเบียนในสหรัฐ 200 ticker (curated universe ไม่ใช่อันดับ Market Cap)
US_STOCKS = [
    # Mega Cap Tech & AI
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "AMD", "PLTR",
    "NFLX", "ORCL", "ADBE", "CRM", "INTC", "QCOM", "TXN", "AMAT", "MU", "LRCX",
    "KLAC", "MRVL", "ARM", "SMCI", "ASML", "TSM", "BABA", "PDD", "BIDU", "JD",
    # Crypto / FinTech / High Growth
    "COIN", "MSTR", "MARA", "RIOT", "HOOD", "XYZ", "PYPL", "V", "MA", "AXP",
    "SHOP", "UBER", "ABNB", "DASH", "SNOW", "DDOG", "NET", "CRWD", "PANW", "ZS",
    # EV / Clean Tech / Industrials
    "RIVN", "LCID", "NIO", "LI", "XPEV", "CAT", "DE", "BA", "GE", "LMT",
    # Healthcare & Pharma
    "LLY", "NVO", "JNJ", "UNH", "PFE", "MRK", "ABBV", "ISRG", "VRTX", "REGN",
    # Consumer / Retail / Media
    "WMT", "COST", "TGT", "HD", "NKE", "SBUX", "MCD", "DIS", "SPOT", "ROKU",
    # Financials & Energy
    "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "XOM", "CVX", "COP",
    # Index & Major ETFs
    "SPY", "QQQ", "IWM", "DIA", "SMH", "SOXX", "ARKK", "XLF", "XLE", "XLK",
    # Enterprise software, semiconductor & cybersecurity
    "CSCO", "IBM", "NOW", "INTU", "ACN", "CDNS", "SNPS", "ADI", "NXPI", "MCHP",
    "ON", "MPWR", "DELL", "HPE", "HPQ", "WDAY", "TEAM", "MDB", "HUBS", "FTNT",
    # Banks, capital markets & insurance
    "BRK-B", "SCHW", "USB", "PNC", "TFC", "MET", "STT", "NTRS", "CME", "ICE",
    "SPGI", "MCO", "MSCI", "AON", "MRSH", "AJG", "PGR", "TRV", "ALL", "AIG",
    # Healthcare, medical equipment & pharmaceuticals
    "ABT", "AMGN", "GILD", "BMY", "TMO", "DHR", "MDT", "BSX", "SYK", "CVS",
    # Aerospace, transport, industrials & infrastructure
    "RTX", "NOC", "GD", "HON", "UNP", "UPS", "FDX", "WM", "RSG", "ETN",
    "PH", "ITW", "MMM", "EMR", "JCI", "CMI", "PCAR", "ROK", "OTIS", "CARR",
    # Consumer staples & retail
    "KO", "PEP", "PG", "CL", "KMB", "MDLZ", "GIS", "KHC", "LOW", "TJX",
    # Utilities & real estate
    "NEE", "DUK", "SO", "AEP", "SRE", "D", "AMT", "PLD", "EQIX", "O",
    # Energy, mining & materials
    "SLB", "EOG", "OXY", "MPC", "PSX", "VLO", "FCX", "NEM", "NUE", "LIN"
]

# รายชื่อหุ้นไทย SET100 ครบเซ็ต (Thai SET100 Tickers)
THAI_STOCKS = [
    "AAV.BK", "ADVANC.BK", "AMATA.BK", "AOT.BK", "AP.BK", "AWC.BK", "BAM.BK", "BANPU.BK",
    "BBL.BK", "BCH.BK", "BCP.BK", "BCPG.BK", "BDMS.BK", "BEM.BK", "BGRIM.BK", "BH.BK",
    "BJC.BK", "BLA.BK", "BTG.BK", "BTS.BK", "CBG.BK", "CCET.BK", "CENTEL.BK",
    "CHG.BK", "CK.BK", "CKP.BK", "COM7.BK", "CPALL.BK", "CPF.BK", "CPN.BK", "CRC.BK",
    "DELTA.BK", "DOHOME.BK", "EA.BK", "EGCO.BK", "ERW.BK", "GLOBAL.BK", "GPSC.BK", "GULF.BK",
    "GUNKUL.BK", "HANA.BK", "HMPRO.BK", "ICHI.BK", "ITC.BK", "IVL.BK", "JAS.BK",
    "JMART.BK", "JMT.BK", "KBANK.BK", "KCE.BK", "KKP.BK", "KTB.BK", "KTC.BK", "LH.BK",
    "M.BK", "MAJOR.BK", "MASTER.BK", "MBK.BK", "MEGA.BK", "MINT.BK", "MOSHI.BK", "MTC.BK",
    "OR.BK", "OSP.BK", "PLANB.BK", "PR9.BK", "PRM.BK", "PTG.BK", "PTL.BK", "PTT.BK",
    "PTTEP.BK", "PTTGC.BK", "QH.BK", "RATCH.BK", "RBF.BK", "RCL.BK", "SAPPE.BK", "SAWAD.BK",
    "SCB.BK", "SCC.BK", "SCGP.BK", "SIRI.BK", "SISB.BK", "SJWD.BK", "SPALI.BK", "SPRC.BK",
    "STA.BK", "STECON.BK", "TASCO.BK", "TCAP.BK", "THANI.BK", "THCOM.BK", "TIDLOR.BK", "TISCO.BK",
    "TLI.BK", "TOP.BK", "TRUE.BK", "TTB.BK", "TU.BK", "VGI.BK", "WHA.BK"
]

# รายชื่อเหรียญคริปโตสำรอง (Fallback Crypto List กรณีต่อ API ไม่ได้)
CRYPTO_LIST = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "DOGE-USD", "ADA-USD",
    "AVAX-USD", "LINK-USD", "SUI-USD", "NEAR-USD", "RENDER-USD", "SHIB-USD", "PEPE-USD",
    "DOT-USD", "ATOM-USD", "APT-USD", "TAO-USD", "INJ-USD", "FET-USD", "ENA-USD", "UNI-USD"
]
