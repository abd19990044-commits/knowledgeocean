@echo off
chcp 65001 >nul
title محيط المعرفة — أداة قفل وحقن الوسيط العتادي (CD / DVD / FLASH)
cls
echo ======================================================================
echo    محيط المعرفة — تشغيل أداة قفل وتشفير المثبت العتادي
echo ======================================================================
echo.

where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3.12 bind_media.py %*
    goto :end
)

where python >nul 2>nul
if %errorlevel% equ 0 (
    python bind_media.py %*
    goto :end
)

echo [X] تعذر العثور على مفسر بايثون (Python). يرجى التأكد من تثبيت Python 3.
pause
exit /b 1

:end
echo.
pause
