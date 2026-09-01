# для запуску потрібен pip install requests

import requests
import time
from concurrent.futures import ThreadPoolExecutor

URL = "http://localhost:8080/upload"
TEST_IMAGE = "images/test.jpg"  # будь-яка наявна тестова картинка
NUM_REQUESTS = 10


def upload_one(i):
    with open(TEST_IMAGE, "rb") as f:
        files = {"file": (f"test_{i}.jpg", f, "image/jpeg")}
        start = time.time()
        response = requests.post(URL, files=files)
        elapsed = time.time() - start
        return i, response.status_code, elapsed


if __name__ == "__main__":
    overall_start = time.time()
    with ThreadPoolExecutor(max_workers=NUM_REQUESTS) as executor:
        results = list(executor.map(upload_one, range(NUM_REQUESTS)))
    overall_elapsed = time.time() - overall_start

    for i, status, elapsed in results:
        print(f"Запит {i}: статус {status}, час {elapsed:.3f}с")

    print(f"\nЗагальний час для {NUM_REQUESTS} одночасних запитів: {overall_elapsed:.3f}с")
