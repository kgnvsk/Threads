# 🚀 Налаштування Threads Bot для роботи 24/7

## 📋 Зміст
1. [Управління ботом (Використовуй це!)](#управління-ботом)
2. [Налаштування для Linux серверів](#для-linux-серверів-systemd)
3. [Налаштування для macOS](#для-macos-launchd)
4. [Альтернатива: screen/tmux](#альтернатива-screentmux)

---

## 🎮 Управління ботом

### Базові команди (ЗАВЖДИ використовуй ці):

```bash
# Запуск бота
./bot_manager.sh start

# Зупинка бота
./bot_manager.sh stop

# Перезапуск бота
./bot_manager.sh restart

# Статус бота
./bot_manager.sh status
```

### ✅ Переваги:
- ✨ Завжди тільки **ОДИН** екземпляр бота
- 📁 PID файл запобігає дублюванню
- 🔒 Автоматична перевірка запущених процесів
- 📊 Легка діагностика статусу

---

## 🐧 Для Linux серверів (systemd)

### 1. Скопіюй service файл:
```bash
sudo cp threads-bot.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/threads-bot.service
```

### 2. Оновлюй шляхи в `/etc/systemd/system/threads-bot.service`:
- Зміни `User=admin` на своє ім'я користувача
- Зміни `/Users/admin/Threads` на свій шлях

### 3. Активуй та запусти:
```bash
# Перезавантаж конфіги
sudo systemctl daemon-reload

# Увімкни автозапуск
sudo systemctl enable threads-bot

# Запусти бота
sudo systemctl start threads-bot

# Перевір статус
sudo systemctl status threads-bot

# Дивись логи
sudo journalctl -u threads-bot -f
```

### 4. Команди управління:
```bash
# Зупинити
sudo systemctl stop threads-bot

# Перезапустити
sudo systemctl restart threads-bot

# Вимкнути автозапуск
sudo systemctl disable threads-bot
```

---

## 🍎 Для macOS (launchd)

### 1. Скопіюй plist файл:
```bash
cp com.threads.bot.plist ~/Library/LaunchAgents/
chmod 644 ~/Library/LaunchAgents/com.threads.bot.plist
```

### 2. Завантаж та запусти:
```bash
# Завантаж сервіс
launchctl load ~/Library/LaunchAgents/com.threads.bot.plist

# Запусти (якщо не запустився автоматично)
launchctl start com.threads.bot

# Перевір статус
launchctl list | grep threads.bot
```

### 3. Команди управління:
```bash
# Зупинити
launchctl stop com.threads.bot

# Видалити з автозапуску
launchctl unload ~/Library/LaunchAgents/com.threads.bot.plist

# Перезапустити
launchctl stop com.threads.bot && launchctl start com.threads.bot
```

---

## 🖥️ Альтернатива: screen/tmux

### Використання screen:
```bash
# Створи нову сесію
screen -S threads_bot

# Запусти бота
python3 bot.py

# Відключись від сесії: Ctrl+A, потім D

# Повернись до сесії
screen -r threads_bot

# Список сесій
screen -ls

# Вбити сесію
screen -X -S threads_bot quit
```

### Використання tmux:
```bash
# Створи нову сесію
tmux new -s threads_bot

# Запусти бота
python3 bot.py

# Відключись від сесії: Ctrl+B, потім D

# Повернись до сесії
tmux attach -t threads_bot

# Список сесій
tmux ls

# Вбити сесію
tmux kill-session -t threads_bot
```

---

## 🔍 Діагностика

### Перевірка запущених процесів:
```bash
# Знайти процеси бота
ps aux | grep "bot.py"

# Знайти по PID файлу
cat bot.pid

# Перевірити логи
tail -f threads_bot.log
```

### Якщо бот не запускається:
1. Перевір логи: `tail -50 threads_bot.log`
2. Перевір права: `chmod +x bot_manager.sh`
3. Перевір Python: `which python3`
4. Перевір залежності: `pip3 list | grep telegram`

---

## ⚠️ ВАЖЛИВО

### ❌ НЕ РОБИ:
- ❌ `python3 bot.py &` - створить процес без контролю
- ❌ `nohup python3 bot.py &` - може створити дублікати
- ❌ Запускати бота кілька разів

### ✅ ЗАВЖДИ ВИКОРИСТОВУЙ:
- ✅ `./bot_manager.sh start` - безпечний запуск
- ✅ `./bot_manager.sh stop` перед новим запуском
- ✅ `./bot_manager.sh status` для перевірки

---

## 📞 Швидка допомога

**Бот не запускається?**
```bash
./bot_manager.sh stop
rm -f bot.pid
./bot_manager.sh start
```

**Кілька процесів бота?**
```bash
killall -9 python3
rm -f bot.pid
./bot_manager.sh start
```

**Переглянути останні помилки:**
```bash
tail -100 threads_bot.log | grep ERROR
```

