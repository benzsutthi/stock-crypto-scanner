# config.py
import os
from dotenv import load_dotenv

load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv(
    "LINE_CHANNEL_ACCESS_TOKEN", 
    "F1+rOyHfN+u/c6jLTBvlMlLhFYkIaa8Uit7iSeriOYEl39/K7QHulG4Ya6IWqzgzeNg0zcNhQ4LzeU3GAboJbTmn0c39Q/E+YltCsD3H7bF/Ae4YZ4tKvQ5ZkmCYedcQac2XEe/3Zlq+DVYyyPylQgdB04t89/1O/w1cDnyilFU="
)

# รายชื่อสินทรัพย์ที่ต้องการสแกน
# หุ้นสหรัฐฯ ยอดนิยม (US Stocks)
US_STOCKS = [
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "AMD", "PLTR", "COIN",
    "NFLX", "AVGO", "SMCI", "QCOM", "ARM", "INTC", "TSM", "BABA"
]

# หุ้นไทยยอดนิยม (Thai SET Top Stocks)
THAI_STOCKS = [
    "DELTA.BK", "PTT.BK", "AOT.BK", "CPALL.BK", "ADVANC.BK", "GULF.BK", "KBANK.BK",
    "SCB.BK", "BDMS.BK", "BBL.BK", "TRUE.BK", "KTB.BK", "CRC.BK", "MINT.BK", "CPN.BK",
    "WHA.BK", "BH.BK", "HMPRO.BK", "TOP.BK", "EA.BK"
]

# คริปโตยอดนิยม (Crypto Major & Trending)
CRYPTO_LIST = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "DOGE-USD", "ADA-USD",
    "AVAX-USD", "LINK-USD", "NEAR-USD", "RENDER-USD", "SHIB-USD", "DOT-USD", "ATOM-USD"
]
