# PhotoDrop

Сервіс для зберігання та роздачі зображень. Завантажуєш картинку — отримуєш пряме посилання на неї.

## Стек

- **Python** (стандартна бібліотека `http.server`, без фреймворків) + `Pillow`
- **Nginx** — роздача статики (`/images/`, `/static/`) і проксування решти запитів на бекенд
- **Docker / Docker Compose** — контейнеризація, multi-stage build для мінімального розміру образу

## Структура проєкту

```
PhotoDrop/
├── app.py                # Python-бекенд (маршрути, валідація, логування)
├── requirements.txt      # Залежності Python
├── Dockerfile             # Multi-stage build бекенду
├── docker-compose.yml    # app + nginx, спільні volumes
├── nginx.conf             # Конфігурація Nginx
├── templates/index.html  # Головна сторінка
├── static/                # CSS/JS/іконки
├── images/                # Завантажені зображення (Docker volume)
├── logs/                  # app.log (Docker volume)
└── scripts/load_test.py  # Тестовий скрипт для перевірки паралельних завантажень
```

## Запуск

Потрібен лише Docker (з Docker Compose).

```bash
docker compose up --build
```

- Веб-інтерфейс: **http://localhost:8080**
- Бекенд напряму (для налагодження): **http://localhost:8000**
- Зображення: **http://localhost:8080/images/<ім'я_файлу>**

Зупинка: `Ctrl+C`, або `docker compose down` (додай `-v`, щоб видалити volumes і зображення/логи разом з ними).

## Маршрути API

| Маршрут | Метод | Опис |
|---|---|---|
| `/` | GET | Головна сторінка з формою завантаження |
| `/upload` | POST | Приймає файл (`multipart/form-data`, поле `file`). Формати: `.jpg`, `.jpeg`, `.png`, `.gif`. Максимальний розмір: 5MB. Перевіряється і розширення, і реальний вміст файлу (Pillow). Повертає пряме посилання на завантажене зображення або `400 Bad Request` з описом помилки |
| `/images/<ім'я_файлу>` | GET | Віддає завантажене зображення (обробляється Nginx) |
| `/static/...` | GET | CSS/JS/іконки інтерфейсу (обробляється Nginx) |

## Логування

Кожна дія (успішне завантаження чи помилка) записується в `logs/app.log` у форматі:
```
[Дата/час] Дія: повідомлення
```

## Тестування паралельних завантажень

```bash
pip install requests
python scripts/load_test.py
```

Надсилає 10 одночасних POST-запитів на `/upload` і вимірює час — перевіряє, що бекенд (`ThreadingHTTPServer`) реально обробляє запити паралельно.
