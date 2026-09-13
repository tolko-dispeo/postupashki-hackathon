# Скрипты проекта

Все команды выполняются из корня репозитория после активации Python-
окружения. Скрипты используют базу из переменной `DATABASE_URL`; если она
не задана, применяется `sqlite:///data/postupashki_mvp.sqlite3`.

| Скрипт | Назначение |
| --- | --- |
| `init_db.py` | Создать текущие таблицы SQLAlchemy в выбранной БД |
| `seed_demo.py` | Пересоздать небольшой synthetic-набор: 3 кампании, 6 размещений, 497 кликов, 63 лида и 23 оплаты |
| `seed_large_demo.py` | Пересоздать большую synthetic-базу по `data/mock/large_demo/placements_plan.csv` |
| `docker_start.py` | Внутри backend-контейнера подготовить постоянную demo-БД и запустить FastAPI |
| `show_events.py` | Вывести события выбранной БД по времени |
| `show_attribution.py` | Показать диагностический SQL-отчёт last-touch |

## Небольшая база

```powershell
$env:DATABASE_URL = "sqlite:///data/postupashki_mvp.sqlite3"
python scripts/init_db.py
python scripts/seed_demo.py
```

`seed_demo.py` удаляет и создаёт заново только synthetic-данные в
выбранной базе.

## Большая база

```powershell
$env:DATABASE_URL = "sqlite:///data/postupashki_mvp_large_demo.sqlite3"
python scripts/seed_large_demo.py
```

Доступные параметры:

```powershell
python scripts/seed_large_demo.py --help
```

Генератор полностью очищает выбранную БД. Без `--force` он работает только
с локальной SQLite, в имени которой есть `large_demo` или `synthetic`.
Не применяйте `--force` к рабочим или реальным данным.

## Docker

`docker_start.py` вызывается автоматически из `docker/backend.Dockerfile`.
Вручную его запускать не нужно. При первом старте он создаёт большую базу в
Docker volume, а при следующих стартах сохраняет уже имеющиеся данные.

## Диагностика

```powershell
python scripts/show_events.py
python scripts/show_attribution.py
```

Канонические метрики приложения рассчитываются сервисами из
`src/postupashki_mvp/services/`; `show_attribution.py` предназначен только
для прозрачной ручной проверки last-touch.
