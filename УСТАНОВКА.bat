@echo off
chcp 65001 >nul
echo.
echo ╔══════════════════════════════════════╗
echo ║     🍳 Личный Шеф — Установка       ║
╚══════════════════════════════════════╝
echo.

echo [1/3] Проверяю Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден!
    echo Открываю сайт для скачивания...
    start https://python.org/downloads
    echo.
    echo После установки Python:
    echo  - Поставь галочку "Add Python to PATH"
    echo  - Закрой это окно и запусти снова
    pause
    exit
)
echo ✅ Python найден!

echo.
echo [2/3] Устанавливаю библиотеки...
pip install python-telegram-bot groq python-dotenv requests beautifulsoup4 -q
echo ✅ Библиотеки установлены!

echo.
echo [3/3] Проверяю файл с ключами...
if not exist .env (
    echo.
    echo ⚠️  Файл .env не найден! Введи ключи:
    echo.
    set /p TOKEN="Вставь ТОКЕН от @BotFather: "
    set /p GROQ="Вставь ключ от Groq (console.groq.com): "
    echo TELEGRAM_TOKEN=%TOKEN%>.env
    echo GROQ_API_KEY=%GROQ%>>.env
    echo ✅ Файл .env создан!
) else (
    echo ✅ Файл .env найден!
)

echo.
echo ══════════════════════════════════════
echo ✅ Всё готово! Запускаю бота...
echo ══════════════════════════════════════
echo.
echo Бот запущен! Открой Telegram и напиши /start
echo Чтобы остановить — нажми Ctrl+C
echo.
python bot.py
pause
