@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 國語字音字形數位學習系統 - 本地伺服器
echo ========================================================
echo   國語字音字形數位學習系統 - 本地伺服器啟動中...
echo ========================================================
echo.
echo 正在啟動伺服器並開啟瀏覽器...
start http://localhost:8000/dispute.html
echo 伺服器已於 http://localhost:8000 運行
echo 如欲停止伺服器，請直接關閉此視窗或按下 Ctrl + C。
echo ========================================================
echo.
python server.py 8000
if errorlevel 1 (
    echo Python 啟動失敗，嘗試 py -3...
    py -3 server.py 8000
)
pause
