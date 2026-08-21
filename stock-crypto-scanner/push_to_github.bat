@echo off
chcp 65001 > nul
echo ===================================================
echo   กำลังส่งโค้ดขึ้น GitHub: benzsutthi/stock-crypto-scanner
echo ===================================================
cd /d "%~dp0"
git remote remove origin >nul 2>&1
git remote add origin https://github.com/benzsutthi/stock-crypto-scanner.git
git branch -M main
git push -u origin main
echo ===================================================
echo   เสร็จสิ้น! หากสำเร็จสามารถปิดหน้านี้ได้เลยครับ
echo ===================================================
pause
