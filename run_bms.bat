@echo off
chcp 65001 >nul
REM ====================================================================
REM  仓控板 BMS 模拟器 - 一键启动脚本
REM  自动检测/安装 32 位 Python，用它来加载 32 位 ControlCAN.dll
REM ====================================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "MAIN_SCRIPT=%SCRIPT_DIR%bms_simulator.py"

if not exist "%MAIN_SCRIPT%" (
    echo [错误] 找不到 bms_simulator.py
    echo 当前目录: %SCRIPT_DIR%
    pause
    exit /b 1
)

REM --- 1. 先检查当前系统 Python 位数 ---
echo.
echo ===============================================
echo   仓控板 BMS 模拟器
echo ===============================================
echo.

for /f "tokens=*" %%B in ('python -c "import struct; print(struct.calcsize('P')*8)" 2^>nul') do set "CUR_BITS=%%B"
if "%CUR_BITS%"=="" (
    for /f "tokens=*" %%B in ('py -3 -c "import struct; print(struct.calcsize('P')*8)" 2^>nul') do set "CUR_BITS=%%B"
)

echo [检测] 当前默认 Python 位数: %CUR_BITS% 位
if "%CUR_BITS%"=="64" (
    echo [警告] 64 位 Python 无法加载 32 位的 ControlCAN.dll
    echo         需要 32 位 Python 才能正常使用 CANalyst-II 接口
    echo.
)

REM --- 2. 找 32 位 Python ---
set "PY32="

REM 先搜常见安装位置（含本脚本静默安装的默认位置）
for %%D in ("%LocalAppData%\Programs\Python\Python38-32" "C:\Python38-32" "C:\Python39-32" "C:\Python310-32" "C:\Python311-32" "C:\Python312-32") do (
    if exist "%%~D\python.exe" (
        for /f "tokens=*" %%B in ('"%%~D\python.exe" -c "import struct; print(struct.calcsize('P')*8)" 2^>nul') do set "BITS=%%B"
        if "!BITS!"=="32" (
            set "PY32=%%~D\python.exe"
            echo [找到] 32 位 Python: !PY32!
            goto :found
        )
    )
)

REM py launcher 可能注册了 -32
where /q py 2>nul
if %errorlevel%==0 (
    for /f "delims=" %%P in ('py -3 -c "import sys,struct; print(sys.executable if struct.calcsize('P')==4 else '')" 2^>nul') do (
        if not "%%P"=="" (
            set "PY32=%%P"
            echo [找到] 32 位 Python (通过 py launcher): !PY32!
            goto :found
        )
    )
    for /f "delims=" %%P in ('py -3.8-32 -c "import sys; print(sys.executable)" 2^>nul') do (
        if not "%%P"=="" (
            set "PY32=%%P"
            echo [找到] 32 位 Python 3.8-32: !PY32!
            goto :found
        )
    )
    for /f "delims=" %%P in ('py -3.11-32 -c "import sys; print(sys.executable)" 2^>nul') do (
        if not "%%P"=="" (
            set "PY32=%%P"
            echo [找到] 32 位 Python 3.11-32: !PY32!
            goto :found
        )
    )
)

if not "%PY32%"=="" goto :found

REM --- 2.5 同目录自带安装包 → 直接静默安装，无需联网 ---
if exist "%SCRIPT_DIR%python-3.8.10.exe" (
    echo [提示] 发现同目录的 python-3.8.10.exe，将静默安装 32 位 Python 3.8.10
    call "%SCRIPT_DIR%install_python38_32.bat" --auto
    goto :recheck
)

REM --- 3. 没找到 → 下载安装 ---
echo.
echo -----------------------------------------------
echo   未检测到 32 位 Python，需要先安装一份
echo -----------------------------------------------
echo.
echo 方案 A (推荐): 用 winget 自动安装 Python 3.11 (32-bit)
echo 方案 B: 浏览器打开 python.org 手动下载安装
echo.

choice /C AB /M "请选择安装方式"
if %errorlevel%==1 goto :try_winget
goto :manual_download

:try_winget
where /q winget 2>nul
if %errorlevel%==0 (
    echo.
    echo [安装] winget install Python.Python.3.11 （需用户确认）...
    winget install Python.Python.3.11 --architecture x86 --accept-source-agreements --accept-package-agreements
    if %errorlevel%==0 (
        echo.
        echo [安装完成] 正在刷新 PATH 并重新检测...
        goto :recheck
    ) else (
        echo [提示] winget 安装未成功，改为手动下载
        goto :manual_download
    )
) else (
    echo [提示] 系统没有 winget，改为手动下载
    goto :manual_download
)

:manual_download
echo.
echo [打开浏览器] 即将跳转 Python 官网 32 位下载页...
echo.
echo 下载地址: https://www.python.org/downloads/windows/
echo   → 选择 "Download Windows installer (32-bit)"
echo.
echo 安装时注意:
echo   - 安装路径可设为 C:\Python312-32（简单好记）
echo   - 勾选 "Add Python to PATH"
echo   - 安装完成后回到此窗口继续
echo.
start "" "https://www.python.org/downloads/windows/"
echo.
echo 安装完成后，按任意键继续检测...
pause >nul

:recheck
REM 刷新 PATH 后再试一轮
for /f "tokens=*" %%B in ('python -c "import struct; print(struct.calcsize('P')*8)" 2^>nul') do set "CUR_BITS=%%B"
if "%CUR_BITS%"=="32" (
    set "PY32=python"
    echo [检测] 当前 python 已经是 32 位了！
    goto :found
)
for %%D in ("%LocalAppData%\Programs\Python\Python38-32" "C:\Python312-32" "C:\Python311-32" "C:\Python310-32" "C:\Python39-32" "C:\Python38-32") do (
    if exist "%%~D\python.exe" (
        for /f "tokens=*" %%B in ('"%%~D\python.exe" -c "import struct; print(struct.calcsize('P')*8)" 2^>nul') do set "BITS=%%B"
        if "!BITS!"=="32" (
            set "PY32=%%~D\python.exe"
            echo [找到] 新安装的 32 位 Python: !PY32!
            goto :found
        )
    )
)

goto :manual_download

:found
echo.
echo -----------------------------------------------
echo   启动 BMS 模拟器
echo -----------------------------------------------
echo.
echo 解释器 : %PY32%
echo 脚本   : %MAIN_SCRIPT%
echo.

"%PY32%" "%MAIN_SCRIPT%"
if errorlevel 1 (
    echo.
    echo [错误] 脚本运行异常，退出码 %errorlevel%
    pause
)

endlocal
