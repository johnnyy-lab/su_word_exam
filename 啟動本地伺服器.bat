@echo off
chcp 65001 > nul
title 國語字音字形數位學習系統 - 本地伺服器

echo ========================================================
echo   國語字音字形數位學習系統 - 本地伺服器啟動中...
echo ========================================================
echo.

:: 檢查 python 指令是否存在
python --version > nul 2>&1
if errorlevel 1 (
    echo [錯誤] 找不到 Python 環境！請確認已安裝 Python 並將其加入系統 PATH。
    echo.
    pause
    exit /b 1
)

:: 自動在預設瀏覽器中開啟爭議字維護頁面
start http://localhost:8000/dispute.html

echo [成功] 本地伺服器已在 http://localhost:8000 啟動！
echo.
echo   - 爭議字審查維護系統: http://localhost:8000/dispute.html
echo   - 主學習系統入口:     http://localhost:8000/index.html
echo.
echo 提示：
echo   1. 請保持此黑底視窗開啟，以維持本地伺服器運作。
echo   2. 在網頁上修改完成後點擊「確認修改」，系統將直接改寫檔案並重新驗證！
echo   3. 如欲停止伺服器，請直接關閉此視窗或按下 Ctrl + C。
echo ========================================================
echo.

python server.py 8000
pause
