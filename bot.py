"""
Основний модуль Telegram боту для автоматичної публікації в Threads
"""
import time
import asyncio
import logging
import requests
from typing import List, Optional
from telegram import Update, PhotoSize, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters
)

from config import config
from threads_api import ThreadsAPI, MediaType
from text_splitter import TextSplitter
from database import Database

# Налаштування логування
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Вимикаємо DEBUG логи від бібліотек
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('openai').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class ThreadsBot:
    """Головний клас боту"""
    
    def __init__(self):
        """Ініціалізація боту"""
        self.threads_api = ThreadsAPI(
            user_id=config.THREADS_USER_ID,
            access_token=config.THREADS_ACCESS_TOKEN
        )
        self.text_splitter = TextSplitter(
            api_key=config.OPENAI_API_KEY,
            model=config.OPENAI_MODEL,
            max_length=config.MAX_TEXT_LENGTH
        )
        self.database = Database()
        
        # Стан бота
        self.is_running = True
        
        # Текст рекламного поста (можна змінювати через /set_promo)
        saved_promo = self.database.get_setting('promo_text')
        self.promo_text = saved_promo if saved_promo else "📌 Якщо хочете знати більше про АІ, як на ньому заробляти, його реальні кейси застосування та безкоштовно отримати базові знання – підписуйтесь на мій ТГ канал: t.me/kgnvsk_ai"
    
    def _get_admin_keyboard(self):
        """Створює клавіатуру адміністратора"""
        keyboard = [
            [KeyboardButton("📊 Статус"), KeyboardButton("📈 Статистика")],
            [KeyboardButton("📝 Логи"), KeyboardButton("❌ Помилки")],
            [KeyboardButton("🔧 API Статус"), KeyboardButton("💬 Промо текст")],
            [KeyboardButton("▶️ Запустити"), KeyboardButton("⏸️ Зупинити")],
            [KeyboardButton("❓ Допомога")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def _extract_links_from_entities(self, text: str, entities: list) -> str:
        """
        Витягує приховані посилання з entities і додає їх явно після тексту
        
        Args:
            text: Оригінальний текст
            entities: Список entities з Telegram (MessageEntity)
            
        Returns:
            Текст з явними посиланнями
        """
        if not text or not entities:
            return text
        
        # Сортуємо entities в зворотному порядку (від кінця до початку)
        # щоб зміщення позицій не вплинуло на наступні заміни
        sorted_entities = sorted(entities, key=lambda e: e.offset, reverse=True)
        
        result = text
        
        for entity in sorted_entities:
            # Обробляємо тільки text_link (приховані посилання)
            if entity.type == "text_link":
                # Витягуємо текст посилання
                start = entity.offset
                end = start + entity.length
                link_text = text[start:end]
                url = entity.url
                
                # Замінюємо "текст" на "текст URL"
                replacement = f"{link_text} {url}"
                result = result[:start] + replacement + result[end:]
                
                logger.debug(f"  🔗 Витягнуто посилання: '{link_text}' -> {url}")
        
        return result
    
    def _clean_text(self, text: str) -> str:
        """Очищає текст від непотрібних елементів"""
        if not text:
            return text
            
        # Видаляємо "Джерело" в кінці
        text = text.strip()
        if text.endswith("Джерело"):
            text = text[:-7].strip()
        
        return text
    
    async def _add_promo_post(self, reply_to_id: str) -> bool:
        """
        Додає рекламний пост як відповідь
        
        Args:
            reply_to_id: ID поста, до якого додаємо відповідь
            
        Returns:
            True якщо успішно, False якщо помилка
        """
        logger.info("📌 Додаємо рекламний пост...")
        time.sleep(config.PUBLISH_DELAY)
        
        promo_id = self.threads_api.create_and_publish_text(
            text=self.promo_text,
            reply_to_id=reply_to_id,
            publish_delay=config.PUBLISH_DELAY
        )
        
        if promo_id:
            logger.info(f"✅ Рекламний пост додано: {promo_id}")
            return True
        else:
            logger.error("❌ Не вдалося додати рекламний пост")
            return False
    
    async def _upload_to_imgbb(self, image_bytes: bytes, is_video: bool = False) -> Optional[str]:
        """
        Завантажує медіа (фото або відео) на публічний хостинг
        
        Args:
            image_bytes: Байти файлу
            is_video: True якщо це відео, False якщо фото
            
        Returns:
            URL файлу або None при помилці
        """
        try:
            file_size_mb = len(image_bytes) / 1024 / 1024
            logger.debug(f"  Розмір файлу: {file_size_mb:.2f} MB")
            
            # Для відео використовуємо catbox.moe (підтримує до 200MB БЕЗ обмеження на тривалість!)
            if is_video and file_size_mb <= 200:
                try:
                    logger.info(f"  📤 Пробуємо catbox.moe для відео ({file_size_mb:.2f} MB)...")
                    files = {'fileToUpload': ('video.mp4', image_bytes, 'video/mp4')}
                    data = {'reqtype': 'fileupload'}
                    
                    response = await asyncio.to_thread(
                        requests.post,
                        "https://catbox.moe/user/api.php",
                        files=files,
                        data=data,
                        timeout=120  # Більший timeout для великих файлів
                    )
                    
                    logger.info(f"  📡 Catbox відповідь: HTTP {response.status_code}")
                    
                    if response.status_code == 200:
                        url = response.text.strip()
                        if url.startswith('http'):
                            logger.info(f"  ✅ Відео завантажено на catbox: {url}")
                            return url
                        else:
                            logger.warning(f"  ⚠️ Catbox повернув не-URL: {url[:100]}")
                    else:
                        logger.warning(f"  ⚠️ Catbox помилка HTTP {response.status_code}: {response.text[:200]}")
                except Exception as e:
                    logger.warning(f"  ⚠️ Catbox не спрацював: {e}")
                
                # Fallback: спробуємо Imgur (але він обмежений 1 хвилиною)
                try:
                    logger.info(f"  📤 Fallback: пробуємо Imgur (обмеження 1 хвилина)...")
                    
                    files = {'video': ('video.mp4', image_bytes, 'video/mp4')}
                    headers = {'Authorization': 'Client-ID 546c25a59c58ad7'}  # Публічний client ID
                    
                    response = await asyncio.to_thread(
                        requests.post,
                        "https://api.imgur.com/3/upload",
                        files=files,
                        headers=headers,
                        timeout=120
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success'):
                            url = data['data']['link']
                            logger.info(f"  ✅ Відео завантажено на Imgur: {url}")
                            return url
                    else:
                        logger.warning(f"  ⚠️ Imgur повернув HTTP {response.status_code}: {response.text[:100]}")
                except Exception as e:
                    logger.warning(f"  ⚠️ Imgur не спрацював: {e}")
            
            # Для фото - спробуємо telegraph
            if not is_video:
                try:
                    logger.info(f"  📤 Пробуємо telegraph...")
                    files = {'file': ('image.jpg', image_bytes, 'image/jpeg')}
                    response = await asyncio.to_thread(
                        requests.post, 
                        "https://telegra.ph/upload",
                        files=files,
                        timeout=30
                    )
                    
                    logger.info(f"  📡 Telegraph відповідь: HTTP {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"  📦 Telegraph дані: {data}")
                        if isinstance(data, list) and len(data) > 0:
                            path = data[0].get('src')
                            if path:
                                url = f"https://telegra.ph{path}"
                                logger.info(f"  ✅ Фото завантажено на telegraph: {url}")
                                return url
                        else:
                            logger.warning(f"  ⚠️ Telegraph повернув порожній список")
                    else:
                        logger.warning(f"  ⚠️ Telegraph помилка HTTP {response.status_code}: {response.text[:200]}")
                except Exception as e:
                    logger.warning(f"  ⚠️ Telegraph exception: {type(e).__name__}: {e}")
            
            # Спроба 3: catbox.moe (для фото <2MB)
            if not is_video and file_size_mb < 2:
                try:
                    logger.info(f"  📤 Пробуємо catbox.moe...")
                    files = {'fileToUpload': ('image.jpg', image_bytes, 'image/jpeg')}
                    data = {'reqtype': 'fileupload'}
                    response = await asyncio.to_thread(
                        requests.post,
                        "https://catbox.moe/user/api.php",
                        files=files,
                        data=data,
                        timeout=30
                    )
                    
                    logger.info(f"  📡 Catbox відповідь: HTTP {response.status_code}")
                    
                    if response.status_code == 200:
                        url = response.text.strip()
                        if url.startswith('http'):
                            logger.info(f"  ✅ Фото завантажено на catbox: {url}")
                            return url
                        else:
                            logger.warning(f"  ⚠️ Catbox повернув не-URL: {url[:100]}")
                    else:
                        logger.warning(f"  ⚠️ Catbox помилка HTTP {response.status_code}: {response.text[:200]}")
                except Exception as e:
                    logger.warning(f"  ⚠️ Catbox exception: {type(e).__name__}: {e}")
            
            logger.error(f"  ❌ Не вдалося завантажити фото на жоден сервіс")
            return None
                
        except Exception as e:
            logger.error(f"  ❌ Помилка завантаження: {e}")
            return None
        
    async def handle_channel_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обробник нових постів з каналу
        
        Args:
            update: Об'єкт оновлення від Telegram
            context: Контекст
        """
        logger.debug(f"=== handle_channel_post викликано ===")
        logger.debug(f"Update object: {update}")
        
        # Перевіряємо чи бот працює
        if not self.is_running:
            logger.info("⏸️ Бот зупинено, пост пропущено")
            return
        
        message = update.channel_post or update.message
        
        if not message:
            logger.warning("Повідомлення відсутнє в update")
            return
            
        logger.info(f"✅ Отримано новий пост з каналу!")
        logger.info(f"  📝 Message ID: {message.message_id}")
        logger.info(f"  👤 Chat ID: {message.chat.id}")
        logger.info(f"  📢 Chat username: @{message.chat.username if message.chat.username else 'N/A'}")
        logger.info(f"  📅 Date: {message.date}")
        
        try:
            # Визначаємо тип поста
            logger.debug(f"🔍 Аналізуємо тип контенту...")
            logger.debug(f"  - media_group_id: {message.media_group_id}")
            logger.debug(f"  - photo: {bool(message.photo)}")
            logger.debug(f"  - video: {bool(message.video)}")
            logger.debug(f"  - text: {bool(message.text)}")
            logger.debug(f"  - caption: {bool(message.caption)}")
            
            if message.media_group_id:
                # Медіа група (кілька фото/відео)
                logger.info(f"📦 Тип: МЕДІА ГРУПА (ID: {message.media_group_id})")
                await self._handle_media_group(update, context)
                
            elif message.photo:
                # Одне фото
                logger.info(f"🖼️ Тип: ОДНЕ ФОТО")
                await self._handle_single_photo(message)
                
            elif message.video:
                # Одне відео
                logger.info(f"🎥 Тип: ОДНЕ ВІДЕО")
                await self._handle_single_video(message)
                
            elif message.text:
                # Текстовий пост
                logger.info(f"📝 Тип: ТЕКСТОВИЙ ПОСТ")
                await self._handle_text_post(message)
                
            else:
                logger.warning(f"⚠️ Непідтримуваний тип поста: {message.message_id}")
                logger.debug(f"Об'єкт повідомлення: {message}")
                
        except Exception as e:
            logger.error(f"❌ ПОМИЛКА при обробці поста {message.message_id}: {e}", exc_info=True)
    
    async def _handle_text_post(self, message):
        """Обробка текстового поста"""
        logger.debug(f">>> _handle_text_post() викликано")
        
        text = message.text or message.caption
        
        if not text:
            logger.warning("⚠️ Пост не містить тексту")
            return
        
        # Витягуємо приховані посилання з entities
        entities = message.entities or message.caption_entities
        if entities:
            text = self._extract_links_from_entities(text, entities)
            logger.info(f"  🔗 Оброблено приховані посилання")
        
        # Очищаємо текст від "Джерело"
        text = self._clean_text(text)
            
        logger.info(f"📝 Обробляємо текстовий пост")
        logger.info(f"  📊 Довжина тексту: {len(text)} символів")
        logger.debug(f"  💬 Текст: {text[:100]}..." if len(text) > 100 else f"  💬 Текст: {text}")
        
        # Перевіряємо, чи потрібно розбивати текст
        if self.text_splitter.needs_splitting(text):
            logger.info("✂️ Текст довгий, розбиваємо на частини через GPT...")
            logger.debug(f"  🤖 Модель GPT: {config.OPENAI_MODEL}")
            
            chunks = self.text_splitter.split_text(text)
            
            if not chunks:
                logger.error("❌ Не вдалося розбити текст через GPT")
                return
            
            logger.info(f"✅ Текст розбито на {len(chunks)} частин")
            for i, chunk in enumerate(chunks, 1):
                logger.debug(f"  📄 Частина {i}: {len(chunk)} символів - {chunk[:50]}...")
                
            # Публікуємо перший пост
            logger.info(f"🚀 Публікуємо першу частину в Threads...")
            first_post_id = self.threads_api.create_and_publish_text(
                text=chunks[0],
                publish_delay=config.PUBLISH_DELAY
            )
            
            if not first_post_id:
                logger.error("❌ Не вдалося опублікувати перший пост")
                return
                
            logger.info(f"✅ Перший пост опубліковано: {first_post_id}")
            
            # Публікуємо інші частини як відповіді
            current_reply_id = first_post_id
            
            for i, chunk in enumerate(chunks[1:], start=2):
                time.sleep(config.PUBLISH_DELAY)
                
                reply_post_id = self.threads_api.create_and_publish_text(
                    text=chunk,
                    reply_to_id=current_reply_id,
                    publish_delay=config.PUBLISH_DELAY
                )
                
                if reply_post_id:
                    logger.info(f"Частина {i} опубліковано: {reply_post_id}")
                    current_reply_id = reply_post_id
                else:
                    logger.error(f"Не вдалося опублікувати частину {i}")
                    break
                    
            logger.info(f"✅ Пост успішно опубліковано ({len(chunks)} частин)")
            # Зберігаємо статистику
            self.database.add_post(message.message_id, first_post_id, 'text', 'success')
            
            # Додаємо рекламний пост до останньої частини
            await self._add_promo_post(current_reply_id)
            
        else:
            # Публікуємо короткий текст
            post_id = self.threads_api.create_and_publish_text(
                text=text,
                publish_delay=config.PUBLISH_DELAY
            )
            
            if post_id:
                logger.info(f"✅ Пост успішно опубліковано: {post_id}")
                # Зберігаємо статистику
                self.database.add_post(message.message_id, post_id, 'text', 'success')
                # Додаємо рекламний пост
                await self._add_promo_post(post_id)
            else:
                logger.error("Не вдалося опублікувати пост")
                self.database.add_post(message.message_id, None, 'text', 'error', "Не вдалося опублікувати")
    
    async def _handle_single_photo(self, message):
        """Обробка поста з одним фото"""
        logger.debug(">>> _handle_single_photo() викликано")
        logger.info("📸 Обробляємо пост з фото")
        
        try:
            # Беремо найбільше фото
            photo: PhotoSize = message.photo[-1]
            logger.debug(f"  Розмір фото: {photo.width}x{photo.height}, file_id: {photo.file_id}")
            
            # Отримуємо інформацію про файл з retry логікою
            max_retries = 3
            file = None
            for attempt in range(max_retries):
                try:
                    logger.debug(f"  Спроба {attempt + 1}/{max_retries} отримати file info...")
                    file = await photo.get_file()
                    logger.debug(f"  ✅ File info отримано: {file.file_path}")
                    break
                except Exception as e:
                    logger.warning(f"  ⚠️ Спроба {attempt + 1} невдала: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                    else:
                        raise
            
            # Завантажуємо фото локально
            logger.info("  📥 Завантажуємо фото з Telegram...")
            photo_bytes = await file.download_as_bytearray()
            logger.info(f"  ✅ Фото завантажено: {len(photo_bytes)} байт")
            
            # Загружаємо на imgbb.com (публічний хостинг)
            logger.info("  ☁️ Загружаємо фото на публічний хостинг...")
            photo_url = await self._upload_to_imgbb(photo_bytes)
            
            if not photo_url:
                logger.error("❌ Не вдалося загрузити фото на хостинг")
                return
                
            logger.info(f"  📎 Photo URL: {photo_url}")
        except Exception as e:
            logger.error(f"❌ Не вдалося отримати URL фото: {e}")
            return
        
        text = message.caption if message.caption else None
        
        # Витягуємо приховані посилання з entities
        if text:
            entities = message.caption_entities
            if entities:
                text = self._extract_links_from_entities(text, entities)
                logger.info(f"  🔗 Оброблено приховані посилання")
        
        # Очищаємо текст від "Джерело"
        if text:
            text = self._clean_text(text)
        
        # Перевіряємо довжину тексту
        if text and self.text_splitter.needs_splitting(text):
            logger.info("Текст до фото довгий, розбиваємо")
            chunks = self.text_splitter.split_text(text)
            
            if not chunks:
                logger.error("Не вдалося розбити текст")
                return
                
            # Створюємо медіа пост з першою частиною тексту
            creation_id = self.threads_api.create_media_post(
                media_url=photo_url,
                media_type=MediaType.IMAGE,
                text=chunks[0]
            )
            
            if not creation_id:
                logger.error("Не вдалося створити медіа пост")
                return
                
            time.sleep(config.PUBLISH_DELAY)
            first_post_id = self.threads_api.publish_post(creation_id)
            
            if not first_post_id:
                logger.error("Не вдалося опублікувати медіа пост")
                return
                
            logger.info(f"Медіа пост опубліковано: {first_post_id}")
            
            # Публікуємо інші частини як відповіді
            current_reply_id = first_post_id
            
            for i, chunk in enumerate(chunks[1:], start=2):
                time.sleep(config.PUBLISH_DELAY)
                
                reply_post_id = self.threads_api.create_and_publish_text(
                    text=chunk,
                    reply_to_id=current_reply_id,
                    publish_delay=config.PUBLISH_DELAY
                )
                
                if reply_post_id:
                    logger.info(f"Частина {i} опубліковано: {reply_post_id}")
                    current_reply_id = reply_post_id
                else:
                    logger.error(f"Не вдалося опублікувати частину {i}")
                    break
                    
            logger.info(f"✅ Медіа пост успішно опубліковано ({len(chunks)} частин)")
            
            # Додаємо рекламний пост до останньої частини
            await self._add_promo_post(current_reply_id)
            
        else:
            # Публікуємо просто фото з текстом
            creation_id = self.threads_api.create_media_post(
                media_url=photo_url,
                media_type=MediaType.IMAGE,
                text=text
            )
            
            if not creation_id:
                logger.error("Не вдалося створити медіа пост")
                return
                
            time.sleep(config.PUBLISH_DELAY)
            post_id = self.threads_api.publish_post(creation_id)
            
            if post_id:
                logger.info(f"✅ Медіа пост успішно опубліковано: {post_id}")
                # Зберігаємо статистику
                self.database.add_post(message.message_id, post_id, 'photo', 'success')
                # Додаємо рекламний пост
                await self._add_promo_post(post_id)
            else:
                logger.error("Не вдалося опублікувати медіа пост")
                self.database.add_post(message.message_id, None, 'photo', 'error', "Не вдалося опублікувати")
    
    async def _handle_single_video(self, message):
        """Обробка поста з одним відео"""
        logger.debug(">>> _handle_single_video() викликано")
        logger.info("🎥 Обробляємо пост з відео")
        
        try:
            # Отримуємо відео
            video = message.video
            logger.debug(f"  Розмір відео: {video.width}x{video.height}, file_id: {video.file_id}")
            
            # Отримуємо файл з retry логікою
            max_retries = 3
            file = None
            for attempt in range(max_retries):
                try:
                    logger.debug(f"  Спроба {attempt + 1}/{max_retries} отримати file info...")
                    file = await video.get_file()
                    logger.debug(f"  ✅ File info отримано: {file.file_path}")
                    break
                except Exception as e:
                    logger.warning(f"  ⚠️ Спроба {attempt + 1} невдала: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                    else:
                        raise
            
            # Завантажуємо відео локально
            logger.info("  📥 Завантажуємо відео з Telegram...")
            video_bytes = await file.download_as_bytearray()
            logger.info(f"  ✅ Відео завантажено: {len(video_bytes)} байт ({len(video_bytes) / 1024 / 1024:.1f} MB)")
            
            # Загружаємо на file.io (підтримує великі файли)
            logger.info("  ☁️ Загружаємо відео на file.io...")
            video_url = await self._upload_to_imgbb(video_bytes, is_video=True)
            
            if not video_url:
                logger.error("❌ Не вдалося загрузити відео на хостинг")
                return
                
            logger.info(f"  📎 Video URL: {video_url}")
        except Exception as e:
            logger.error(f"❌ Не вдалося отримати URL відео: {e}")
            return
        
        text = message.caption if message.caption else None
        
        # Витягуємо приховані посилання з entities
        if text:
            entities = message.caption_entities
            if entities:
                text = self._extract_links_from_entities(text, entities)
                logger.info(f"  🔗 Оброблено приховані посилання")
        
        # Очищаємо текст від "Джерело"
        if text:
            text = self._clean_text(text)
        
        # Аналогічно до фото
        if text and self.text_splitter.needs_splitting(text):
            chunks = self.text_splitter.split_text(text)
            
            if not chunks:
                logger.error("Не вдалося розбити текст")
                return
                
            creation_id = self.threads_api.create_media_post(
                media_url=video_url,
                media_type=MediaType.VIDEO,
                text=chunks[0]
            )
            
            if not creation_id:
                logger.error("Не вдалося створити відео пост")
                return
                
            time.sleep(config.PUBLISH_DELAY)
            first_post_id = self.threads_api.publish_post(
                creation_id,
                max_checks=config.MAX_STATUS_CHECKS,
                check_delay=config.STATUS_CHECK_DELAY
            )
            
            if not first_post_id:
                logger.error("Не вдалося опублікувати відео пост")
                return
                
            logger.info(f"Відео пост опубліковано: {first_post_id}")
            
            # Публікуємо інші частини
            current_reply_id = first_post_id
            
            for i, chunk in enumerate(chunks[1:], start=2):
                time.sleep(config.PUBLISH_DELAY)
                
                reply_post_id = self.threads_api.create_and_publish_text(
                    text=chunk,
                    reply_to_id=current_reply_id,
                    publish_delay=config.PUBLISH_DELAY
                )
                
                if reply_post_id:
                    logger.info(f"Частина {i} опубліковано: {reply_post_id}")
                    current_reply_id = reply_post_id
                else:
                    logger.error(f"Не вдалося опублікувати частину {i}")
                    break
                    
            logger.info(f"✅ Відео пост успішно опубліковано ({len(chunks)} частин)")
            # Зберігаємо статистику
            self.database.add_post(message.message_id, first_post_id, 'video', 'success')
            
            # Додаємо рекламний пост до останньої частини
            await self._add_promo_post(current_reply_id)
            
        else:
            creation_id = self.threads_api.create_media_post(
                media_url=video_url,
                media_type=MediaType.VIDEO,
                text=text
            )
            
            if not creation_id:
                logger.error("Не вдалося створити відео пост")
                return
                
            time.sleep(config.PUBLISH_DELAY)
            post_id = self.threads_api.publish_post(
                creation_id,
                max_checks=config.MAX_STATUS_CHECKS,
                check_delay=config.STATUS_CHECK_DELAY
            )
            
            if post_id:
                logger.info(f"✅ Відео пост успішно опубліковано: {post_id}")
                # Зберігаємо статистику
                self.database.add_post(message.message_id, post_id, 'video', 'success')
                # Додаємо рекламний пост
                await self._add_promo_post(post_id)
            else:
                logger.error("Не вдалося опублікувати відео пост")
                self.database.add_post(message.message_id, None, 'video', 'error', "Не вдалося опублікувати")
    
    async def _handle_media_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обробка медіа групи (кілька фото/відео)
        
        Примітка: Telegram надсилає кожне фото/відео окремим повідомленням,
        але з однаковим media_group_id. Потрібно зібрати всі елементи групи.
        """
        logger.info("Обробляємо медіа групу")
        
        message = update.channel_post
        media_group_id = message.media_group_id
        
        # Зберігаємо повідомлення в контексті
        if 'media_groups' not in context.bot_data:
            context.bot_data['media_groups'] = {}
            
        if media_group_id not in context.bot_data['media_groups']:
            context.bot_data['media_groups'][media_group_id] = {
                'messages': [],
                'processed': False
            }
            
        context.bot_data['media_groups'][media_group_id]['messages'].append(message)
        
        # Чекаємо трохи, щоб зібрати всі елементи групи (використовуємо asyncio замість job_queue)
        # Якщо це перше повідомлення в групі, запускаємо обробку через 3 секунди
        if len(context.bot_data['media_groups'][media_group_id]['messages']) == 1:
            asyncio.create_task(self._delayed_process_media_group(context, media_group_id))
    
    async def _delayed_process_media_group(self, context: ContextTypes.DEFAULT_TYPE, media_group_id: str):
        """Відкладена обробка медіа групи через 3 секунди"""
        await asyncio.sleep(3)
        await self._process_media_group(context, media_group_id)
    
    async def _process_media_group(self, context: ContextTypes.DEFAULT_TYPE, media_group_id: str):
        """Обробка зібраної медіа групи"""
        
        if media_group_id not in context.bot_data.get('media_groups', {}):
            return
            
        group_data = context.bot_data['media_groups'][media_group_id]
        
        if group_data['processed']:
            return
            
        group_data['processed'] = True
        messages = group_data['messages']
        
        logger.info(f"Обробляємо медіа групу з {len(messages)} елементів")
        
        # Створюємо елементи каруселі
        media_ids = []
        
        for i, msg in enumerate(messages, 1):
            try:
                if msg.photo:
                    logger.info(f"  Обробляємо фото {i}/{len(messages)}")
                    photo = msg.photo[-1]
                    
                    # Детальна інформація про фото
                    logger.info(f"    📸 Розміри: {photo.width}x{photo.height} px")
                    logger.info(f"    📝 File ID: {photo.file_id[:30]}...")
                    
                    file = await photo.get_file()
                    
                    # Завантажуємо фото з Telegram
                    logger.debug(f"    Завантажуємо фото з Telegram...")
                    photo_bytes = await file.download_as_bytearray()
                    file_size_mb = len(photo_bytes) / 1024 / 1024
                    logger.info(f"    💾 Розмір файлу: {file_size_mb:.2f} MB ({len(photo_bytes)} байт)")
                    
                    # Визначаємо формат за сигнатурою
                    if photo_bytes[:8] == b'\x89PNG\r\n\x1a\n':
                        photo_format = "PNG"
                    elif photo_bytes[:2] == b'\xff\xd8':
                        photo_format = "JPEG"
                    else:
                        photo_format = "Unknown"
                    logger.info(f"    🎨 Формат: {photo_format}")
                    
                    # Загружаємо на публічний хостинг (метод вже має fallback Telegraph→catbox)
                    logger.debug(f"    Загружаємо на публічний хостинг...")
                    photo_url = await self._upload_to_imgbb(photo_bytes, is_video=False)
                    
                    if not photo_url:
                        logger.error(f"    ❌ Не вдалося завантажити фото {i}")
                        continue
                    
                    logger.info(f"    ✅ Фото завантажено: {photo_url}")
                    logger.info(f"    📏 Довжина URL: {len(photo_url)} символів")
                    
                    logger.info(f"    ⏳ Створюємо елемент каруселі в Threads API...")
                    creation_id = self.threads_api.create_media_post(
                        media_url=photo_url,
                        media_type=MediaType.IMAGE,
                        is_carousel_item=True
                    )
                    
                elif msg.video:
                    logger.info(f"  Обробляємо відео {i}/{len(messages)}")
                    video = msg.video
                    file = await video.get_file()
                    
                    # Завантажуємо відео з Telegram
                    logger.debug(f"    Завантажуємо відео з Telegram...")
                    video_bytes = await file.download_as_bytearray()
                    logger.debug(f"    Завантажено: {len(video_bytes)} байт")
                    
                    # Загружаємо на публічний хостинг (Imgur для відео)
                    logger.debug(f"    Загружаємо відео на Imgur...")
                    video_url = await self._upload_to_imgbb(video_bytes, is_video=True)
                    
                    if not video_url:
                        logger.error(f"    ❌ Не вдалося завантажити відео {i}")
                        continue
                    
                    logger.info(f"    ✅ Відео завантажено: {video_url[:50]}...")
                    
                    creation_id = self.threads_api.create_media_post(
                        media_url=video_url,
                        media_type=MediaType.VIDEO,
                        is_carousel_item=True
                    )
                else:
                    continue
                    
                if creation_id:
                    logger.info(f"    ✅ Елемент каруселі створено: {creation_id}")
                    media_ids.append(creation_id)
                    logger.info(f"    ⏸️  Затримка 5 секунд перед наступним елементом...")
                    time.sleep(5)  # Затримка між створенням елементів (збільшено з 2 до 5)
                else:
                    logger.error(f"    ❌ Не вдалося створити елемент каруселі {i}")
                    
            except Exception as e:
                logger.error(f"    ❌ Помилка при обробці елемента {i}: {e}")
                
        if not media_ids:
            logger.error("Не вдалося створити жодного елемента каруселі")
            return
            
        # Беремо текст з першого повідомлення (якщо є)
        text = messages[0].caption if messages[0].caption else None
        
        # Витягуємо приховані посилання з entities
        if text:
            entities = messages[0].caption_entities
            if entities:
                text = self._extract_links_from_entities(text, entities)
                logger.info(f"  🔗 Оброблено приховані посилання в caption")
        
        # Очищаємо текст від "Джерело"
        if text:
            text = self._clean_text(text)
        
        # Threads API вимагає мінімум 2 елементи для каруселі
        if len(media_ids) < 2:
            logger.error(f"⚠️ Недостатньо елементів для каруселі: {len(media_ids)}/мінімум 2")
            logger.error("Threads API вимагає мінімум 2 медіа елементи для каруселі")
            # Очищаємо дані групи
            del context.bot_data['media_groups'][media_group_id]
            return
        
        # Створюємо карусель
        logger.info("⏳ Чекаємо 30 секунд, щоб Threads API обробив всі відео елементи...")
        time.sleep(30)  # Threads API потребує більше часу для обробки відео в каруселі
        
        # Перевіряємо довжину тексту для каруселі
        # Для каруселей ліміт менший (200 символів), бо текст URL-кодується
        # і кириличні символи займають ~3x більше місця
        CAROUSEL_TEXT_LIMIT = 200
        
        carousel_text = None
        remaining_text = None
        
        if text:
            if len(text) > CAROUSEL_TEXT_LIMIT:
                logger.info(f"⚠️ Текст довгий ({len(text)} символів), розбиваємо розумно через GPT")
                
                # Розбиваємо текст розумно через GPT
                split_result = self.text_splitter.split_for_carousel(text, CAROUSEL_TEXT_LIMIT)
                
                if split_result:
                    carousel_text, remaining_text = split_result
                    logger.info(f"✅ Розбито: карусель {len(carousel_text)} символів, залишок {len(remaining_text) if remaining_text else 0} символів")
                else:
                    # Якщо GPT не спрацював, обрізаємо по останньому пробілу
                    logger.warning("GPT не спрацював, обрізаємо по останньому пробілу")
                    carousel_text = text[:CAROUSEL_TEXT_LIMIT].rsplit(' ', 1)[0]
                    remaining_text = text[len(carousel_text):].strip()
            else:
                # Весь текст в карусель
                carousel_text = text
        
        # Створюємо і публікуємо карусель з текстом (або без нього)
        carousel_id = self.threads_api.create_carousel_post(media_ids, carousel_text)
        
        if not carousel_id:
            logger.error("Не вдалося створити карусель")
            return
            
        time.sleep(config.PUBLISH_DELAY)
        post_id = self.threads_api.publish_post(
            carousel_id,
            max_checks=config.MAX_STATUS_CHECKS,
            check_delay=config.STATUS_CHECK_DELAY
        )
        
        if not post_id:
            logger.error("Не вдалося опублікувати карусель")
            return
            
        logger.info(f"✅ Карусель опубліковано: {post_id}")
        
        # Якщо є залишок тексту, розбиваємо через GPT і публікуємо як коментарі
        if remaining_text:
            logger.info(f"📝 Публікуємо залишок тексту ({len(remaining_text)} символів) як коментарі")
            
            chunks = self.text_splitter.split_text(remaining_text)
            
            if not chunks:
                logger.warning("Не вдалося розбити текст, публікуємо як є")
                chunks = [remaining_text[:450]]  # Обрізаємо до 450 якщо GPT не спрацював
            
            current_reply_id = post_id
            
            for i, chunk in enumerate(chunks, start=1):
                time.sleep(config.PUBLISH_DELAY)
                
                reply_post_id = self.threads_api.create_and_publish_text(
                    text=chunk,
                    reply_to_id=current_reply_id,
                    publish_delay=config.PUBLISH_DELAY
                )
                
                if reply_post_id:
                    logger.info(f"Коментар {i} опубліковано: {reply_post_id}")
                    current_reply_id = reply_post_id
                else:
                    logger.error(f"Не вдалося опублікувати коментар {i}")
                    break
            
            # Додаємо промо до останнього коментаря
            await self._add_promo_post(current_reply_id)
        else:
            # Немає залишку тексту, додаємо промо просто до каруселі
            await self._add_promo_post(post_id)
        
        # Очищаємо дані групи
        del context.bot_data['media_groups'][media_group_id]
    
    # ==================== АДМІН КОМАНДИ ====================
    
    async def cmd_start_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start - привітання з меню"""
        if update.effective_chat.id != config.ADMIN_ID:
            return
        
        await update.message.reply_text(
            "🎛️ *АДМІН-ПАНЕЛЬ THREADS BOT*\n\n"
            "Виберіть дію з меню нижче або використовуйте команди:\n\n"
            "📊 Статус - поточний стан бота\n"
            "📈 Статистика - звіт по постах\n"
            "📝 Логи - останні операції\n"
            "❌ Помилки - тільки помилки\n"
            "🔧 API Статус - перевірка API\n"
            "💬 Промо текст - налаштування\n"
            "▶️ Запустити / ⏸️ Зупинити\n"
            "❓ Допомога - список команд",
            parse_mode='Markdown',
            reply_markup=self._get_admin_keyboard()
        )
        logger.info("✅ Адмінка відкрита через команду /start")
    
    async def cmd_stop_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stop - зупинка бота"""
        if update.effective_chat.id != config.ADMIN_ID:
            return
        
        self.is_running = False
        await update.message.reply_text(
            "⏸️ *БОТ ЗУПИНЕНО*\n\n"
            "Автопублікація призупинена. Нові пости не будуть публікуватись.\n"
            "Для запуску використовуйте /start",
            parse_mode='Markdown'
        )
        logger.info("⏸️ Бот зупинено через команду /stop")
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /status - поточний стан"""
        if update.effective_chat.id != config.ADMIN_ID:
            return
        
        stats = self.database.get_stats(days=1)
        
        status_icon = "✅" if self.is_running else "⏸️"
        status_text = "працює" if self.is_running else "зупинено"
        
        # Форматування часу останнього поста
        last_post_info = "Немає постів"
        if stats['last_post']:
            from datetime import datetime
            last_time = datetime.fromisoformat(stats['last_post'][0])
            time_diff = datetime.now() - last_time
            minutes = int(time_diff.total_seconds() / 60)
            
            if minutes < 1:
                last_post_info = "Щойно"
            elif minutes < 60:
                last_post_info = f"{minutes} хв назад"
            else:
                hours = minutes // 60
                last_post_info = f"{hours} год назад"
        
        message = (
            f"{status_icon} *СТАТУС БОТА*\n\n"
            f"{'✅' if self.is_running else '❌'} Бот {status_text}\n"
            f"📊 Опубліковано сьогодні: *{stats['total_posts']}* постів\n"
            f"⏰ Останній пост: {last_post_info}\n"
        )
        
        if stats['by_type']:
            message += "\n📝 Типи:\n"
            type_icons = {
                'photo': '📸',
                'video': '🎥',
                'text': '📝',
                'carousel': '🎡'
            }
            for ptype, count in stats['by_type'].items():
                icon = type_icons.get(ptype, '📄')
                message += f"  {icon} {ptype}: {count}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats - статистика"""
        if update.effective_chat.id != config.ADMIN_ID:
            return
        
        stats_today = self.database.get_stats(days=1)
        stats_week = self.database.get_stats(days=7)
        
        message = (
            "📊 *СТАТИСТИКА*\n\n"
            f"*Сьогодні:*\n"
            f"  ✅ Опубліковано: {stats_today['total_posts']} постів\n"
            f"  ❌ Помилки: {stats_today['total_errors']}\n\n"
            f"*За тиждень:*\n"
            f"  ✅ Опубліковано: {stats_week['total_posts']} постів\n"
            f"  ❌ Помилки: {stats_week['total_errors']}\n\n"
        )
        
        if stats_week['by_type']:
            message += "*Типи контенту (тиждень):*\n"
            type_icons = {
                'photo': '📸',
                'video': '🎥',
                'text': '📝',
                'carousel': '🎡'
            }
            for ptype, count in stats_week['by_type'].items():
                icon = type_icons.get(ptype, '📄')
                message += f"  {icon} {ptype.title()}: {count}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /logs - останні логи"""
        if update.effective_chat.id != config.ADMIN_ID:
            return
        
        logs = self.database.get_recent_logs(limit=15)
        
        if not logs:
            await update.message.reply_text("📋 Логів поки немає")
            return
        
        message = "📋 *ОСТАННІ ЛОГИ*\n\n"
        
        status_icons = {
            'success': '✅',
            'error': '❌'
        }
        
        type_icons = {
            'photo': '📸',
            'video': '🎥',
            'text': '📝',
            'carousel': '🎡'
        }
        
        for log in logs:
            from datetime import datetime
            time = datetime.fromisoformat(log['created_at']).strftime('%H:%M')
            status = status_icons.get(log['status'], '❓')
            ptype = type_icons.get(log['post_type'], '📄')
            
            message += f"`[{time}]` {status} {ptype} #{log['telegram_id']}"
            
            if log['status'] == 'error' and log['error_message']:
                error_short = log['error_message'][:30]
                message += f"\n  ⚠️ _{error_short}_"
            
            message += "\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_errors(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /errors - тільки помилки"""
        if update.effective_chat.id != config.ADMIN_ID:
            return
        
        logs = self.database.get_recent_logs(limit=10, errors_only=True)
        
        if not logs:
            await update.message.reply_text("✅ Помилок немає!")
            return
        
        message = "❌ *ОСТАННІ ПОМИЛКИ*\n\n"
        
        type_icons = {
            'photo': '📸',
            'video': '🎥',
            'text': '📝',
            'carousel': '🎡'
        }
        
        for log in logs:
            from datetime import datetime
            time = datetime.fromisoformat(log['created_at']).strftime('%d.%m %H:%M')
            ptype = type_icons.get(log['post_type'], '📄')
            
            message += f"`[{time}]` {ptype} #{log['telegram_id']}\n"
            if log['error_message']:
                error_short = log['error_message'][:50]
                message += f"  ⚠️ _{error_short}_\n"
            message += "\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_set_promo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /set_promo - змінити промо текст"""
        if update.effective_chat.id != config.ADMIN_ID:
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Використання: `/set_promo текст`\n\n"
                "Приклад:\n"
                "`/set_promo 📌 Підписуйтесь на канал!`",
                parse_mode='Markdown'
            )
            return
        
        new_promo = ' '.join(context.args)
        self.promo_text = new_promo
        self.database.set_setting('promo_text', new_promo)
        
        await update.message.reply_text(
            f"✅ *ПРОМО ТЕКСТ ОНОВЛЕНО*\n\n{new_promo}",
            parse_mode='Markdown'
        )
        logger.info(f"Промо текст змінено: {new_promo[:50]}...")
    
    async def cmd_get_promo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /get_promo - показати промо текст"""
        if update.effective_chat.id != config.ADMIN_ID:
            return
        
        await update.message.reply_text(
            f"📌 *ПОТОЧНИЙ ПРОМО ТЕКСТ:*\n\n{self.promo_text}",
            parse_mode='Markdown'
        )
    
    async def cmd_check_api(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /check_api - перевірка всіх API"""
        if update.effective_chat.id != config.ADMIN_ID:
            return
        
        await update.message.reply_text("🔍 Перевіряю API...")
        
        results = []
        
        # Telegram Bot API
        try:
            await update.get_bot().get_me()
            results.append("✅ Telegram Bot API")
        except:
            results.append("❌ Telegram Bot API")
        
        # Threads API (перевіримо через просте запит)
        try:
            import requests
            response = requests.get(
                f"https://graph.threads.net/v1.0/{config.THREADS_USER_ID}",
                params={'access_token': config.THREADS_ACCESS_TOKEN},
                timeout=10
            )
            if response.status_code in [200, 400]:  # 400 теж ок, значить API відповідає
                results.append("✅ Threads API")
            else:
                results.append("❌ Threads API")
        except:
            results.append("❌ Threads API")
        
        # OpenAI API
        try:
            from openai import OpenAI
            client = OpenAI(api_key=config.OPENAI_API_KEY)
            client.models.list()
            results.append("✅ OpenAI API")
        except:
            results.append("❌ OpenAI API")
        
        # Telegraph
        try:
            response = requests.get("https://telegra.ph", timeout=5)
            if response.status_code == 200:
                results.append("✅ Telegraph")
            else:
                results.append("⚠️ Telegraph")
        except:
            results.append("❌ Telegraph")
        
        # Catbox
        try:
            response = requests.get("https://catbox.moe", timeout=5)
            if response.status_code == 200:
                results.append("✅ Catbox")
            else:
                results.append("⚠️ Catbox")
        except:
            results.append("❌ Catbox")
        
        # Imgur
        try:
            response = requests.get("https://imgur.com", timeout=5)
            if response.status_code == 200:
                results.append("✅ Imgur")
            else:
                results.append("⚠️ Imgur")
        except:
            results.append("❌ Imgur")
        
        message = "🔍 *ПЕРЕВІРКА API:*\n\n" + "\n".join(results)
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help - допомога"""
        if update.effective_chat.id != config.ADMIN_ID:
            return
        
        message = (
            "🎛️ *КОМАНДИ АДМІНКИ*\n\n"
            "*Управління:*\n"
            "/start - Запустити бота\n"
            "/stop - Зупинити бота\n"
            "/status - Поточний стан\n\n"
            "*Статистика:*\n"
            "/stats - Статистика постів\n"
            "/logs - Останні 15 логів\n"
            "/errors - Тільки помилки\n\n"
            "*Налаштування:*\n"
            "/set\\_promo [текст] - Змінити промо\n"
            "/get\\_promo - Показати промо\n\n"
            "*Тестування:*\n"
            "/check\\_api - Перевірка всіх API\n\n"
            "/help - Ця допомога"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=self._get_admin_keyboard())
    
    async def handle_button_press(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка натискання кнопок меню"""
        if update.effective_chat.id != config.ADMIN_ID:
            return
        
        text = update.message.text
        
        # Маршрутизація кнопок до відповідних команд
        if text == "📊 Статус":
            await self.cmd_status(update, context)
        elif text == "📈 Статистика":
            await self.cmd_stats(update, context)
        elif text == "📝 Логи":
            await self.cmd_logs(update, context)
        elif text == "❌ Помилки":
            await self.cmd_errors(update, context)
        elif text == "🔧 API Статус":
            await self.cmd_check_api(update, context)
        elif text == "💬 Промо текст":
            await self.cmd_get_promo(update, context)
        elif text == "▶️ Запустити":
            self.is_running = True
            await update.message.reply_text(
                "✅ *БОТ ЗАПУЩЕНО*\n\n"
                "Автопублікація постів з Telegram у Threads активна.",
                parse_mode='Markdown'
            )
            logger.info("✅ Бот запущено через кнопку")
        elif text == "⏸️ Зупинити":
            self.is_running = False
            await update.message.reply_text(
                "⏸️ *БОТ ЗУПИНЕНО*\n\n"
                "Автопублікація призупинена. Для запуску натисніть '▶️ Запустити'.",
                parse_mode='Markdown'
            )
            logger.info("⏸️ Бот зупинено через кнопку")
        elif text == "❓ Допомога":
            await self.cmd_help(update, context)
    
    # ==================== КІНЕЦЬ АДМІН КОМАНД ====================
    
    def run(self):
        """Запуск боту"""
        logger.info("=" * 60)
        logger.info("🚀 ЗАПУСК THREADS BOT")
        logger.info("=" * 60)
        logger.info(f"📋 Конфігурація:")
        logger.info(f"  🤖 Telegram Bot Token: {config.TELEGRAM_BOT_TOKEN[:20]}...")
        logger.info(f"  📢 Telegram Channel: {config.TELEGRAM_CHANNEL_ID}")
        logger.info(f"  🧵 Threads User ID: {config.THREADS_USER_ID}")
        logger.info(f"  🔑 Threads Token: {config.THREADS_ACCESS_TOKEN[:30]}...")
        logger.info(f"  🤖 OpenAI Model: {config.OPENAI_MODEL}")
        logger.info(f"  📏 Max Text Length: {config.MAX_TEXT_LENGTH}")
        logger.info("=" * 60)
        
        try:
            # Створюємо додаток
            logger.debug("Створюємо Telegram Application...")
            application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
            logger.debug("✅ Application створено")
            
            # Додаємо обробники команд для адмінки
            logger.debug("Додаємо обробники адмін-команд...")
            application.add_handler(CommandHandler("start", self.cmd_start_bot))
            application.add_handler(CommandHandler("stop", self.cmd_stop_bot))
            application.add_handler(CommandHandler("status", self.cmd_status))
            application.add_handler(CommandHandler("stats", self.cmd_stats))
            application.add_handler(CommandHandler("logs", self.cmd_logs))
            application.add_handler(CommandHandler("errors", self.cmd_errors))
            application.add_handler(CommandHandler("set_promo", self.cmd_set_promo))
            application.add_handler(CommandHandler("get_promo", self.cmd_get_promo))
            application.add_handler(CommandHandler("check_api", self.cmd_check_api))
            application.add_handler(CommandHandler("help", self.cmd_help))
            logger.debug("✅ Адмін-команди додано")
            
            # Додаємо обробник кнопок адмінки
            logger.debug("Додаємо обробник кнопок...")
            application.add_handler(
                MessageHandler(
                    filters.ChatType.PRIVATE & ~filters.COMMAND & filters.TEXT,
                    self.handle_button_press
                )
            )
            logger.debug("✅ Обробник кнопок додано")
            
            # Додаємо обробник постів з каналу
            logger.debug("Додаємо обробники повідомлень...")
            application.add_handler(
                MessageHandler(
                    filters.Chat(chat_id=config.TELEGRAM_CHANNEL_ID) & filters.ChatType.CHANNEL & ~filters.COMMAND,
                    self.handle_channel_post
                )
            )
            logger.debug(f"✅ Обробник для каналу {config.TELEGRAM_CHANNEL_ID} додано")
            
            logger.info("")
            logger.info("✅ БОТ ГОТОВИЙ ДО РОБОТИ!")
            logger.info(f"👂 Слухаємо канал: {config.TELEGRAM_CHANNEL_ID}")
            logger.info(f"📊 Рівень логування: {config.LOG_LEVEL}")
            logger.info(f"📝 Лог файл: {config.LOG_FILE}")
            logger.info("")
            logger.info("💡 Опублікуйте пост у вашому каналі для тестування")
            logger.info("🛑 Натисніть Ctrl+C для зупинки")
            logger.info("=" * 60)
            
            # Запускаємо бота
            logger.debug("Запускаємо polling...")
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
        except Exception as e:
            logger.error(f"❌ КРИТИЧНА ПОМИЛКА при запуску бота: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    bot = ThreadsBot()
    bot.run()

