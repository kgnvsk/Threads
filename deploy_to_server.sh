#!/bin/bash

# Скрипт для швидкого розгортання Threads Bot на Linux сервері
# Використання: ./deploy_to_server.sh SERVER_IP

set -e

if [ -z "$1" ]; then
    echo "❌ Використання: ./deploy_to_server.sh user@server-ip"
    echo "Приклад: ./deploy_to_server.sh ubuntu@54.123.45.67"
    exit 1
fi

SERVER="$1"
BOT_DIR="/Users/admin/Threads"
REMOTE_DIR="~/Threads"

echo "🚀 Розгортання Threads Bot на $SERVER"
echo ""

# 1. Перевірка підключення
echo "1️⃣ Перевірка SSH з'єднання..."
if ssh -o ConnectTimeout=5 "$SERVER" "echo '✅ З'"'"'єднання OK'" 2>/dev/null; then
    echo "✅ SSH з'єднання працює"
else
    echo "❌ Не вдалося підключитися до сервера"
    echo "Перевір:"
    echo "  - IP адресу сервера"
    echo "  - SSH ключ"
    echo "  - Firewall правила"
    exit 1
fi
echo ""

# 2. Встановлення залежностей на сервері
echo "2️⃣ Встановлення залежностей на сервері..."
ssh "$SERVER" << 'ENDSSH'
echo "📦 Оновлення системи..."
sudo apt update -qq

echo "🐍 Встановлення Python..."
sudo apt install -y python3 python3-pip git > /dev/null 2>&1

echo "📚 Встановлення Python бібліотек..."
pip3 install -q python-telegram-bot openai requests

echo "✅ Залежності встановлено"
ENDSSH
echo ""

# 3. Створення директорії
echo "3️⃣ Створення директорії на сервері..."
ssh "$SERVER" "mkdir -p $REMOTE_DIR"
echo "✅ Директорія створена"
echo ""

# 4. Копіювання файлів
echo "4️⃣ Копіювання файлів бота..."
echo "  📄 bot.py"
scp -q "$BOT_DIR/bot.py" "$SERVER:$REMOTE_DIR/"
echo "  📄 config.py"
scp -q "$BOT_DIR/config.py" "$SERVER:$REMOTE_DIR/"
echo "  📄 database.py"
scp -q "$BOT_DIR/database.py" "$SERVER:$REMOTE_DIR/"
echo "  📄 threads_api.py"
scp -q "$BOT_DIR/threads_api.py" "$SERVER:$REMOTE_DIR/"
echo "  📄 text_splitter.py"
scp -q "$BOT_DIR/text_splitter.py" "$SERVER:$REMOTE_DIR/"
echo "  📄 media_uploader.py"
scp -q "$BOT_DIR/media_uploader.py" "$SERVER:$REMOTE_DIR/"
echo "✅ Файли скопійовано"
echo ""

# 5. Налаштування systemd
echo "5️⃣ Налаштування systemd service..."

# Отримуємо username
USERNAME=$(ssh "$SERVER" "whoami")
REMOTE_PATH=$(ssh "$SERVER" "cd $REMOTE_DIR && pwd")

# Створюємо service файл
cat > /tmp/threads-bot.service << EOF
[Unit]
Description=Threads Bot - Telegram to Threads Auto Publisher
After=network.target

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=$REMOTE_PATH
ExecStart=/usr/bin/python3 $REMOTE_PATH/bot.py
Restart=always
RestartSec=10
StandardOutput=append:$REMOTE_PATH/threads_bot.log
StandardError=append:$REMOTE_PATH/threads_bot.log

[Install]
WantedBy=multi-user.target
EOF

# Копіюємо на сервер
scp -q /tmp/threads-bot.service "$SERVER:/tmp/"
rm /tmp/threads-bot.service

# Встановлюємо service
ssh "$SERVER" << 'ENDSSH'
sudo mv /tmp/threads-bot.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/threads-bot.service
sudo systemctl daemon-reload
sudo systemctl enable threads-bot
ENDSSH

echo "✅ Systemd service налаштовано"
echo ""

# 6. Запуск бота
echo "6️⃣ Запуск бота..."
ssh "$SERVER" "sudo systemctl start threads-bot"
sleep 3
echo "✅ Бот запущено"
echo ""

# 7. Перевірка статусу
echo "7️⃣ Перевірка статусу..."
if ssh "$SERVER" "sudo systemctl is-active --quiet threads-bot"; then
    echo "✅ Бот працює!"
    echo ""
    echo "📊 Статус:"
    ssh "$SERVER" "sudo systemctl status threads-bot --no-pager -l" | head -15
else
    echo "❌ Бот не запустився"
    echo ""
    echo "📋 Логи:"
    ssh "$SERVER" "tail -20 $REMOTE_DIR/threads_bot.log"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 РОЗГОРТАННЯ ЗАВЕРШЕНО!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 Сервер: $SERVER"
echo "📁 Директорія: $REMOTE_PATH"
echo ""
echo "🎮 Корисні команди:"
echo ""
echo "  Підключитися до сервера:"
echo "    ssh $SERVER"
echo ""
echo "  Переглянути логи:"
echo "    ssh $SERVER 'tail -f $REMOTE_DIR/threads_bot.log'"
echo ""
echo "  Статус бота:"
echo "    ssh $SERVER 'sudo systemctl status threads-bot'"
echo ""
echo "  Перезапустити бота:"
echo "    ssh $SERVER 'sudo systemctl restart threads-bot'"
echo ""
echo "  Зупинити бота:"
echo "    ssh $SERVER 'sudo systemctl stop threads-bot'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

