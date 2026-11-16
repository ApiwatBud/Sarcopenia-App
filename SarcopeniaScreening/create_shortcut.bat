@echo off
rem create_shortcut.bat — สร้าง shortcut "Sarcopenia Screening" (มีไอคอนของโปรแกรม) บน Desktop และ Start Menu
rem   setup.bat เรียกไฟล์นี้ให้อัตโนมัติ — ดับเบิลคลิกเองเมื่อ shortcut หาย หรือย้ายโฟลเดอร์โปรแกรม
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo ยังไม่ได้ติดตั้ง — ดับเบิลคลิก setup.bat ก่อน
    if /i not "%~1"=="nopause" pause
    exit /b 1
)
set "SC_APPDIR=%CD%"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$a = $env:SC_APPDIR; $sh = New-Object -ComObject WScript.Shell;" ^
  "foreach ($d in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {" ^
  "  $s = $sh.CreateShortcut((Join-Path $d 'Sarcopenia Screening.lnk'));" ^
  "  $s.TargetPath = (Join-Path $a '.venv\Scripts\pythonw.exe'); $s.Arguments = 'run_app.py';" ^
  "  $s.WorkingDirectory = $a; $s.IconLocation = (Join-Path $a 'app\assets\icon.ico') + ',0';" ^
  "  $s.Description = 'Sarcopenia Screening'; $s.Save(); Write-Host ('Shortcut: ' + $s.FullName) }"
set "RC=%errorlevel%"
if /i not "%~1"=="nopause" pause
exit /b %RC%
