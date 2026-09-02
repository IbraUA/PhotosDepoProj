from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
import re
import uuid
from datetime import datetime
from PIL import Image
import io

# .jpeg технічно не згадано в ТЗ (лише .jpg), але це той самий формат JPEG —
# додано для реальної зручності (WhatsApp, iPhone та багато камер зберігають саме так)
ALLOWED_EXTENSIONS = {"jpg", "gif", "png", "jpeg"}
MAX_ALLOWED_SIZE = 1024 * 1024 * 5

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("logs/app.log", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


with open("templates/index.html", "r", encoding="utf-8") as file:
    html = file.read()


def extract_file_data(handler):
    try:
        # скільки байтів тіла запиту очікувати (браузер сам повідомляє через заголовок)
        length = int(handler.headers.get("Content-Length"))
        # читаємо рівно стільки байтів, скільки заявлено в Content-Length
        body = handler.rfile.read(length)

        # дістаємо сам роздільник (boundary) із заголовка Content-Type
        boundary = handler.headers['Content-Type'].split('boundary=')[-1].encode()
        # шукаємо перший подвійний перенос і починаємо читати через 4 символи після цього
        start = body.find(b"\r\n\r\n") + 4
        # також визначаємо кінцеву частину повідомлення, що буде читатись
        end = body.find(b"\r\n--" + boundary, start)

        # власне байти файлу, вирізані з body між start і end
        data = body[start:end]

        # шукаємо оригінальну назву файлу (filename="...") у тілі запит
        match = re.search(rb'filename="([^"]+)"', body)
        if match is None:
            return None, None
        upload_name = match.group(1).decode()

        return data, upload_name
    except Exception as e:
        log(f"Непередбачена помилка при парсингу: {e}")
        return None, None



class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        self.wfile.write(html.encode())

    def do_POST(self):

        # перевірка, чи наявний файл для завантаження
        data, upload_name = extract_file_data(self)
        if data is None:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Bad Request: file is required")
            return
        # використовуємо саме цю бібліотеку для уніфікації назви файлу (не буде повторюваних назв гарантовано)
        filename = uuid.uuid4().hex + "." + upload_name.split(".")[-1]

        # приведення регістру до єдиного виду
        ext = upload_name.split(".")[-1].lower()

        # перевірка розширення (згідно ТЗ)

        if ext not in ALLOWED_EXTENSIONS:
            log(f"Помилка: непідтримуваний формат файлу ({upload_name}).")
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Bad Request: unsupported file format")
            return

        # перевірка максимального розміру файлу

        if len(data) > MAX_ALLOWED_SIZE:
            log(f"Помилка: файл перевищує ліміт розміру 5 МБ ({upload_name}).")
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Bad Request: file too large")
            return

        # перевірка, що файл РЕАЛЬНО є зображенням (не лише за розширенням імені)
        try:
            img = Image.open(io.BytesIO(data))
            img.verify()
        except Exception:
            log(f"Помилка: файл не є валідним зображенням ({upload_name}).")
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Bad Request: file is not a valid image")
            return

        # log(len(data))

        path = f"images/{filename}"

        with open(path, "wb") as f:
            f.write(data)

        log(f"Успіх: зображення {filename} завантажено.")

        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

        self.wfile.write(f"http://localhost:8080/{path}".encode())

# створення сервера, що обробляє запити в окремих потоках (ThreadingHTTPServer)

server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)

server.serve_forever()