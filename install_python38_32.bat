@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ====================================================================
REM  一键安装 32 位 Python 3.8.10（用于加载 32 位 ControlCAN.dll）
REM  需要同目录下存在 python-3.8.10.exe
REM ====================================================================

set "SCRIPT_DIR=%~dp0"
set "INSTALLER=%SCRIPT_DIR%python-3.8.10.exe"
set "TARGET_DIR=%LocalAppData%\Programs\Python\Python38-32"
set "AUTO=0"
if "%~1"=="--auto" set "AUTO=1"

echo.
echo ===============================================
echo   安装 32 位 Python 3.8.10
echo ===============================================
echo.

if not exist "%INSTALLER%" (
    echo [错误] 同目录下找不到 python-3.8.10.exe
    echo 请把安装包和本脚本放在同一文件夹后再运行。
    if "!AUTO!"=="0" pause
    exit /b 1
)

REM 已安装则跳过安装，直接复用
if exist "%TARGET_DIR%\python.exe" (
    for /f "tokens=*" %%B in ('"%TARGET_DIR%\python.exe" -c "import struct;print(struct.calcsize('P')*8)" 2^>nul') do set "EXIST_BITS=%%B"
    if "!EXIST_BITS!"=="32" (
        echo [跳过] 已检测到 32 位 Python：%TARGET_DIR%\python.exe
        goto :configure
    )
)

echo [1/3] 静默安装到：%TARGET_DIR%
echo        （按用户安装，无需管理员权限）

"%INSTALLER%" /quiet InstallAllUsers=0 TargetDir="%TARGET_DIR%" PrependPath=1 Include_pip=1 Include_tcltk=1 Include_test=0 Include_doc=0 Include_launcher=1 AssociateFiles=1 Shortcuts=1
set "RC=%errorlevel%"
echo       安装程序返回码：%RC%

if "%RC%"=="3010" (
    echo [提示] 安装完成，但系统建议重启（返回码 3010）。可以稍后重启。
) else (
    if not "%RC%"=="0" goto :fail
)

if not exist "%TARGET_DIR%\python.exe" (
    REM 兜底：搜索其它可能的安装位置
    for /d %%D in ("%LocalAppData%\Programs\Python\Python38*" "C:\Python38-32") do (
        if exist "%%~D\python.exe" set "TARGET_DIR=%%~D"
    )
)

if not exist "%TARGET_DIR%\python.exe" goto :fail

:configure
set "PY=%TARGET_DIR%\python.exe"

echo.
echo [2/3] 校验解释器位数
"%PY%" -c "import sys,struct; print('Python', sys.version.split()[0], '|', struct.calcsize('P')*8, '位 |', sys.executable)"
if errorlevel 1 goto :fail

echo.
echo [3/3] 安装运行依赖 python-can
"%PY%" -m pip install --disable-pip-version-check --no-warn-script-location -i https://pypi.tuna.tsinghua.edu.cn/simple "python-can==4.5.0"
set "PIPRC=%errorlevel%"
if not "%PIPRC%"=="0" (
    echo [警告] 清华镜像安装失败，改用官方源重试...
    "%PY%" -m pip install --disable-pip-version-check --no-warn-script-location "python-can==4.5.0"
    set "PIPRC=!errorlevel!"
)
if not "!PIPRC!"=="0" goto :fail

echo.
echo 依赖检查：
"%PY%" -c "import can, tkinter; print('  python-can', can.__version__); print('  tkinter OK')"
if errorlevel 1 goto :fail

echo.
echo ===============================================
echo   安装完成
echo ===============================================
echo.
echo   解释器：%PY%
echo.
echo   下一步：双击同目录的 run_bms.bat 启动模拟器
echo.
if "!AUTO!"=="0" pause
exit /b 0

:fail
echo.
echo [失败] 安装未完成，请检查上面的错误信息。
echo        常见原因：安装包被安全软件拦截、磁盘空间不足。
echo        也可以手动双击 python-3.8.10.exe，
echo        安装时勾选 "Install launcher for all users" 和 "Add Python 3.8 to PATH"。
echo.
if "!AUTO!"=="0" pause
exit /b 1
