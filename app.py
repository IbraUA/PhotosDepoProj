from http.server import HTTPServer, BaseHTTPRequestHandler
import re
import uuid
from datetime import datetime

ALLOWED_EXTENSIONS = {"jpg", "gif", "png"}
MAX_ALLOWED_SIZE = 1024 * 1024 * 5

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("logs/app.log", "a", encoding="utf-8") as f:
        f.write(f"{timestamp}: {message}\n")


with open("templates/index.html", "r", encoding="utf-8") as file:
    html = file.read()


# template = file.read()
# class Handler(BaseHTTPRequestHandler):
# HOST = '0.0.0.0'
# PORT = 8000
def extract_file_data(handler):
    length = int(handler.headers.get("Content-Length"))
    body = handler.rfile.read(length)

    boundary = handler.headers['Content-Type'].split('boundary=')[-1].encode()
    start = body.find(b"\r\n\r\n") + 4
    end = body.find(b"\r\n--" + boundary, start)

    data = body[start:end]

    match = re.search(rb'filename="([^"]+)"', body)
    if match is None:
        return None, None
    upload_name = match.group(1).decode()

    return data, upload_name

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        self.wfile.write(html.encode())

    def do_POST(self):

        data, upload_name = extract_file_data(self)
        if data is None:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Bad Request: file is required")
            return
        filename = uuid.uuid4().hex + "." + upload_name.split(".")[-1]


        ext = upload_name.split(".")[-1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            log(f"Помилка: непідтримуваний формат файлу ({upload_name}).")
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Bad Request: unsupported file format")
            return

        if len(data) > MAX_ALLOWED_SIZE:
            log(f"Помилка: файл перевищує ліміт розміру 5 МБ ({upload_name}).")
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Bad Request: file too large")
            return
        print(len(data))

        path = f"images/{filename}"

        with open(path, "wb") as f:
            f.write(data)

        log(f"Успіх: зображення {filename} завантажено.")

        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

        self.wfile.write(f"http://localhost:8080/{path}".encode())

server = HTTPServer(
    ("0.0.0.0", 8000),
    Handler)

server.serve_forever()