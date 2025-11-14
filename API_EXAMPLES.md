# 📡 Приклади роботи з Threads API

Цей документ містить практичні приклади використання Threads API з командного рядка (curl) та Python.

## 🔑 Базові налаштування

Замініть ці значення на ваші:
- `{threads-user-id}` — ваш Threads User ID
- `{access-token}` — ваш Threads Access Token

---

## 1️⃣ Отримання інформації про профіль

### cURL

```bash
curl -X GET \
  "https://graph.threads.net/v1.0/me?fields=id,username,threads_profile_picture_url&access_token={access-token}"
```

### Python

```python
import requests

response = requests.get(
    "https://graph.threads.net/v1.0/me",
    params={
        "fields": "id,username,threads_profile_picture_url",
        "access_token": "{access-token}"
    }
)

print(response.json())
```

### Відповідь

```json
{
  "id": "1234567890123456",
  "username": "your_username",
  "threads_profile_picture_url": "https://..."
}
```

---

## 2️⃣ Створення текстового поста

### cURL

```bash
curl -X POST \
  "https://graph.threads.net/v1.0/{threads-user-id}/threads" \
  -d "media_type=TEXT" \
  -d "text=Привіт, Threads! 👋" \
  -d "access_token={access-token}"
```

### Python

```python
import requests

response = requests.post(
    f"https://graph.threads.net/v1.0/{threads_user_id}/threads",
    params={
        "media_type": "TEXT",
        "text": "Привіт, Threads! 👋",
        "access_token": access_token
    }
)

creation_id = response.json()["id"]
print(f"Creation ID: {creation_id}")
```

### Відповідь

```json
{
  "id": "17855847105309514"
}
```

---

## 3️⃣ Створення поста з фото

### cURL

```bash
curl -X POST \
  "https://graph.threads.net/v1.0/{threads-user-id}/threads" \
  -d "media_type=IMAGE" \
  -d "image_url=https://example.com/photo.jpg" \
  -d "text=Дивіться на це фото!" \
  -d "access_token={access-token}"
```

### Python

```python
response = requests.post(
    f"https://graph.threads.net/v1.0/{threads_user_id}/threads",
    params={
        "media_type": "IMAGE",
        "image_url": "https://example.com/photo.jpg",
        "text": "Дивіться на це фото!",
        "access_token": access_token
    }
)

creation_id = response.json()["id"]
```

---

## 4️⃣ Створення поста з відео

### cURL

```bash
curl -X POST \
  "https://graph.threads.net/v1.0/{threads-user-id}/threads" \
  -d "media_type=VIDEO" \
  -d "video_url=https://example.com/video.mp4" \
  -d "text=Крутий відос!" \
  -d "access_token={access-token}"
```

### Python

```python
response = requests.post(
    f"https://graph.threads.net/v1.0/{threads_user_id}/threads",
    params={
        "media_type": "VIDEO",
        "video_url": "https://example.com/video.mp4",
        "text": "Крутий відос!",
        "access_token": access_token
    }
)

creation_id = response.json()["id"]
```

---

## 5️⃣ Створення каруселі (кілька фото)

### Крок 1: Створити елементи каруселі

```python
# Елемент 1
response1 = requests.post(
    f"https://graph.threads.net/v1.0/{threads_user_id}/threads",
    params={
        "media_type": "IMAGE",
        "image_url": "https://example.com/photo1.jpg",
        "is_carousel_item": "true",
        "access_token": access_token
    }
)
item_id_1 = response1.json()["id"]

# Елемент 2
response2 = requests.post(
    f"https://graph.threads.net/v1.0/{threads_user_id}/threads",
    params={
        "media_type": "IMAGE",
        "image_url": "https://example.com/photo2.jpg",
        "is_carousel_item": "true",
        "access_token": access_token
    }
)
item_id_2 = response2.json()["id"]
```

### Крок 2: Створити карусель

```python
response = requests.post(
    f"https://graph.threads.net/v1.0/{threads_user_id}/threads",
    params={
        "media_type": "CAROUSEL",
        "children": f"{item_id_1},{item_id_2}",
        "text": "Подивіться на ці фото!",
        "access_token": access_token
    }
)

carousel_creation_id = response.json()["id"]
```

