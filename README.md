# Поступашки — Marketing Measurement MVP

Рабочий MVP для измерения пути пользователя от рекламного размещения в
Telegram до оплаты курса. Система создаёт tracking-ссылки, записывает
события, связывает их с лидами, заказами и платежами, распределяет выручку
по рекламным касаниям и показывает итоговые метрики в веб-интерфейсе.

Основной стек: FastAPI, SQLAlchemy, SQLite, Pandas, Streamlit, JavaScript,
Vite и Chart.js.

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

## Требования

- Python 3.11 или новее;
- Node.js 22.12 или новее и npm;
- PowerShell-команды ниже выполняются из корня репозитория.

## Установка

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Выбор базы данных

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

Большой сценарий создаёт 10 кампаний, 20 размещений, 7 280 кликов,
772 лида, 456 заказов и 273 оплаты. Генератор полностью очищает выбранную
demo-базу перед заполнением и отказывается работать с SQLite-файлом без
`large_demo` или `synthetic` в имени, если не передан `--force`.

## Запуск с JavaScript-интерфейсом

Единый автозапуск пока не реализован, поэтому нужны два терминала.

Терминал 1 — backend:

```powershell
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL = "sqlite:///data/postupashki_mvp_large_demo.sqlite3"
python -m uvicorn postupashki_mvp.api:app --host 127.0.0.1 --port 8000
```

Терминал 2 — frontend:

```powershell
cd frontend
Copy-Item .env.example .env.local
notepad .env.local
npm ci
npm run dev -- --port 5174
```

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

## Mock-режим frontend

Для автономного просмотра интерфейса без backend укажите:

```dotenv
VITE_DATA_SOURCE=mock
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Затем запустите `npm run dev`. В mock-режиме аналитика загружается из
`frontend/public/mock/`, а созданные записи хранятся только в памяти
вкладки до перезагрузки.

## Streamlit

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
