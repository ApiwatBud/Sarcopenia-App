@echo off
rem run_app.bat — เปิดโปรแกรม (ใช้ Python ใน .venv ของโฟลเดอร์นี้, ไม่มีหน้าต่างดำค้าง)
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo ยังไม่ได้ติดตั้ง — ดับเบิลคลิก setup.bat ก่อน
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" run_app.py
