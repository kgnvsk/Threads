"""
Модуль для роботи з Threads API
"""
import time
import logging
import requests
from typing import Optional, Dict, List, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class MediaType(Enum):
    """Типи медіа для Threads"""
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    CAROUSEL = "CAROUSEL"


class PublishStatus(Enum):
    """Статуси публікації"""
    FINISHED = "FINISHED"
    IN_PROGRESS = "IN_PROGRESS"
    ERROR = "ERROR"
    PUBLISHED = "PUBLISHED"


class ThreadsAPI:
    """Клас для роботи з Threads API"""
    
    BASE_URL = "https://graph.threads.net/v1.0"
    
    def __init__(self, user_id: str, access_token: str):
        """
        Ініціалізація Threads API клієнта
        
        Args:
            user_id: ID користувача Threads
            access_token: Access token для API
        """
        self.user_id = user_id
        self.access_token = access_token
        
    def create_text_post(self, text: str, reply_to_id: Optional[str] = None) -> Optional[str]:
        """
        Створення текстового поста
        
        Args:
            text: Текст поста
            reply_to_id: ID поста, на який відповідаємо (для створення ланцюжка)
            
        Returns:
            creation_id або None у випадку помилки
        """
        logger.debug(f">>> create_text_post() викликано")
        logger.debug(f"  Довжина тексту: {len(text)} символів")
        logger.debug(f"  Reply to ID: {reply_to_id}")
        
        url = f"{self.BASE_URL}/{self.user_id}/threads"
        
        params = {
            "media_type": MediaType.TEXT.value,
            "text": text,
            "access_token": self.access_token
        }
        
        if reply_to_id:
            params["reply_to_id"] = reply_to_id
            
        logger.debug(f"🌐 API Request:")
        logger.debug(f"  URL: {url}")
        logger.debug(f"  Params: {dict((k, v[:30]+'...' if k == 'access_token' else v) for k, v in params.items())}")
            
        try:
            logger.debug(f"📤 Надсилаємо POST запит...")
            response = requests.post(url, params=params, timeout=30)
            logger.debug(f"📥 Отримано відповідь: Status {response.status_code}")
            
            response.raise_for_status()
            data = response.json()
            logger.debug(f"  Response JSON: {data}")
            
            creation_id = data.get("id")
            logger.info(f"✅ Текстовий пост створено: {creation_id}")
            return creation_id
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Помилка при створенні текстового поста: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"  📄 Status Code: {e.response.status_code}")
                logger.error(f"  📄 Відповідь API: {e.response.text}")
            return None
    
    def create_media_post(
        self,
        media_url: str,
        media_type: MediaType,
        text: Optional[str] = None,
        is_carousel_item: bool = False
    ) -> Optional[str]:
        """
        Створення поста з медіа (фото або відео)
        
        Args:
            media_url: URL медіа файлу
            media_type: Тип медіа (IMAGE або VIDEO)
            text: Текст поста (опціонально)
            is_carousel_item: Чи є це елемент каруселі
            
        Returns:
            creation_id або None у випадку помилки
        """
        url = f"{self.BASE_URL}/{self.user_id}/threads"
        
        params = {
            "media_type": media_type.value,
            "access_token": self.access_token
        }
        
        # Додаємо URL медіа залежно від типу
        if media_type == MediaType.IMAGE:
            params["image_url"] = media_url
        elif media_type == MediaType.VIDEO:
            params["video_url"] = media_url
            
        if text:
            params["text"] = text
            
        if is_carousel_item:
            params["is_carousel_item"] = "true"
            
        # Retry для 500 помилок (до 5 спроб)
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = requests.post(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                creation_id = data.get("id")
                logger.info(f"Медіа пост створено: {creation_id}")
                return creation_id
                
            except requests.exceptions.RequestException as e:
                is_500_error = hasattr(e, 'response') and e.response is not None and e.response.status_code == 500
                
                if is_500_error and attempt < max_retries - 1:
                    logger.warning(f"Threads API 500 помилка, спроба {attempt + 1}/{max_retries}, чекаємо 10 секунд...")
                    time.sleep(10)
                    continue
                    
                logger.error(f"Помилка при створенні медіа поста: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Відповідь API: {e.response.text}")
                return None
    
    def create_carousel_post(
        self,
        media_ids: List[str],
        text: Optional[str] = None
    ) -> Optional[str]:
        """
        Створення каруселі (медіа група)
        
        Args:
            media_ids: Список ID медіа елементів
            text: Текст поста
            
        Returns:
            creation_id або None у випадку помилки
        """
        url = f"{self.BASE_URL}/{self.user_id}/threads"
        
        params = {
            "media_type": MediaType.CAROUSEL.value,
            "children": ",".join(media_ids),
            "access_token": self.access_token
        }
        
        if text:
            params["text"] = text
            
        try:
            response = requests.post(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            creation_id = data.get("id")
            logger.info(f"Карусель створено: {creation_id}")
            return creation_id
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка при створенні каруселі: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Відповідь API: {e.response.text}")
            return None
    
    def check_status(self, creation_id: str) -> Tuple[PublishStatus, Optional[str]]:
        """
        Перевірка статусу публікації
        
        Args:
            creation_id: ID створеного поста
            
        Returns:
            Кортеж (статус, повідомлення про помилку)
        """
        url = f"{self.BASE_URL}/{creation_id}"
        
        params = {
            "fields": "status,error_message",
            "access_token": self.access_token
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            status_str = data.get("status", "ERROR")
            error_message = data.get("error_message")
            
            try:
                status = PublishStatus[status_str]
            except KeyError:
                status = PublishStatus.ERROR
                
            logger.info(f"Статус поста {creation_id}: {status_str}")
            
            return status, error_message
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка при перевірці статусу: {e}")
            return PublishStatus.ERROR, str(e)
    
    def publish_post(self, creation_id: str, max_checks: int = 20, check_delay: int = 5) -> Optional[str]:
        """
        Публікація поста з перевіркою статусу
        
        Args:
            creation_id: ID створеного поста
            max_checks: Максимальна кількість перевірок статусу
            check_delay: Затримка між перевірками (секунди)
            
        Returns:
            ID опублікованого поста або None у випадку помилки
        """
        url = f"{self.BASE_URL}/{self.user_id}/threads_publish"
        
        params = {
            "creation_id": creation_id,
            "access_token": self.access_token
        }
        
        # Спочатку перевіряємо статус
        for attempt in range(max_checks):
            status, error_message = self.check_status(creation_id)
            
            if status == PublishStatus.FINISHED:
                logger.info(f"Пост готовий до публікації: {creation_id}")
                break
            elif status == PublishStatus.ERROR:
                logger.error(f"Помилка при створенні поста: {error_message}")
                return None
            elif status == PublishStatus.IN_PROGRESS:
                logger.info(f"Пост обробляється... спроба {attempt + 1}/{max_checks}")
                time.sleep(check_delay)
            else:
                logger.warning(f"Невідомий статус: {status}")
                time.sleep(check_delay)
        else:
            logger.error(f"Перевищено максимальну кількість перевірок статусу")
            return None
        
        # Публікуємо
        try:
            response = requests.post(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            post_id = data.get("id")
            logger.info(f"Пост опубліковано: {post_id}")
            return post_id
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка при публікації поста: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Відповідь API: {e.response.text}")
            return None
    
    def create_and_publish_text(
        self,
        text: str,
        reply_to_id: Optional[str] = None,
        publish_delay: int = 3
    ) -> Optional[str]:
        """
        Створення та публікація текстового поста (повний цикл)
        
        Args:
            text: Текст поста
            reply_to_id: ID поста для відповіді
            publish_delay: Затримка перед публікацією
            
        Returns:
            ID опублікованого поста або None
        """
        creation_id = self.create_text_post(text, reply_to_id)
        if not creation_id:
            return None
            
        time.sleep(publish_delay)
        return self.publish_post(creation_id)

