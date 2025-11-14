"""
Конфігураційний файл для Threads Bot
Скопіюйте цей файл як config.py та заповніть своїми даними
"""
import os
from dataclasses import dataclass

@dataclass
class Config:
    # Telegram налаштування
    TELEGRAM_BOT_TOKEN: str = "YOUR_TELEGRAM_BOT_TOKEN"
    TELEGRAM_CHANNEL_ID: int = -1234567890  # Chat ID вашого каналу
    ADMIN_ID: int = 123456789  # Telegram ID адміністратора (для команд)
    
    # Threads API налаштування
    THREADS_USER_ID: str = "YOUR_THREADS_USER_ID"
    THREADS_ACCESS_TOKEN: str = "YOUR_THREADS_ACCESS_TOKEN"
    
    # OpenAI налаштування (для розбивки довгих текстів)
    OPENAI_API_KEY: str = "YOUR_OPENAI_API_KEY"
    OPENAI_MODEL: str = "gpt-4.1"  # GPT-4.1
    
    # Загальні налаштування
    MAX_TEXT_LENGTH: int = 450  # максимум символів в одному пості Threads
    PUBLISH_DELAY: int = 3  # затримка між публікаціями (секунди)
    STATUS_CHECK_DELAY: int = 5  # затримка перед перевіркою статусу публікації
    MAX_STATUS_CHECKS: int = 20  # максимальна кількість перевірок статусу
    
    # Логування
    LOG_LEVEL: str = "INFO"  # INFO для нормальної роботи, DEBUG для детального логування
    LOG_FILE: str = "threads_bot.log"


# Завантаження з environment variables (якщо є)
config = Config(
    TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN", Config.TELEGRAM_BOT_TOKEN),
    TELEGRAM_CHANNEL_ID=int(os.getenv("TELEGRAM_CHANNEL_ID", str(Config.TELEGRAM_CHANNEL_ID))),
    THREADS_USER_ID=os.getenv("THREADS_USER_ID", Config.THREADS_USER_ID),
    THREADS_ACCESS_TOKEN=os.getenv("THREADS_ACCESS_TOKEN", Config.THREADS_ACCESS_TOKEN),
    OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", Config.OPENAI_API_KEY),
)

