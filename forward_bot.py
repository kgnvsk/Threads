#!/usr/bin/env python3
"""
Простий бот для пересилання повідомлень з одного Telegram каналу в інший
Підтримує медіа-групи (альбоми)
Видаляє "Джерело" з посиланням в кінці поста
"""
import logging
import asyncio
import re
from telegram import Update, InputMediaPhoto, InputMediaVideo, InputMediaDocument
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Налаштування
TELEGRAM_BOT_TOKEN = "8334384472:AAFU_dvzum7fANCbWN9tOrYCOT5LOo_TjUg"
SOURCE_CHAT_ID = -1002408747166  # Звідки пересилаємо
TARGET_CHAT_ID = -1002707910280  # Куди пересилаємо

# Логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('forward_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def remove_source_link(text: str) -> str:
    """
    Видаляє 'Джерело' з посиланням в кінці тексту
    Приклади:
    - "текст\n\nДжерело" -> "текст"
    - "текст\n\nДжерело https://..." -> "текст"
    - "текст Джерело" -> "текст"
    """
    if not text:
        return text
    
    # Видаляємо "Джерело" + опціональне посилання в кінці
    # Патерн: "Джерело" + можливий пробіл + можливе посилання
    text = re.sub(r'\n*Джерело\s*(https?://\S+)?\s*$', '', text, flags=re.IGNORECASE)
    
    return text.strip()

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересилає повідомлення з одного каналу в інший"""
    try:
        # Перевіряємо чи повідомлення з потрібного каналу
        if not update.channel_post or update.channel_post.chat.id != SOURCE_CHAT_ID:
            return
            
        message = update.channel_post
        
        # Перевіряємо чи це медіа-група
        if message.media_group_id:
            logger.info(f"📦 Отримано елемент медіа-групи: {message.media_group_id}")
            logger.info(f"   Message ID: {message.message_id}")
            
            # Ініціалізуємо словник для медіа-груп якщо його немає
            if 'media_groups' not in context.bot_data:
                context.bot_data['media_groups'] = {}
            
            media_group_id = message.media_group_id
            
            # Додаємо повідомлення до групи
            if media_group_id not in context.bot_data['media_groups']:
                context.bot_data['media_groups'][media_group_id] = {
                    'messages': [],
                    'processed': False
                }
            
            context.bot_data['media_groups'][media_group_id]['messages'].append(message)
            logger.info(f"   Елементів у групі: {len(context.bot_data['media_groups'][media_group_id]['messages'])}")
            
            # Запускаємо відкладену обробку (через 2 секунди)
            asyncio.create_task(process_media_group_delayed(context, media_group_id))
            
        else:
            # Звичайне повідомлення (не медіа-група)
            logger.info(f"📨 Отримано повідомлення з каналу {SOURCE_CHAT_ID}")
            logger.info(f"   Message ID: {message.message_id}")
            
            # Отримуємо caption або text
            original_text = message.caption or message.text or ""
            
            # Видаляємо "Джерело"
            cleaned_text = remove_source_link(original_text)
            
            if original_text != cleaned_text:
                logger.info(f"   🧹 Видалено 'Джерело' з тексту")
            
            # Пересилаємо в залежності від типу
            if message.photo:
                # Фото
                photo = message.photo[-1]  # Найбільше фото
                await context.bot.send_photo(
                    chat_id=TARGET_CHAT_ID,
                    photo=photo.file_id,
                    caption=cleaned_text if cleaned_text else None
                )
            elif message.video:
                # Відео
                await context.bot.send_video(
                    chat_id=TARGET_CHAT_ID,
                    video=message.video.file_id,
                    caption=cleaned_text if cleaned_text else None
                )
            elif message.document:
                # Документ
                await context.bot.send_document(
                    chat_id=TARGET_CHAT_ID,
                    document=message.document.file_id,
                    caption=cleaned_text if cleaned_text else None
                )
            elif message.text:
                # Текст
                await context.bot.send_message(
                    chat_id=TARGET_CHAT_ID,
                    text=cleaned_text
                )
            else:
                # Інше - просто копіюємо
                await context.bot.copy_message(
                    chat_id=TARGET_CHAT_ID,
                    from_chat_id=SOURCE_CHAT_ID,
                    message_id=message.message_id
                )
            
            logger.info(f"✅ Повідомлення переслано!")
            
    except Exception as e:
        logger.error(f"❌ Помилка при пересиланні: {e}", exc_info=True)

async def process_media_group_delayed(context: ContextTypes.DEFAULT_TYPE, media_group_id: str):
    """Відкладена обробка медіа-групи (через 2 секунди після останнього повідомлення)"""
    await asyncio.sleep(2)
    await process_media_group(context, media_group_id)

async def process_media_group(context: ContextTypes.DEFAULT_TYPE, media_group_id: str):
    """Обробка зібраної медіа-групи"""
    try:
        if media_group_id not in context.bot_data.get('media_groups', {}):
            return
            
        group_data = context.bot_data['media_groups'][media_group_id]
        
        # Якщо вже оброблено - виходимо
        if group_data['processed']:
            return
            
        group_data['processed'] = True
        messages = group_data['messages']
        
        logger.info(f"📦 Обробляємо медіа-групу з {len(messages)} елементів")
        
        # Створюємо InputMedia об'єкти з очищеним текстом
        media_items = []
        for i, msg in enumerate(messages):
            original_caption = msg.caption or ""
            cleaned_caption = remove_source_link(original_caption)
            
            if i == 0 and original_caption != cleaned_caption:
                logger.info(f"   🧹 Видалено 'Джерело' з медіа-групи")
            
            # Тільки перший елемент має caption
            caption = cleaned_caption if i == 0 and cleaned_caption else None
            
            if msg.photo:
                photo = msg.photo[-1]
                media_items.append(InputMediaPhoto(media=photo.file_id, caption=caption))
            elif msg.video:
                media_items.append(InputMediaVideo(media=msg.video.file_id, caption=caption))
            elif msg.document:
                media_items.append(InputMediaDocument(media=msg.document.file_id, caption=caption))
        
        if media_items:
            # Відправляємо медіа-групу
            await context.bot.send_media_group(
                chat_id=TARGET_CHAT_ID,
                media=media_items
            )
            
            logger.info(f"✅ Медіа-група переслана! {len(media_items)} елементів")
        
        # Очищаємо дані групи
        del context.bot_data['media_groups'][media_group_id]
        
    except Exception as e:
        logger.error(f"❌ Помилка при пересиланні медіа-групи: {e}", exc_info=True)

def main():
    """Запускає бота"""
    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК FORWARD BOT (з підтримкою медіа-груп)")
    logger.info("=" * 60)
    logger.info(f"📥 Джерело: {SOURCE_CHAT_ID}")
    logger.info(f"📤 Цільовий канал: {TARGET_CHAT_ID}")
    logger.info(f"🧹 Видалення 'Джерело': УВІМКНЕНО")
    logger.info("=" * 60)
    
    # Створюємо додаток
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Обробник для всіх повідомлень з каналу
    application.add_handler(
        MessageHandler(
            filters.Chat(SOURCE_CHAT_ID) & filters.ChatType.CHANNEL,
            forward_message
        )
    )
    
    logger.info("✅ БОТ ГОТОВИЙ! Очікую повідомлень...")
    logger.info("🛑 Натисніть Ctrl+C для зупинки")
    logger.info("=" * 60)
    
    # Запускаємо polling
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⏹️  Бот зупинено користувачем")
    except Exception as e:
        logger.error(f"❌ Критична помилка: {e}", exc_info=True)
