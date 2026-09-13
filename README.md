# Поступашки — Marketing Measurement MVP

Рабочий MVP для измерения пути пользователя от рекламного размещения в
Telegram до оплаты курса. Система создаёт tracking-ссылки, записывает
события, связывает их с лидами, заказами и платежами, распределяет выручку
по рекламным касаниям и показывает итоговые метрики в веб-интерфейсе.

Основной стек: FastAPI, SQLAlchemy, SQLite, Pandas, Streamlit, JavaScript,
Vite, Chart.js и C#/.NET WPF.

## Как работает система

1. Сотрудник создаёт кампанию и рекламное размещение.
2. Backend возвращает tracking-ссылку вида `/t/{placement_id}`.
3. Переход по ссылке записывается как `ad_click`, после чего пользователь
   перенаправляется на посадочную страницу.
4. События сайта связывают анонимного посетителя с лидом.
5. Заказ и успешная оплата продолжают ту же цепочку идентификаторов.
6. Модель атрибуции распределяет выручку по рекламным касаниям за 30 дней
   до создания лида.
7. FastAPI отдаёт расчёты JavaScript-интерфейсу и Streamlit-дашборду.

## Возможности

- реестр кампаний и рекламных размещений;
- tracking-ссылки и фиксация рекламных переходов;
- путь `visitor → lead → order → payment`;
- модели атрибуции `last_touch`, `first_touch` и `linear`;
- поддержка повторных касаний и органического трафика;
- аналитика по кампаниям и размещениям;
- контроль качества данных;
- разделение synthetic и real данных;
- JavaScript/Vite-интерфейс с режимами API и mock;
- графический Windows-лаунчер для Docker-запуска;
- дополнительный Streamlit-дашборд;
- малый контрольный и большой демонстрационный наборы данных.

## Основные метрики

| Метрика | Определение в текущем MVP |
| --- | --- |
| CPL | расходы / атрибутированные лиды |
| CPO | расходы / атрибутированные заказы |
| CAC | расходы / успешные оплаты |
| Средний платёж | атрибутированная выручка / успешные оплаты |
| ROMI | `(атрибутированная выручка − расходы) / расходы × 100%` |
| Покрытие атрибуции | атрибутированная выручка / общая выручка × 100% |

При модели `linear` используются взвешенные эквиваленты. ROMI считается
по выручке, а не по прибыли, и не доказывает причинный эффект рекламы.

## Совместимость запуска

Само приложение запускается через Docker Compose и не привязано к пути
проекта или учётной записи разработчика. После клонирования каждый
пользователь получает собственные локальные контейнеры и Docker volume с
demo-данными.

| Система | Docker-запуск | Графический лаунчер |
| --- | --- | --- |
| Windows 10/11 x64 | Да, через Docker Desktop | Да, `PostupashkiLauncher.exe` |
| macOS Intel / Apple silicon | Да, через Docker Desktop | Нет, используется Terminal |
| Linux | Да, через Docker Engine и Compose plugin | Нет, используется терминал |

Во всех системах frontend открывается локально на
<http://127.0.0.1:8080/>. На компьютере должен быть свободен порт `8080` и
запущен Docker. Python, Node.js и SQLite для Docker-сценария не нужны.

## Графический запуск на Windows x64

`PostupashkiLauncher.exe` проводит пользователя через четыре понятных
экрана: поиск проекта, проверку Docker Desktop, выбор режима и запуск.
Лаунчер показывает живой лог, ждёт готовности `/health`, открывает дашборд
и умеет безопасно остановить контейнеры.

Готовый EXE не хранится в Git: каталог `launcher/publish/` игнорируется.
Поэтому после обычного `git clone` пользователь либо запускает Compose
командой из следующего раздела, либо отдельно получает лаунчер:

