@echo off
chcp 65001 >nul
echo ================================
echo    NCM 快速解密工具选择器
echo ================================
echo.
echo 请选择解密模式:
echo 1. 普通优化模式 (兼容性好)
echo 2. 超快速模式 (需要 numpy，速度更快)
echo 3. 安装 numpy 依赖
echo 4. 退出
echo.
set /p choice="请输入选择 (1-4): "

if "%choice%"=="1" (
    echo.
    echo 启动普通优化模式...
    python crack.py
    pause
) else if "%choice%"=="2" (
    echo.
    echo 启动超快速模式...
    python crack_ultra_fast.py
    pause
) else if "%choice%"=="3" (
    echo.
    echo 正在安装 numpy...
    pip install numpy
    echo.
    echo 安装完成！
    pause
) else if "%choice%"=="4" (
    exit
) else (
    echo 无效选择，请重新运行程序
    pause
)
