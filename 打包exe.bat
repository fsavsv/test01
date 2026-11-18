@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 python，请先安装 Python 3.10 及以上版本，安装时勾选 "Add Python to PATH"
    pause
    exit /b 1
)

echo [1/3] 安装依赖...
python -m pip install --upgrade pip
python -m pip install pyinstaller pandas openpyxl requests
if errorlevel 1 goto fail

echo [2/3] 打包中，首次打包约需 1-3 分钟...
python -m PyInstaller --noconfirm --clean --onefile --name "设备升级工具" green_tool.py
if errorlevel 1 goto fail

echo [3/3] 打包完成
echo.
echo 生成文件: %cd%\dist\设备升级工具.exe
echo 使用前请把 原始数据.xlsx 和 京东320台样柜电柜号^&ZL编码信息_20260817^(1^).xlsx 放到 exe 同目录。
pause
exit /b 0

:fail
echo.
echo [失败] 打包过程出错，请把上面的报错信息发给开发人员。
pause
exit /b 1
