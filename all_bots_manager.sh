#!/bin/bash

# Управління всіма ботами одночасно
# Використання: ./all_bots_manager.sh {start|stop|restart|status}

BOT_DIR="/Users/admin/Threads"
cd "$BOT_DIR" || exit 1

case "$1" in
    start)
        echo "🚀 ЗАПУСК ВСІХ БОТІВ"
        echo "===================="
        echo ""
        echo "1️⃣ Threads Bot (основний):"
        ./bot_manager.sh start
        echo ""
        echo "2️⃣ Forward Bot (пересилання):"
        ./forward_bot_manager.sh start
        echo ""
        echo "✅ Всі боти запущені!"
        ;;
    
    stop)
        echo "🛑 ЗУПИНКА ВСІХ БОТІВ"
        echo "===================="
        echo ""
        echo "1️⃣ Threads Bot (основний):"
        ./bot_manager.sh stop
        echo ""
        echo "2️⃣ Forward Bot (пересилання):"
        ./forward_bot_manager.sh stop
        echo ""
        echo "✅ Всі боти зупинені!"
        ;;
    
    restart)
        echo "🔄 ПЕРЕЗАПУСК ВСІХ БОТІВ"
        echo "========================"
        echo ""
        echo "🛑 Спочатку зупиняємо все..."
        ./bot_manager.sh stop
        ./forward_bot_manager.sh stop
        echo ""
        echo "⏳ Чекаємо 3 секунди..."
        sleep 3
        echo ""
        echo "🚀 Запускаємо знову..."
        ./bot_manager.sh start
        echo ""
        ./forward_bot_manager.sh start
        echo ""
        echo "✅ Всі боти перезапущені!"
        ;;
    
    status)
        echo "📊 СТАТУС ВСІХ БОТІВ"
        echo "===================="
        echo ""
        echo "1️⃣ Threads Bot (основний):"
        ./bot_manager.sh status
        STATUS1=$?
        echo ""
        echo "2️⃣ Forward Bot (пересилання):"
        ./forward_bot_manager.sh status
        STATUS2=$?
        echo ""
        echo "===================="
        if [ $STATUS1 -eq 0 ] && [ $STATUS2 -eq 0 ]; then
            echo "✅ Всі боти працюють нормально"
        else
            echo "⚠️  Деякі боти не працюють!"
        fi
        ;;
    
    *)
        echo "Використання: $0 {start|stop|restart|status}"
        echo ""
        echo "Команди:"
        echo "  start   - Запустити всі боти"
        echo "  stop    - Зупинити всі боти"
        echo "  restart - Перезапустити всі боти"
        echo "  status  - Показати статус всіх ботів"
        exit 1
        ;;
esac

exit 0