---

## 6️⃣ Перевірка статусу поста

### cURL

```bash
curl -X GET \
  "https://graph.threads.net/v1.0/{creation-id}?fields=status,error_message&access_token={access-token}"
```

### Python

```python
response = requests.get(
    f"https://graph.threads.net/v1.0/{creation_id}",
    params={
        "fields": "status,error_message",
        "access_token": access_token
    }
)

status = response.json()
print(f"Status: {status['status']}")
```

### Відповідь

```json
{
  "status": "FINISHED",
  "id": "17855847105309514"
}
```

**Можливі статуси:**
- `FINISHED` — готовий до публікації
- `IN_PROGRESS` — обробляється
- `ERROR` — помилка
- `EXPIRED` — прострочений (>24 години)

---

## 7️⃣ Публікація поста

### cURL

```bash
curl -X POST \
  "https://graph.threads.net/v1.0/{threads-user-id}/threads_publish" \
  -d "creation_id={creation-id}" \
  -d "access_token={access-token}"
```

### Python

```python
response = requests.post(
    f"https://graph.threads.net/v1.0/{threads_user_id}/threads_publish",
    params={
        "creation_id": creation_id,
        "access_token": access_token
    }
)

post_id = response.json()["id"]
print(f"Published Post ID: {post_id}")
```

### Відповідь

```json
{
  "id": "18013829824345162"
}
```

---

## 8️⃣ Створення відповіді (reply) до поста

### cURL

```bash
curl -X POST \
  "https://graph.threads.net/v1.0/me/threads" \
  -d "media_type=TEXT" \
  -d "text=Це продовження поста ⬇️" \
  -d "reply_to_id={post-id}" \
  -d "access_token={access-token}"
```

### Python

```python
# Створюємо reply
response = requests.post(
    "https://graph.threads.net/v1.0/me/threads",
    data={
        "media_type": "TEXT",
        "text": "Це продовження поста ⬇️",
        "reply_to_id": post_id,
        "access_token": access_token
    }
)

reply_creation_id = response.json()["id"]

# Публікуємо reply
response = requests.post(
    f"https://graph.threads.net/v1.0/{threads_user_id}/threads_publish",
    params={
        "creation_id": reply_creation_id,
        "access_token": access_token
    }
)

reply_post_id = response.json()["id"]
```

---

## 9️⃣ Отримання списку ваших постів

### cURL

```bash
curl -X GET \
  "https://graph.threads.net/v1.0/me/threads?fields=id,text,timestamp&access_token={access-token}"
```

### Python

```python
response = requests.get(
    "https://graph.threads.net/v1.0/me/threads",
    params={
        "fields": "id,text,timestamp,media_type",
        "access_token": access_token
    }
)

posts = response.json()["data"]
for post in posts:
    print(f"Post ID: {post['id']}")
    print(f"Text: {post.get('text', 'N/A')}")
    print(f"Time: {post['timestamp']}")
    print("---")
```

---

## 🔟 Повний цикл публікації (Create + Publish)

### Python

```python
import requests
import time

# Налаштування
threads_user_id = "YOUR_USER_ID"
access_token = "YOUR_ACCESS_TOKEN"

def create_and_publish_text(text):
    """Створює та публікує текстовий пост"""
    
    # Крок 1: Створити media container
    print("1. Створюємо пост...")
    response = requests.post(
        f"https://graph.threads.net/v1.0/{threads_user_id}/threads",
        params={
            "media_type": "TEXT",
            "text": text,
            "access_token": access_token
        }
    )
    
    creation_id = response.json()["id"]
    print(f"   Creation ID: {creation_id}")
    
    # Крок 2: Перевірити статус
    print("2. Перевіряємо статус...")
    for i in range(10):
        response = requests.get(
            f"https://graph.threads.net/v1.0/{creation_id}",
            params={
                "fields": "status,error_message",
                "access_token": access_token
            }
        )
        
        status_data = response.json()
        status = status_data["status"]
        print(f"   Спроба {i+1}: {status}")
        
        if status == "FINISHED":
            break
        elif status == "ERROR":
            print(f"   Помилка: {status_data.get('error_message')}")
            return None
            
        time.sleep(2)
    
    # Крок 3: Опублікувати
    print("3. Публікуємо пост...")
    response = requests.post(
        f"https://graph.threads.net/v1.0/{threads_user_id}/threads_publish",
        params={
            "creation_id": creation_id,
            "access_token": access_token
        }
    )
    
    post_id = response.json()["id"]
    print(f"   ✅ Опубліковано! Post ID: {post_id}")
    
    return post_id


# Використання
post_id = create_and_publish_text("Привіт, Threads! 🚀")
```

