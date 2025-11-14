"""
Модуль для розбивки довгих текстів на частини через OpenAI
"""
import json
import logging
from typing import List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class TextSplitter:
    """Клас для розбивки довгих текстів"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", max_length: int = 450):
        """
        Ініціалізація
        
        Args:
            api_key: OpenAI API ключ
            model: Модель для використання
            max_length: Максимальна довжина одного фрагмента
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.max_length = max_length
        
    def split_text(self, text: str) -> Optional[List[str]]:
        """
        Розбиває текст на частини, якщо він довгий
        
        Args:
            text: Текст для розбивки
            
        Returns:
            Список частин тексту або None у випадку помилки
        """
        if len(text) <= self.max_length:
            logger.info(f"Текст короткий ({len(text)} символів), розбивка не потрібна")
            return [text]
            
        logger.info(f"Розбиваємо довгий текст ({len(text)} символів)")
        
        prompt = f"""Завдання: Розділи наданий текст на фрагменти до {self.max_length} символів кожен. Жоден фрагмент не повинен дорівнювати {self.max_length} символам, він має бути трохи меншим.

Формат подачі:

1. Перший фрагмент:
   - Містить основний початок тексту (не більше {self.max_length} символів)
   - Завершується символом ⬇️
   - Після основного тексту має бути один пустий рядок

2. Наступні фрагменти починаються з /1, /2, і так далі
3. В кінці кожного фрагмента додавай ⬇️, окрім останнього
4. Останній фрагмент НЕ містить жодних додаткових текстів

Форматування:
- Якщо у тексті містяться переліки чи інший вид нумерації, маркерування - завжди починай новий елемент з нового рядка
- Намагайся не обривати речення посередині

Формат виведення: JSON масив об'єктів

{{
  "chunks": [
    {{"text": "Початковий текст... ⬇️"}},
    {{"text": "/1 Продовження тексту... ⬇️"}},
    {{"text": "/2 Далі текст... ⬇️"}},
    {{"text": "/3 Завершення тексту"}}
  ]
}}

Строгі обмеження:
1. Кожен фрагмент НЕ перевищує {self.max_length} символів
2. Уникай обривання слів або речень у середині фрагмента
3. Дотримуйся форматування та структури JSON
4. Поверни ТІЛЬКИ валідний JSON, без додаткового тексту

Текст:
{text}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Ти асистент, який розбиває довгі тексти на короткі фрагменти. Завжди повертай ТІЛЬКИ валідний JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            logger.debug(f"Відповідь від OpenAI: {content}")
            
            # Парсимо JSON
            data = json.loads(content)
            chunks = [chunk["text"] for chunk in data.get("chunks", [])]
            
            if not chunks:
                logger.error("OpenAI повернув порожній список фрагментів")
                return None
                
            # Перевіряємо довжину кожного фрагмента
            for i, chunk in enumerate(chunks):
                if len(chunk) > self.max_length:
                    logger.warning(f"Фрагмент {i+1} перевищує максимальну довжину: {len(chunk)} > {self.max_length}")
                    
            logger.info(f"Текст розбито на {len(chunks)} частин")
            return chunks
            
        except json.JSONDecodeError as e:
            logger.error(f"Помилка парсингу JSON від OpenAI: {e}")
            logger.error(f"Отримано: {content if 'content' in locals() else 'N/A'}")
            return None
            
        except Exception as e:
            logger.error(f"Помилка при розбивці тексту: {e}")
            return None
    
    def needs_splitting(self, text: str) -> bool:
        """
        Перевіряє, чи потрібно розбивати текст
        
        Args:
            text: Текст для перевірки
            
        Returns:
            True, якщо текст довший за максимальну довжину
        """
        return len(text) > self.max_length
    
    def split_for_carousel(self, text: str, first_part_limit: int = 150) -> Optional[tuple[str, str]]:
        """
        Розумно розбиває текст для каруселі: перша частина до first_part_limit, решта окремо
        
        Args:
            text: Текст для розбивки
            first_part_limit: Максимальна довжина першої частини (для каруселі)
            
        Returns:
            Кортеж (перша_частина, залишок) або None у випадку помилки
        """
        if len(text) <= first_part_limit:
            logger.info(f"Текст короткий ({len(text)} символів), розбивка не потрібна")
            return (text, None)
            
        logger.info(f"Розбиваємо текст для каруселі: перша частина до {first_part_limit} символів")
        
        prompt = f"""Завдання: Розділи текст на ДВІ частини:

1. **Перша частина** (для каруселі з медіа):
   - Не більше {first_part_limit} символів
   - Має закінчуватись на повному слові або реченні (не обривай посередині!)
   - Має містити початок тексту, який логічно завершується
   - БЕЗ будь-яких стрілок, маркерів чи спеціальних символів в кінці

2. **Друга частина** (решта тексту):
   - Весь залишок тексту
   - Має природно продовжувати першу частину

Формат виведення: JSON об'єкт

{{
  "first": "Початок тексту, який логічно завершується",
  "second": "Продовження та решта тексту"
}}

Строгі обмеження:
1. Перша частина НЕ перевищує {first_part_limit} символів
2. НЕ обривай слова або речення посередині
3. Перша частина має бути змістовною і логічно завершеною
4. Поверни ТІЛЬКИ валідний JSON, без додаткового тексту

Текст:
{text}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Ти асистент, який розумно розбиває текст для каруселі. Завжди повертай ТІЛЬКИ валідний JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            logger.debug(f"Відповідь від OpenAI: {content}")
            
            # Парсимо JSON
            data = json.loads(content)
            first_part = data.get("first", "")
            second_part = data.get("second", "")
            
            if not first_part:
                logger.error("OpenAI повернув порожню першу частину")
                return None
            
            # Перевіряємо довжину першої частини
            # Дозволяємо невелике перевищення (+50 символів), якщо GPT завершив речення
            if len(first_part) > first_part_limit + 50:
                logger.warning(f"Перша частина надто довга: {len(first_part)} > {first_part_limit + 50}, обрізаємо")
                # Обрізаємо по останньому пробілу
                first_part = first_part[:first_part_limit].rsplit(' ', 1)[0]
            elif len(first_part) > first_part_limit:
                logger.info(f"Перша частина трохи довша ({len(first_part)} символів), але це ОК - речення завершене")
                    
            logger.info(f"Текст розбито: перша частина {len(first_part)} символів, друга частина {len(second_part)} символів")
            return (first_part, second_part if second_part else None)
            
        except json.JSONDecodeError as e:
            logger.error(f"Помилка парсингу JSON від OpenAI: {e}")
            logger.error(f"Отримано: {content if 'content' in locals() else 'N/A'}")
            return None
            
        except Exception as e:
            logger.error(f"Помилка при розбивці тексту для каруселі: {e}")
            return None

