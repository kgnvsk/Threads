# ⚡ Швидкий старт: Розгортання на сервері

## 🎯 Мета
Запустити бота на хмарному сервері, щоб він працював 24/7 навіть коли твій комп'ютер вимкнений.

---

## 🚀 Варіант 1: Автоматичне розгортання (РЕКОМЕНДУЮ)

### Крок 1: Створи сервер
Вибери платформу:
- **AWS EC2** (безкоштовно перший рік) → https://aws.amazon.com/free/
- **Hetzner** (€4.15/міс, найдешевше) → https://www.hetzner.com/cloud
- **DigitalOcean** ($6/міс) → https://www.digitalocean.com/

**Налаштування при створенні:**
- OS: Ubuntu 22.04 LTS
- RAM: мінімум 1GB
- SSH ключ: додай свій публічний ключ

### Крок 2: Запусти скрипт розгортання
```bash
./deploy_to_server.sh user@your-server-ip
```

Приклад:
```bash
./deploy_to_server.sh ubuntu@54.123.45.67
```

### Крок 3: Готово! 🎉
Бот автоматично:
- ✅ Встановить всі залежності
- ✅ Скопіює файли
- ✅ Налаштує автозапуск
- ✅ Запустить бота

---

## 🛠️ Варіант 2: Ручне розгортання

### 1. Підключись до сервера
```bash
ssh user@your-server-ip
```

### 2. Встанови залежності
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip git -y
pip3 install python-telegram-bot openai requests
```

### 3. Завантаж файли бота
```bash
mkdir ~/Threads
cd ~/Threads

# На локальному комп'ютері:
# scp -r /Users/admin/Threads/* user@server-ip:~/Threads/
```

### 4. Налаштуй автозапуск
```bash
# Створи service файл
sudo nano /etc/systemd/system/threads-bot.service
```

Вставити:
```ini
[Unit]
Description=Threads Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/Threads
ExecStart=/usr/bin/python3 /home/YOUR_USERNAME/Threads/bot.py
Restart=always
RestartSec=10
StandardOutput=append:/home/YOUR_USERNAME/Threads/threads_bot.log
StandardError=append:/home/YOUR_USERNAME/Threads/threads_bot.log

[Install]
WantedBy=multi-user.target
```

### 5. Запусти
```bash
sudo systemctl daemon-reload
sudo systemctl enable threads-bot
sudo systemctl start threads-bot
sudo systemctl status threads-bot
```

---

## 📊 Після розгортання

### Перевірити статус
```bash
ssh user@server-ip 'sudo systemctl status threads-bot'
```

### Подивитися логи
```bash
ssh user@server-ip 'tail -f ~/Threads/threads_bot.log'
```

### Перезапустити
```bash
ssh user@server-ip 'sudo systemctl restart threads-bot'
```

---

## 💰 Рекомендації по хостингу

### 🏆 Найкраще для старту
**AWS EC2 Free Tier**
- ✅ Безкоштовно 12 місяців
- ✅ Надійно
- ✅ 1GB RAM достатньо
- 📝 Потрібна картка (не списують)

### 💵 Найдешевше довгостроково
**Hetzner Cloud**
- ✅ €4.15/міс (~$4.5)
- ✅ 2GB RAM
- ✅ Швидко
- 📝 Потрібна оплата

### 🆓 Безкоштовно назавжди
**Google Cloud e2-micro**
- ✅ Безкоштовно назавжди
- ⚠️ Тільки 0.25-1GB RAM
- 📝 Може бути повільно

---

## ⚠️ Важливо!

### Перед розгортанням:
- [ ] Маєш SSH ключ
- [ ] config.py з правильними токенами
- [ ] Вибрав хостинг-провайдера

### Після розгортання:
- [ ] Перевір що бот працює (`systemctl status`)
- [ ] Перевір логи (без помилок)
- [ ] Перезавантаж сервер (`sudo reboot`) та перевір що бот автоматично запустився
- [ ] Надішли `/status` боту в Telegram

---

## 🆘 Проблеми?

### Бот не запускається
```bash
# Подивись логи
ssh user@server-ip 'sudo journalctl -u threads-bot -n 50'
```

### Conflict errors
```bash
# Зупини та перезапусти
ssh user@server-ip 'sudo systemctl restart threads-bot'
```

### Мало пам'яті
```bash
# Додай swap
ssh user@server-ip << 'EOF'
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
EOF
```

---

## 📞 Потрібна допомога?

Детальні інструкції: [DEPLOY_SERVER.md](DEPLOY_SERVER.md)

**Основні файли:**
- `deploy_to_server.sh` - автоматичне розгортання
- `DEPLOY_SERVER.md` - детальні інструкції
- `threads-bot.service` - systemd конфіг

---

## ✅ Чеклист готовності

- [ ] Створив сервер на AWS/Hetzner/DO
- [ ] Додав SSH ключ
- [ ] Запустив `./deploy_to_server.sh`
- [ ] Перевірив статус (`systemctl status`)
- [ ] Протестував перезавантаження сервера
- [ ] Бот відповідає в Telegram

**Готово! Твій бот працює 24/7** 🎉

