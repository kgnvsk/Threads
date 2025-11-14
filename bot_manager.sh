#!/bin/bash

# Управління Threads Bot
# Використання: ./bot_manager.sh {start|stop|restart|status}

BOT_DIR="/Users/admin/Threads"
PID_FILE="$BOT_DIR/bot.pid"
LOG_FILE="$BOT_DIR/threads_bot.log"
PYTHON="python3"

cd "$BOT_DIR" || exit 1

start_bot() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "❌ Бот вже запущено (PID: $PID)"
            return 1
        else
            echo "⚠️  PID файл існує, але процес не знайдено. Очищаємо..."
            rm -f "$PID_FILE"
        fi
    fi
    
    echo "🚀 Запускаємо бота..."
    nohup $PYTHON "$BOT_DIR/bot.py" >> "$LOG_FILE" 2>&1 &
    BOT_PID=$!
    echo $BOT_PID > "$PID_FILE"
    
    sleep 2
    
    if ps -p "$BOT_PID" > /dev/null 2>&1; then
        echo "✅ Бот успішно запущено (PID: $BOT_PID)"
        echo "📝 Логи: tail -f $LOG_FILE"
        return 0
    else
        echo "❌ Помилка запуску бота"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop_bot() {
    if [ ! -f "$PID_FILE" ]; then
        echo "⚠️  PID файл не знайдено"
        # Перевіряємо чи є запущені процеси
        PIDS=$(ps aux | grep "[p]ython.*bot.py" | awk '{print $2}')
        if [ -n "$PIDS" ]; then
            echo "🔍 Знайдено запущені процеси бота: $PIDS"
            echo "🛑 Зупиняємо їх..."
            echo "$PIDS" | xargs kill -9 2>/dev/null
            echo "✅ Процеси зупинено"
        else
            echo "ℹ️  Бот не запущено"
        fi
        return 0
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "🛑 Зупиняємо бота (PID: $PID)..."
        kill -15 "$PID" 2>/dev/null
        sleep 2
        
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "⚠️  Процес не відповідає, використовуємо SIGKILL..."
            kill -9 "$PID" 2>/dev/null
            sleep 1
        fi
        
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "❌ Не вдалося зупинити процес"
            return 1
        else
            echo "✅ Бот зупинено"
            rm -f "$PID_FILE"
            return 0
        fi
    else
        echo "⚠️  Процес не знайдено"
        rm -f "$PID_FILE"
        return 0
    fi
}

status_bot() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "✅ Бот ЗАПУЩЕНО (PID: $PID)"
            echo ""
            ps -p "$PID" -o pid,comm,%cpu,%mem,etime,command | grep -v PID
            return 0
        else
            echo "❌ PID файл існує, але процес не запущено"
            return 1
        fi
    else
        # Перевіряємо чи є запущені процеси без PID файлу
        PIDS=$(ps aux | grep "[p]ython.*bot.py" | awk '{print $2}')
        if [ -n "$PIDS" ]; then
            echo "⚠️  Бот запущено БЕЗ PID файлу (PID: $PIDS)"
            return 2
        else
            echo "⏹️  Бот ЗУПИНЕНО"
            return 1
        fi
    fi
}

restart_bot() {
    echo "🔄 Перезапускаємо бота..."
    stop_bot
    sleep 2
    start_bot
}

case "$1" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    status)
        status_bot
        ;;
    *)
        echo "Використання: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

exit $?