1. Скачайте `PostupashkiLauncher.exe` из
   [последнего GitHub Release](https://github.com/tolko-dispeo/postupashki-hackathon/releases/latest).
2. Положите EXE рядом с `compose.yaml` в корень проекта.
3. Запустите двойным нажатием и выберите «Обычный запуск».

Лаунчер автоматически находит `compose.yaml` рядом с собой или предлагает
выбрать его вручную. На компьютере пользователя не нужны Python, Node.js
или .NET Runtime, однако Docker Desktop должен быть установлен. Исходники,
локальная сборка и выпуск EXE описаны в
[`launcher/BUILDING.md`](launcher/BUILDING.md).

## Самый быстрый запуск через Docker

На Windows и macOS нужен запущенный Docker Desktop. На Linux нужны Docker
Engine и Compose plugin. Python, Node.js и ручное создание базы для этого
способа не требуются.

Одинаковая команда для Windows PowerShell, macOS Terminal и Linux shell:

```shell
docker compose up --build -d
docker compose ps
```

На Windows также можно дважды нажать `docker-start.bat`.

Первый запуск скачивает базовые образы, собирает приложение и автоматически
создаёт большую synthetic-базу. После готовности откройте:

- frontend: <http://127.0.0.1:8080/>;
- Swagger: <http://127.0.0.1:8080/docs>;
- health-check: <http://127.0.0.1:8080/health>.

Индикатор в правом верхнем углу frontend должен показывать `API`, а сводка —
10 кампаний, 20 размещений и 7 280 рекламных кликов.

Остановить проект на любой системе можно командой:

```shell
docker compose down
```

На Windows также можно дважды нажать `docker-stop.bat`.

Данные сохраняются в Docker volume между запусками. Чтобы удалить их и при
следующем старте заново создать чистую большую базу, выполните:

```shell
docker compose down -v
```

Эта команда удаляет только Docker volume проекта. Локальные файлы
`data/*.sqlite3` не используются и не изменяются.

## Ручной запуск без Docker

Требования: Python 3.11 или новее, Node.js 22.12 или новее и npm.
Команды выполняются из корня репозитория.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

### Выбор базы данных

SQLite-файлы являются локальными и не коммитятся в Git.

| Файл | Назначение |
| --- | --- |
| `data/postupashki_mvp.sqlite3` | Небольшая штатная база для быстрого smoke-теста |
| `data/postupashki_mvp_v2.sqlite3` | Локальный рабочий снимок расширенного MVP |
| `data/postupashki_mvp_large_demo.sqlite3` | Большая synthetic-база для проверки графиков и скорости |

Для стандартного набора:

```powershell
$env:DATABASE_URL = "sqlite:///data/postupashki_mvp.sqlite3"
python scripts/init_db.py
python scripts/seed_demo.py
```

Для воспроизводимой большой базы:

```powershell
$env:DATABASE_URL = "sqlite:///data/postupashki_mvp_large_demo.sqlite3"
python scripts/seed_large_demo.py
```

На macOS/Linux переменная задаётся так:

```bash
export DATABASE_URL="sqlite:///data/postupashki_mvp_large_demo.sqlite3"
python scripts/seed_large_demo.py
```

Большой сценарий создаёт 10 кампаний, 20 размещений, 7 280 кликов,
772 лида, 456 заказов и 273 оплаты. Генератор полностью очищает выбранную
demo-базу перед заполнением и отказывается работать с SQLite-файлом без
`large_demo` или `synthetic` в имени, если не передан `--force`.

### Запуск с JavaScript-интерфейсом

При ручном запуске нужны два терминала.

Терминал 1 — backend:

```powershell
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL = "sqlite:///data/postupashki_mvp_large_demo.sqlite3"
python -m uvicorn postupashki_mvp.api:app --host 127.0.0.1 --port 8000
```

На macOS/Linux активируйте окружение через
`source .venv/bin/activate` и задайте URL командой
`export DATABASE_URL="sqlite:///data/postupashki_mvp_large_demo.sqlite3"`.

Терминал 2 — frontend:

```shell
cd frontend
npm ci
npm run dev -- --port 5174
```

Перед запуском скопируйте `.env.example` в `.env.local`: на Windows
используйте `Copy-Item .env.example .env.local`, на macOS/Linux —
`cp .env.example .env.local`.

Содержимое `frontend/.env.local` для настоящего API:

```dotenv
VITE_DATA_SOURCE=api
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Открыть:

- frontend: <http://127.0.0.1:5174/>;
- Swagger: <http://127.0.0.1:8000/docs>;
- health-check: <http://127.0.0.1:8000/health>.

Индикатор в правом верхнем углу frontend должен показывать `API`.

### Mock-режим frontend

Для автономного просмотра интерфейса без backend укажите:

```dotenv
VITE_DATA_SOURCE=mock
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Затем запустите `npm run dev`. В mock-режиме аналитика загружается из
`frontend/public/mock/`, а созданные записи хранятся только в памяти
вкладки до перезагрузки.

### Streamlit

Дополнительный Python-дашборд использует ту же переменную `DATABASE_URL`:

```powershell
streamlit run src/postupashki_mvp/dashboard/app.py
```

## API

| Метод | Назначение |
| --- | --- |
| `GET /health` | Проверка доступности backend |
| `GET /analytics/summary` | Общая бизнес-сводка |
| `GET /analytics/campaigns` | Метрики кампаний |
| `GET /analytics/funnel` | Воронка целиком или по кампании |
| `GET /analytics/placements` | Метрики размещений |
| `GET /data-quality/summary` | Ошибки и предупреждения качества |
| `GET/POST /campaigns` | Чтение и создание кампаний |
| `GET/POST /placements` | Чтение и создание размещений |
| `GET /t/{placement_id}` | Фиксация клика и redirect |
| `POST /events` | Запись события сайта |
| `POST /manager-link` | Создание связанного обращения |
| `POST /orders` | Создание заказа |
| `POST /payments` | Создание платежа |

Аналитические методы принимают `data_kind=synthetic|real`,
`attribution_model=last_touch|first_touch|linear` и необязательный
`campaign_id`.

## Проверки

Backend:

```powershell
pytest
ruff check src tests scripts
```

Frontend:

```powershell
cd frontend
npm ci
npm test
npm run lint
npm run build
```

## Структура

```text
postupashki-hackathon/
├── frontend/                 # JavaScript/Vite кабинет
├── launcher/                 # графический Windows-лаунчер на WPF
├── docker/                   # Dockerfile и конфигурация Nginx
├── compose.yaml              # единый запуск frontend и backend
├── build-launcher.bat        # локальная сборка Windows EXE
├── docker-start.bat          # запуск для Windows двойным нажатием
├── docker-stop.bat           # остановка контейнеров для Windows
├── src/postupashki_mvp/
│   ├── api.py                # FastAPI и HTTP-контракт
│   ├── dashboard/            # дополнительный Streamlit UI
│   ├── services/             # атрибуция, метрики и качество
│   └── extensions/           # резерв для долгосрочных расширений
├── scripts/                  # инициализация, seed и диагностика
├── tests/                    # backend-тесты
├── data/mock/control/        # контрольные CSV Contract v1
├── data/mock/large_demo/     # конфигурация большой synthetic-базы
├── docs/                     # архитектура и методика
├── notebooks/                # необязательное историческое исследование
└── migrations/               # резерв для версионируемых миграций
```

## Ограничения

- SQLite и synthetic-данные предназначены для локальной демонстрации;
- авторизация, роли, пагинация и production-деплой не реализованы;
- frontend не редактирует и не удаляет существующие записи;
- реальные данные и секреты не должны попадать в Git;
- `notebooks/research.ipynb` не участвует в runtime и не влияет на метрики
  приложения;
- прогнозирование, causal inference и оптимизация бюджета оставлены как
  долгосрочные расширения.
