import subprocess
import datetime
import os


def log(message):
    # app.log лежить у volume "logs" всередині контейнера app, тому пишемо туди через docker compose exec.
    # Формат такий самий, як у log() в app.py: [дата час] повідомлення
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    # текст передаємо окремим аргументом ($1), а не вставляємо в команду — так лапки чи пробіли в повідомленні нічого не зламають
    result = subprocess.run([
        "docker", "compose", "exec", "app",
        "sh", "-c", 'echo "$1" >> logs/app.log', "sh", line,
    ])
    # друкуємо після запису в лог: якщо консоль не вміє кирилицю (напр. Task Scheduler), лог все одно буде записаний
    try:
        print(line)
        if result.returncode != 0:
            print("Попередження: не вдалося записати в app.log (чи запущений контейнер app?)")
    except UnicodeEncodeError:
        pass


def make_backup():
    # переходимо в корінь проєкту, щоб шляхи працювали незалежно від того, звідки запущено скрипт (термінал, PyCharm Run)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    # перевірка, чи існує папка backups, якщо ні - створити, якщо є - ігнорувати
    os.makedirs("backups", exist_ok=True)
    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = f"backup_{current_time}.sql"

    # 1) pg_dump всередині контейнера db (користувач і БД — зі змінних середовища контейнера, тобто з .env); 2) копіювання файлу з контейнера в backups/
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
        log(f"Помилка резервного копіювання: pg_dump завершився з кодом {dump.returncode}.")
        return

    copy = subprocess.run(copy_cmd)
    if copy.returncode != 0:
        log(f"Помилка резервного копіювання: не вдалося скопіювати {filename} з контейнера (код {copy.returncode}).")
        return

    log(f"Успіх: резервну копію бази даних збережено у backups/{filename}.")


make_backup()
