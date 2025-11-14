"""
Скрипт для тестування підключення до Threads API
Використовуйте його для перевірки налаштувань перед запуском бота
"""
import sys
import logging
from config import config
from threads_api import ThreadsAPI

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_threads_connection():
    """Тестує підключення до Threads API"""
    
    logger.info("=" * 60)
    logger.info("ТЕСТУВАННЯ ПІДКЛЮЧЕННЯ ДО THREADS API")
    logger.info("=" * 60)
    
    # Перевіряємо конфігурацію
    logger.info("\n1. Перевірка конфігурації...")
    
    if not config.THREADS_USER_ID or config.THREADS_USER_ID == "ВАШ_THREADS_USER_ID":
        logger.error("❌ THREADS_USER_ID не налаштовано!")
        return False
        
    if not config.THREADS_ACCESS_TOKEN or config.THREADS_ACCESS_TOKEN == "ВАШ_THREADS_ACCESS_TOKEN":
        logger.error("❌ THREADS_ACCESS_TOKEN не налаштовано!")
        return False
        
    logger.info(f"✅ User ID: {config.THREADS_USER_ID[:20]}...")
    logger.info(f"✅ Access Token: {config.THREADS_ACCESS_TOKEN[:30]}...")
    
    # Створюємо API клієнт
    logger.info("\n2. Створення API клієнта...")
    threads_api = ThreadsAPI(
        user_id=config.THREADS_USER_ID,
        access_token=config.THREADS_ACCESS_TOKEN
    )
    logger.info("✅ API клієнт створено")
    
    # Тестуємо створення простого текстового поста
    logger.info("\n3. Тестування створення тестового поста...")
    logger.info("   (Пост буде створено, але НЕ опубліковано)")
    
    test_text = "🤖 Це тестовий пост від Threads Auto-Publisher Bot"
    
    creation_id = threads_api.create_text_post(test_text)
    
    if not creation_id:
        logger.error("❌ Не вдалося створити тестовий пост!")
        logger.error("   Перевірте:")
        logger.error("   - Правильність User ID та Access Token")
        logger.error("   - Дозволи токена (threads_content_publish)")
        logger.error("   - Чи не прострочений токен")
        return False
        
    logger.info(f"✅ Тестовий пост створено! Creation ID: {creation_id}")
    
    # Перевіряємо статус
    logger.info("\n4. Перевірка статусу поста...")
    status, error_message = threads_api.check_status(creation_id)
    
    logger.info(f"   Статус: {status.value}")
    
    if error_message:
        logger.warning(f"   Повідомлення: {error_message}")
    
    if status.value in ["FINISHED", "IN_PROGRESS"]:
        logger.info("✅ Статус поста нормальний")
    else:
        logger.error(f"❌ Статус поста: {status.value}")
        if error_message:
            logger.error(f"   Помилка: {error_message}")
        return False
    
    # Фінальний результат
    logger.info("\n" + "=" * 60)
    logger.info("✅ ВСІ ТЕСТИ ПРОЙДЕНО УСПІШНО!")
    logger.info("=" * 60)
    logger.info("\n📝 Примітка: Тестовий пост НЕ був опубліковано в Threads.")
    logger.info("   Він створений, але залишився в статусі чернетки.")
    logger.info("\n🚀 Ви можете запускати бота: python bot.py")
    logger.info("=" * 60)
    
    return True


def test_telegram_connection():
    """Тестує налаштування Telegram"""
    
    logger.info("\n" + "=" * 60)
    logger.info("ПЕРЕВІРКА НАЛАШТУВАНЬ TELEGRAM")
    logger.info("=" * 60)
    
    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "ВАШ_TELEGRAM_BOT_TOKEN":
        logger.error("❌ TELEGRAM_BOT_TOKEN не налаштовано!")
        return False
        
    if not config.TELEGRAM_CHANNEL_ID or config.TELEGRAM_CHANNEL_ID == "@ВАШ_КАНАЛ":
        logger.error("❌ TELEGRAM_CHANNEL_ID не налаштовано!")
        return False
    
    logger.info(f"✅ Bot Token: {config.TELEGRAM_BOT_TOKEN[:20]}...")
    logger.info(f"✅ Channel ID: {config.TELEGRAM_CHANNEL_ID}")
    
    logger.info("\n⚠️  ВАЖЛИВО: Переконайтесь, що:")
    logger.info("   1. Бот доданий як адміністратор каналу")
    logger.info("   2. У бота є права на читання повідомлень")
    logger.info("   3. Channel ID вказаний правильно (@username або -100...)")
    
    return True


def test_openai_connection():
    """Тестує налаштування OpenAI"""
    
    logger.info("\n" + "=" * 60)
    logger.info("ПЕРЕВІРКА НАЛАШТУВАНЬ OPENAI")
    logger.info("=" * 60)
    
    if not config.OPENAI_API_KEY or config.OPENAI_API_KEY == "ВАШ_OPENAI_API_KEY":
        logger.error("❌ OPENAI_API_KEY не налаштовано!")
        return False
    
    logger.info(f"✅ API Key: {config.OPENAI_API_KEY[:20]}...")
    logger.info(f"✅ Model: {config.OPENAI_MODEL}")
    
    # Можна додати тестовий запит до OpenAI, але це витратить токени
    logger.info("\n📝 Примітка: OpenAI буде використовуватись тільки для довгих текстів")
    
    return True


def main():
    """Головна функція"""
    
    print("\n🔍 Запуск тестування налаштувань...\n")
    
    # Тестуємо всі компоненти
    telegram_ok = test_telegram_connection()
    openai_ok = test_openai_connection()
    threads_ok = test_threads_connection()
    
    # Підсумок
    print("\n\n" + "=" * 60)
    print("ПІДСУМОК ТЕСТУВАННЯ")
    print("=" * 60)
    
    print(f"Telegram:  {'✅ OK' if telegram_ok else '❌ FAILED'}")
    print(f"OpenAI:    {'✅ OK' if openai_ok else '❌ FAILED'}")
    print(f"Threads:   {'✅ OK' if threads_ok else '❌ FAILED'}")
    
    print("=" * 60)
    
    if telegram_ok and openai_ok and threads_ok:
        print("\n🎉 Всі налаштування в порядку! Можна запускати бота.")
        print("   Команда: python bot.py")
        return 0
    else:
        print("\n⚠️  Є проблеми з налаштуваннями. Виправте їх перед запуском бота.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

