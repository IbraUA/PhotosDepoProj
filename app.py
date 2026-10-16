from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
import re
import uuid
from datetime import datetime
from PIL import Image
import io
import os
import psycopg
from urllib.parse import urlparse, parse_qs

def get_connection():
    return psycopg.connect(
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
    )
# .jpeg технічно не згадано в ТЗ (лише .jpg), але це той самий формат JPEG —
# додано для реальної зручності (WhatsApp, iPhone та багато камер зберігають саме так)

ALLOWED_EXTENSIONS = {"jpg", "gif", "png", "jpeg"}
MAX_ALLOWED_SIZE = 1024 * 1024 * 5
FORMAT_BY_EXTENSION = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "gif": "GIF"}

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("logs/app.log", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
def save_metadata(filename, original_name, size, file_type):
    conn = get_connection()
    try:
        with conn:  # у psycopg3 "with conn" сам комітить при успіху і робить rollback при помилці
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO images (filename, original_name, size, file_type) VALUES (%s, %s, %s, %s)",
                    (filename, original_name, size, file_type),
                )
    finally:
        conn.close()

def delete_image(img_id):
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM images WHERE id = %s RETURNING filename",
                    (img_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                else:
                    return row[0]
    finally:
        conn.close()


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
        parsed = urlparse(self.path)
        if parsed.path =="/images-list":
            params = parse_qs(parsed.query)
            page = int(params.get("page", ["1"])[0])
            rows = get_images_metadata(page=page)

            # prev_link = f"/images-list?page={page - 1}" if page > 1 else ""
            # next_link = f"/images-list?page={page + 1}" if len(rows) == 10 else ""
            if page > 1:
                prev_link = f'<a href="/images-list?page={page-1}">← Попередня</a>'
            else:
                prev_link = '<span>← Попередня</span>'
            if len(rows) == 10:
                next_link = f'<a href="/images-list?page={page+1}">Наступна →</a>'
            else:
                next_link = '<span>Наступна →</span>'

            with open("templates/images_list.html", "r", encoding="utf-8") as file:
                page_html = file.read()
                page_html = page_html.replace("{{ROWS}}", render_rows(rows) )
                page_html = page_html.replace("{{PREV_LINK}}", prev_link)
                page_html = page_html.replace("{{NEXT_LINK}}", next_link)
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(page_html.encode())
                return

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        self.wfile.write(html.encode())

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/delete/"):
            try:
                img_id = int(parsed.path.split("/")[-1])
            except ValueError:
                log(f"Bad Request: you entered an invalid image ID.")
                self.send_response(400)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"Bad Request: invalid image id")
                return
            filename = delete_image(img_id)

            if filename is None:
                log(f"Помилка видалення: зображення {img_id} не знайдено")
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"Not found: no such image id")
            else:
                path = f"images/{filename}"
                if os.path.exists(path):
                    os.remove(path)
                else:
                    log(f"Попередження: файл {filename} відсутній на диску (id={img_id}).")
                log(f"Успіх: зображення {filename} (id={img_id}) видалено.")
                self.send_response(303)
                self.send_header("Location", "/images-list")
                self.end_headers()

            return

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
            if img.format != FORMAT_BY_EXTENSION.get(ext):
                log(f"Формат картинки ({upload_name}) не відповідає розширенню .")
                self.send_response(400)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"Bad Request: file extension is fake")
                return

        except Exception:
            log(f"Помилка: файл не є валідним зображенням ({upload_name}).")
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Bad Request: file is not a valid image")
            return

        # log(len(data))

        try:
            save_metadata(filename, upload_name, len(data), ext)
            path = f"images/{filename}"
            with open(path, "wb") as f:
                f.write(data)
            log(f"Успіх: зображення {filename} завантажено.")
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"http://localhost:8080/{path}".encode())
        except Exception as e:
            log(f"Помилка запису метаданих у БД: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Internal Server Error: could not save metadata")
            return



# врахуємо можливість зміни OFFSET в майбутньому
def get_images_metadata(page=1, per_page=10):
    offset = per_page * (page - 1)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, filename, original_name, size, upload_time, file_type "
                "FROM images ORDER BY upload_time DESC LIMIT %s OFFSET %s",
                (per_page, offset,),
            )
            return cur.fetchall()
    finally:

        conn.close()


def render_rows(rows):
    if not rows:
        return "<tr><td colspan='6'>Немає завантажених зображень</td></tr>"

    rows_html = ""
    for row in rows:
        img_id, filename, original_name, size, upload_time, file_type = row
        size_kb = round(size / 1024, 1)
        rows_html += f"""
        <tr>
            <td>
                <a href="/images/{filename}">{filename}</a></td>
            <td>{original_name}</td>
            <td>{size_kb}</td>
            <td>{upload_time}</td>
            <td>{file_type}</td>
            <td>
                <form method="POST" action="/delete/{img_id}">
                <button>Видалити</button>
                </form>
            </td>
        </tr>
        """
    return rows_html
# створення сервера, що обробляє запити в окремих потоках (ThreadingHTTPServer)
server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
server.serve_forever()