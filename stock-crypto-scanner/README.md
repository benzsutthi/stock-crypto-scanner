# 📈 ระบบสแกนหุ้นและคริปโต แจ้งเตือนผ่าน LINE อัตโนมัติ

ระบบค้นหาหุ้นสหรัฐฯ (US Stocks), หุ้นไทย (SET) และคริปโตเคอร์เรนซี (Crypto) ที่มีสัญญาณเทคนิคอลโดดเด่น และส่งข้อความสรุปเข้า LINE Official Account ผ่าน Broadcast API

---

## 📁 โครงสร้างไฟล์
- `config.py`: ตั้งค่า Token และรายชื่อหุ้น/เหรียญคริปโตที่ต้องการสแกน
- `scanner.py`: คำนวณอินดิเคเตอร์ (EMA, RSI, MACD, Volume Spike, Breakout)
- `line_notifier.py`: จัดรูปแบบรายงานและส่งข้อความ Broadcast เข้า LINE
- `main.py`: ไฟล์หลักสำหรับเริ่มสแกนและส่งผลลัพธ์
- `run_scanner.bat`: ดับเบิ้ลคลิกเพื่อรันบน Windows ได้ทันที

---

## 🚀 วิธีเปิดใช้งาน

### 1. รันแบบทันที (Manual)
- ดับเบิ้ลคลิกที่ไฟล์ **`run_scanner.bat`** 
- หรือเปิด Terminal แล้วพิมพ์:
  ```bash
  python main.py
  ```

---

## ⏰ วิธีตั้งเวลาให้รันอัตโนมัติทุกวัน (Windows Task Scheduler)

1. กดปุ่ม `Windows + S` ค้นหา **Task Scheduler** แล้วเปิดขึ้นมา
2. คลิกที่เมนูด้านขวา **Create Basic Task...**
3. ตั้งชื่อ Task เช่น `Daily Stock Crypto Scanner` แล้วกด Next
4. เลือกความถี่เป็น **Daily** (ทุกวัน) แล้วตั้งเวลาที่ต้องการ (เช่น 08:30 น. ก่อนตลาดเปิด หรือ 18:00 น. หลังตลาดปิด)
5. ในขั้นตอน Action เลือก **Start a program**
   - ช่อง **Program/script**: เลือกไปที่ไฟล์ `run_scanner.bat` 
   - เช่น `C:\Users\User_Win10x64\Desktop\skill\stock-crypto-scanner\run_scanner.bat`
   - ช่อง **Start in (optional)**: ใส่โฟลเดอร์ `C:\Users\User_Win10x64\Desktop\skill\stock-crypto-scanner`
6. กด Finish ระบบจะรันและส่ง LINE ให้คุณอัตโนมัติทุกวัน

---

## ⚙️ การเพิ่ม/ลด รายชื่อหุ้นและคริปโต
เปิดไฟล์ `config.py` เพื่อเพิ่มหรือแก้ไขชื่อหุ้นได้ตามต้องการ:
- **หุ้นไทย**: ต้องลงท้ายด้วย `.BK` เช่น `"CPALL.BK"`, `"PTT.BK"`
- **หุ้นสหรัฐฯ**: ใส่ตัวย่อ Ticker เช่น `"NVDA"`, `"TSLA"`, `"AAPL"`
- **คริปโต**: ใส่คู่เหรียญ USD เช่น `"BTC-USD"`, `"ETH-USD"`, `"SOL-USD"`
