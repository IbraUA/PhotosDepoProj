import subprocess
import datetime
import os


def make_backup():
    # переходимо в корінь проєкту, щоб шляхи працювали незалежно від того, звідки запущено скрипт (термінал, PyCharm Run)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    # перевірка, чи існує папка backups, якщо ні - створити, якщо є - ігнорувати
    os.makedirs("backups", exist_ok=True)
    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = f"backup_{current_time}.sql"

    # pg_dump всередині контейнера db (користувач і БД — зі змінних середовища контейнера, тобто з .env); 2) копіювання файлу з контейнера в backups/
    dump_cmd=[
        "docker", "compose", "exec", "db",
        "sh", "-c",
        f"pg_dump -U $POSTGRES_USER -d $POSTGRES_DB -f /tmp/{filename}",
    ]

    copy_cmd=[
        "docker", "compose", "cp",
        f"db:/tmp/{filename}",
        f"backups/{filename}",
    ]
    # запускаємо команди по черзі; якщо дамп не вдався — копіювати нічого
    dump = subprocess.run(dump_cmd)
    if dump.returncode != 0:
        print("Створення бекапу невдале!")
        return

    copy = subprocess.run(copy_cmd)
    if copy.returncode != 0:
        print("Копіювання невдале, помилка!")
        return

    print(f"Бекап {filename} успішно створено!")


make_backup()
