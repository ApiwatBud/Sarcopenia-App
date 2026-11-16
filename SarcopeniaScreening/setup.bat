@echo off
rem ============================================================================
rem setup.bat — ติดตั้งโปรแกรมบนเครื่องใหม่ (รันในโฟลเดอร์ที่ git clone มา, ไม่ต้องมีสิทธิ์ admin)
rem   1) ติดตั้ง Python 3.11 (ถ้ายังไม่มี)
rem   2) สร้าง virtual environment (.venv) ในโฟลเดอร์นี้ + ติดตั้งไลบรารีตาม requirements-runtime.txt
rem   3) ทดสอบโปรแกรม (selftest)
rem   4) สร้าง shortcut "Sarcopenia Screening" บน Desktop และ Start Menu
rem   ฐานข้อมูล: SQLite มากับ Python — สร้างอัตโนมัติตอนเปิดโปรแกรมครั้งแรก
rem   ต้องต่ออินเทอร์เน็ตระหว่างติดตั้ง (ครั้งเดียว)
rem ============================================================================
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "VPY=%CD%\.venv\Scripts\python.exe"

if not exist "app\models\y3.joblib" (
    echo ไม่พบไฟล์โมเดล app\models\y3.joblib — clone ไม่ครบ
    goto :fail
)

rem ---------------------------------------------------------------- 1) Python 3.11
echo [1/4] ตรวจ Python 3.11
set "PY="
py -3.11 -c "import sys" >nul 2>&1 && set "PY=py -3.11"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY="%LOCALAPPDATA%\Programs\Python\Python311\python.exe""
if not defined PY (
    echo      ไม่พบ Python 3.11 — กำลังติดตั้งด้วย winget
    winget install -e --id Python.Python.3.11 --scope user --silent --accept-package-agreements --accept-source-agreements
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY="%LOCALAPPDATA%\Programs\Python\Python311\python.exe""
)
if not defined PY (
    echo      ติดตั้ง Python อัตโนมัติไม่สำเร็จ
    echo      ดาวน์โหลด Python 3.11 ^(Windows installer 64-bit^) จาก https://www.python.org/downloads/
    echo      ติดตั้งแล้วรัน setup.bat ใหม่
    goto :fail
)
echo      ใช้ %PY%

rem ---------------------------------------------------------------- 2) .venv + ไลบรารี
echo [2/4] สร้าง .venv และติดตั้งไลบรารี (ใช้เวลาหลายนาที)
if not exist "%VPY%" %PY% -m venv .venv || goto :fail
"%VPY%" -m pip install --upgrade pip -q || goto :fail
"%VPY%" -m pip install -r requirements-runtime.txt -q || goto :fail

rem ---------------------------------------------------------------- 3) ทดสอบ
echo [3/4] ทดสอบโปรแกรม
"%VPY%" run_app.py --selftest "%CD%\selftest.txt"
type selftest.txt
findstr /c:"SELFTEST PASS" selftest.txt >nul || goto :fail

rem ---------------------------------------------------------------- 4) shortcut
echo [4/4] สร้าง shortcut
call create_shortcut.bat nopause || goto :fail

echo.
echo ติดตั้งเสร็จ — เปิดโปรแกรมจาก shortcut "Sarcopenia Screening" หรือ run_app.bat
echo เปิดครั้งแรกจะให้สร้างบัญชีผู้ดูแล (admin)
pause
exit /b 0

:fail
echo.
echo ติดตั้งไม่สำเร็จ — ถ่ายภาพหน้าจอนี้ส่งให้ผู้ดูแลโปรแกรม
pause
exit /b 1