---

## ⚠️ Важливі обмеження Threads API

### Ліміти публікацій

- ✅ До **250 постів на день** на користувача
- ✅ До **1000 постів на день** для всього додатку

### Ліміти тексту

- ✅ **500 символів** максимум в одному пості
- ✅ Для довших текстів використовуйте replies (ланцюжки)

### Ліміти медіа

**Фото:**
- Формати: JPG, PNG
- Максимальний розмір: 8MB
- Рекомендовано: 1080x1080px

**Відео:**
- Формати: MP4, MOV
- Максимальний розмір: 1GB
- Максимальна тривалість: 5 хвилин
- Рекомендовано: 30fps, H.264 кодек

**Каруселі:**
- Від 2 до 10 елементів
- Можна міксувати фото та відео

### Інше

- Media containers **діють 24 години** (після створення треба опублікувати)
- Access tokens **діють 60 днів** (long-lived tokens)
- Rate limiting: близько **200 запитів на годину**

---

## 🧪 Тестовий скрипт

Збережіть цей скрипт як `test_api.py`:

```python
import requests
import time
import sys

# Ваші дані
THREADS_USER_ID = "YOUR_USER_ID"
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"

def test_api():
    """Тестує основні функції Threads API"""
    
    print("🧪 Тестування Threads API\n")
    
    # Тест 1: Отримання інформації про профіль
    print("1. Тест: Отримання профілю...")
    try:
        response = requests.get(
            "https://graph.threads.net/v1.0/me",
            params={
                "fields": "id,username",
                "access_token": ACCESS_TOKEN
            }
        )
        response.raise_for_status()
        data = response.json()
        print(f"   ✅ Username: {data['username']}")
        print(f"   ✅ User ID: {data['id']}\n")
    except Exception as e:
        print(f"   ❌ Помилка: {e}\n")
        return False
    
    # Тест 2: Створення тестового поста
    print("2. Тест: Створення поста...")
    try:
        response = requests.post(
            f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads",
            params={
                "media_type": "TEXT",
                "text": "🤖 Тестовий пост від API",
                "access_token": ACCESS_TOKEN
            }
        )
        response.raise_for_status()
        creation_id = response.json()["id"]
        print(f"   ✅ Creation ID: {creation_id}\n")
    except Exception as e:
        print(f"   ❌ Помилка: {e}\n")
        return False
    
    # Тест 3: Перевірка статусу
    print("3. Тест: Перевірка статусу...")
    try:
        response = requests.get(
            f"https://graph.threads.net/v1.0/{creation_id}",
            params={
                "fields": "status",
                "access_token": ACCESS_TOKEN
            }
        )
        response.raise_for_status()
        status = response.json()["status"]
        print(f"   ✅ Статус: {status}\n")
    except Exception as e:
        print(f"   ❌ Помилка: {e}\n")
        return False
    
    print("✅ Всі тести пройдено успішно!")
    print("💡 Тестовий пост НЕ був опубліковано (залишився як чернетка)")
    return True

if __name__ == "__main__":
    if test_api():
        sys.exit(0)
    else:
        sys.exit(1)
```

Запустіть:

```bash
python test_api.py
```

---

## 📚 Додаткова інформація

### Офіційна документація
- [Threads API Overview](https://developers.facebook.com/docs/threads)
- [API Reference](https://developers.facebook.com/docs/threads/reference)
- [Rate Limits](https://developers.facebook.com/docs/threads/overview#rate-limits)

### Postman Collection
Ви можете використовувати готову [Postman Collection](https://www.postman.com/meta/threads/overview) від Meta для тестування API.

---

**Успіхів з Threads API! 🚀**

