"""Synchronize every project README with the current hackathon-v3 implementation.

The script is intentionally read-only by default. Use ``--write`` to replace the
README files and ``--check`` in CI to fail when generated content is out of date.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def markdown(value: str) -> str:
    """Normalize an embedded Markdown document to UTF-8/LF-friendly text."""
    return dedent(value).strip() + "\n"


README_CONTENTS = {
    "README.md": markdown(
        """
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
        .\\.venv\\Scripts\\Activate.ps1
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
        .\\.venv\\Scripts\\Activate.ps1
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
        """
    ),
    "frontend/README.md": markdown(
        """
        # Frontend «Поступашки»

        JavaScript/Vite-интерфейс для маркетинговой аналитики и реестра рекламы.
        Визуализации построены на Chart.js. Экономические формулы выполняются на
        backend; frontend запрашивает готовые метрики и форматирует их для показа.

        ## Самый быстрый запуск

        На Windows, macOS и Linux выполните из корня репозитория:

        ```shell
        docker compose up --build -d
        ```

        На Windows вместо команды можно дважды нажать `docker-start.bat` или
        использовать графический `PostupashkiLauncher.exe`. EXE работает только
        на Windows x64; Docker-команда является кроссплатформенной.

        После сборки интерфейс доступен на <http://127.0.0.1:8080/> и уже подключён
        к FastAPI и большой synthetic-базе. Node.js отдельно устанавливать не нужно.
        Инструкция ниже нужна только для ручной frontend-разработки без Docker.

        ## Режимы данных

        | `VITE_DATA_SOURCE` | Источник | Назначение |
        | --- | --- | --- |
        | `api` | FastAPI по `VITE_API_BASE_URL` | Работа с выбранной SQLite-базой |
        | `mock` | JSON из `public/mock/` | Автономный просмотр интерфейса |

        Активный источник отображается в правом верхнем углу страницы. API-режим
        не переключается на mock автоматически при ошибке backend.

        ## Запуск с FastAPI

        Сначала запустите backend из корня репозитория:

        ```powershell
        .\\.venv\\Scripts\\Activate.ps1
        $env:DATABASE_URL = "sqlite:///data/postupashki_mvp_large_demo.sqlite3"
        python -m uvicorn postupashki_mvp.api:app --host 127.0.0.1 --port 8000
        ```

        На macOS/Linux активируйте окружение через
        `source .venv/bin/activate`, задайте `DATABASE_URL` через `export` и
        выполните ту же команду `python -m uvicorn ...`.

        Затем в другом терминале установите зависимости и запустите Vite:

        ```shell
        cd frontend
        npm ci
        npm run dev -- --port 5174
        ```

        Перед запуском создайте `.env.local` из `.env.example`: на Windows
        PowerShell выполните `Copy-Item .env.example .env.local`, на macOS/Linux —
        `cp .env.example .env.local`.

        Укажите в `.env.local`:

        ```dotenv
        VITE_DATA_SOURCE=api
        VITE_API_BASE_URL=http://127.0.0.1:8000
        ```

        Откройте <http://127.0.0.1:5174/>. Backend разрешает локальные Vite-origin
        `http://127.0.0.1:5173` и `http://127.0.0.1:5174`.

        Переменные `VITE_*` подставляются Vite при запуске или сборке и не должны
        содержать секреты. После их изменения перезапустите dev server.

        ## Mock-режим

        В `.env.local` укажите:

        ```dotenv
        VITE_DATA_SOURCE=mock
        VITE_API_BASE_URL=http://127.0.0.1:8000
        ```

        После `npm run dev` FastAPI не требуется. Mock-снимки находятся в
        `public/mock/*.json`. Созданные через формы записи живут только в памяти
        вкладки и исчезают после перезагрузки.

        ## Что реализовано

        - общая аналитическая сводка и 12 KPI;
        - воронка привлечения;
        - графики выручки, расходов и ROMI;
        - таблицы кампаний и размещений;
        - фильтры synthetic/real, модели атрибуции и кампании;
        - проверка качества данных;
        - создание кампаний и размещений;
        - tracking-ссылки и копирование в буфер;
        - пустые, ошибочные и загрузочные состояния;
        - адаптивная вёрстка.

        CAC в текущем MVP означает стоимость успешной оплаты. При `linear`
        интерфейс показывает взвешенные эквиваленты оплат.

        ## Используемый API

        | Метод клиента | HTTP |
        | --- | --- |
        | `getSummary(filters)` | `GET /analytics/summary` |
        | `getCampaignMetrics(filters)` | `GET /analytics/campaigns` |
        | `getFunnel(filters)` | `GET /analytics/funnel` |
        | `getPlacementMetrics(filters)` | `GET /analytics/placements` |
        | `getDataQuality(filters)` | `GET /data-quality/summary` |
        | `getCampaigns()` | `GET /campaigns` |
        | `createCampaign(payload)` | `POST /campaigns` |
        | `getPlacements(campaignId)` | `GET /placements?campaign_id=...` |
        | `createPlacement(payload)` | `POST /placements` |

        Аналитические запросы передают `data_kind`, `attribution_model` и
        необязательный `campaign_id`. HTTP-клиент использует тайм-аут 12 секунд и
        преобразует ошибки FastAPI в сообщения интерфейса.

        ## Проверки

        ```powershell
        npm ci
        npm test
        npm run lint
        npm run build
        ```

        Для локального просмотра production-сборки:

        ```powershell
        npm run preview
        ```

        ## Ограничения

        - нет авторизации и ролей;
        - нет редактирования и удаления существующих записей;
        - нет пагинации и production-деплоя;
        - mock-аналитика не пересчитывается после создания записей.

        ## Скриншоты

        ![Desktop](docs/screenshots/desktop.png)

        ![Mobile](docs/screenshots/mobile.png)
        """
    ),
    "scripts/README.md": markdown(
        """
        # Скрипты проекта

        Все команды выполняются из корня репозитория после активации Python-
        окружения. Скрипты используют базу из переменной `DATABASE_URL`; если она
        не задана, применяется `sqlite:///data/postupashki_mvp.sqlite3`.

        В Windows PowerShell переменная задаётся через
        `$env:DATABASE_URL = "..."`, а в macOS/Linux — через
        `export DATABASE_URL="..."`.

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

        macOS/Linux:

        ```bash
        export DATABASE_URL="sqlite:///data/postupashki_mvp_large_demo.sqlite3"
        python scripts/seed_large_demo.py
        ```

        Доступные параметры:

        ```shell
        python scripts/seed_large_demo.py --help
        ```

        Генератор полностью очищает выбранную БД. Без `--force` он работает только
        с локальной SQLite, в имени которой есть `large_demo` или `synthetic`.
        Не применяйте `--force` к рабочим или реальным данным.

        ## Docker

        `docker_start.py` вызывается автоматически из `docker/backend.Dockerfile`.
        Вручную его запускать не нужно. При первом старте он создаёт большую базу в
        Docker volume, а при следующих стартах сохраняет уже имеющиеся данные.
        Этот Docker-сценарий одинаков для Windows, macOS и Linux.

        ## Диагностика

        ```shell
        python scripts/show_events.py
        python scripts/show_attribution.py
        ```

        Канонические метрики приложения рассчитываются сервисами из
        `src/postupashki_mvp/services/`; `show_attribution.py` предназначен только
        для прозрачной ручной проверки last-touch.
        """
    ),
    "notebooks/README.md": markdown(
        """
        # Ноутбуки

        В каталоге находится один необязательный ноутбук:

        - `research.ipynb` — ручное исследование исторических данных.

        Ноутбук не участвует в запуске FastAPI, frontend или Streamlit, не является
        источником бизнес-метрик приложения и не запускается штатным `pytest`.
        Для повторного анализа может понадобиться исходная выгрузка `base.xlsx`,
        которая не хранится в Git и локально размещается в `data/raw/`.

        Проверенная runtime-логика должна находиться в
        `src/postupashki_mvp/services/`, а не в ноутбуке.
        """
    ),
    "data/mock/README.md": markdown(
        """
        # Синтетические данные

        Каталог содержит два независимых набора:

        - `control/` — небольшой фиксированный Contract v1 для регрессионных
          тестов структуры и связей данных;
        - `large_demo/` — конфигурация генератора большой демонстрационной базы.

        Эти наборы не содержат реальных персональных данных и не заменяют друг
        друга: control проверяет контракт, large demo показывает работу аналитики
        на заметном объёме.

        SQLite-файлы не хранятся в Git. Они создаются локально скриптами из
        `scripts/` и игнорируются правилом `*.sqlite3`.
        """
    ),
    "data/mock/control/README.md": markdown(
        """
        # Контрольный synthetic-набор Contract v1

        Набор фиксирует ожидаемую структуру событий и связи
        `placement → visitor → lead → order → payment`. Он используется
        регрессионными тестами, а не основным дашбордом.

        ## Файлы

        - `placements.csv` — пять размещений двух кампаний;
        - `events.csv` — события четырёх контрольных сценариев;
        - `tests/test_control_data.py` — проверки этого набора.

        `scenario_id` является вспомогательным полем fixture и не входит в
        обязательный контракт `POST /events`. `campaign_name` в placements
        продублирован для читаемости; каноническая связь выполняется по
        `campaign_id`.

        ## Сценарии

        1. Полный путь от рекламного клика до оплаты.
        2. Multi-touch-путь с проверкой last-touch.
        3. Лид без заказа и оплаты.
        4. Просмотр курса без создания лида.

        Ожидаемые итоги: 5 размещений, 2 кампании, 3 лида, 2 заказа, 2 успешные
        оплаты и 85 800 ₽ выручки.

        ## Проверка

        ```powershell
        pytest tests/test_control_data.py
        ```

        Тесты проверяют обязательные столбцы, уникальность ID, допустимые события,
        ссылки на размещения, JSON properties, хронологию, связи этапов, суммы и
        признак `is_synthetic`.
        """
    ),
    "data/mock/large_demo/README.md": markdown(
        """
        # Большой synthetic-набор

        Набор предназначен для локальной демонстрации frontend и Streamlit на
        заметном объёме. Он не заменяет fixtures из `data/mock/control/`.

        ## Состав

        - `placements_plan.csv` — редактируемый план 10 кампаний и 20 размещений;
        - `scripts/seed_large_demo.py` — детерминированный генератор SQLite-базы.

        Ожидаемый результат с параметрами по умолчанию:

        - 10 кампаний и 20 размещений;
        - 7 280 рекламных кликов и 7 230 уникальных посетителей;
        - 772 лида, 456 заказов и 273 оплаты;
        - 4 178 650 ₽ выручки и 2 265 000 ₽ расходов;
        - ROMI 84,49% и покрытие атрибуции 100%.

        ## Автоматическое создание через Docker

        Команда `docker compose up --build -d` работает на Windows, macOS и Linux.
        На Windows её также можно запустить через `docker-start.bat` или
        графический лаунчер. Большая база создаётся автоматически внутри
        постоянного Docker volume. Локальный файл
        `data/postupashki_mvp_large_demo.sqlite3` при этом не изменяется.

        Для принудительного пересоздания Docker-базы:

        ```shell
        docker compose down -v
        docker compose up --build -d
        ```

        ## Создание базы

        Из корня репозитория:

        ```powershell
        $env:DATABASE_URL = "sqlite:///data/postupashki_mvp_large_demo.sqlite3"
        python scripts/seed_large_demo.py
        ```

        macOS/Linux:

        ```bash
        export DATABASE_URL="sqlite:///data/postupashki_mvp_large_demo.sqlite3"
        python scripts/seed_large_demo.py
        ```

        SQLite-файл создаётся локально и не хранится в Git. Генератор полностью
        очищает выбранную demo-базу перед заполнением. Защитная проверка без
        `--force` разрешает только SQLite-файлы с `large_demo` или `synthetic` в
        имени.

        ## Запуск API и frontend

        Терминал 1:

        ```powershell
        $env:DATABASE_URL = "sqlite:///data/postupashki_mvp_large_demo.sqlite3"
        python -m uvicorn postupashki_mvp.api:app --host 127.0.0.1 --port 8000
        ```

        Терминал 2:

        ```powershell
        cd frontend
        npm run dev -- --port 5174
        ```

        В `frontend/.env.local` должен быть выбран `VITE_DATA_SOURCE=api`.
        Откройте <http://127.0.0.1:5174/> и проверьте индикатор `API`.
        """
    ),
    "data/raw/README.md": markdown(
        """
        # Raw data

        Каталог предназначен для локальных исходных выгрузок, например
        `base.xlsx`. Содержимое каталога игнорируется Git, кроме этого README,
        чтобы реальные данные и персональная информация не публиковались.

        Не используйте raw-файлы напрямую как источник runtime-метрик без явного
        импорта, проверки качества и фиксации происхождения данных.
        """
    ),
    "data/processed/README.md": markdown(
        """
        # Processed data

        Каталог зарезервирован для локальных производных выгрузок и аналитических
        витрин. Содержимое игнорируется Git, кроме этого README.

        Основное приложение сейчас рассчитывает метрики непосредственно из
        выбранной SQLite-базы и не зависит от файлов в этом каталоге.
        """
    ),
    "migrations/README.md": markdown(
        """
        # Миграции БД

        Каталог зарезервирован для будущих версионируемых миграций схемы.

        Сейчас Alembic или другой migration runner не подключён: таблицы создаются
        из SQLAlchemy-моделей командой `python scripts/init_db.py`, а каталог
        `versions/` содержит только `.gitkeep`.

        Перед переходом на PostgreSQL или обновлением существующей production-БД
        здесь следует настроить инструмент миграций. До этого момента нельзя
        описывать каталог как действующую систему миграций.
        """
    ),
    "src/postupashki_mvp/extensions/README.md": markdown(
        """
        # Долгосрочные расширения

        Каталог зарезервирован для независимых компонентов после MVP. Сейчас он не
        импортируется runtime-кодом и содержит только этот README и `__init__.py`.

        Возможные направления:

        - сбор и синхронизация Telegram-постов;
        - NLP-классификация контента;
        - эксперименты и incremental ROMI;
        - прогнозирование продаж;
        - рекомендации по распределению бюджета.

        Новые компоненты следует добавлять сюда только после появления конкретного
        контракта, тестов и владельца. Бизнес-логика текущего MVP остаётся в
        `src/postupashki_mvp/services/`.
        """
    ),
}


SKIPPED_DIRECTORY_NAMES = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "coverage",
    "dist",
    "node_modules",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview, write, or verify all project README files."
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--write",
        action="store_true",
        help="Replace README files whose generated content differs.",
    )
    action.add_argument(
        "--check",
        action="store_true",
        help="Exit with status 1 when at least one README is out of date.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (default: parent of the scripts directory).",
    )
    return parser.parse_args()


def validate_root(root: Path) -> None:
    required = (
        root / "pyproject.toml",
        root / "src/postupashki_mvp/api.py",
        root / "frontend/package.json",
    )
    missing = [path.relative_to(root).as_posix() for path in required if not path.is_file()]
    if missing:
        raise SystemExit(
            "Refusing to run outside the Postupashki repository. Missing: " + ", ".join(missing)
        )


def discover_readmes(root: Path) -> set[str]:
    result: set[str] = set()
    for path in root.rglob("README.md"):
        relative = path.relative_to(root)
        if any(part in SKIPPED_DIRECTORY_NAMES for part in relative.parts):
            continue
        result.add(relative.as_posix())
    return result


def write_utf8_lf(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(content)


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    validate_root(root)

    known = set(README_CONTENTS)
    discovered = discover_readmes(root)
    unexpected = sorted(discovered - known)
    missing = sorted(known - discovered)
    if unexpected or missing:
        details = []
        if unexpected:
            details.append("README without template: " + ", ".join(unexpected))
        if missing:
            details.append("Expected README missing: " + ", ".join(missing))
        raise SystemExit("Refusing a partial update. " + "; ".join(details))

    changed: list[str] = []
    for relative, desired in README_CONTENTS.items():
        path = root / relative
        current = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
        if current == desired:
            continue
        changed.append(relative)
        if args.write:
            write_utf8_lf(path, desired)

    if not changed:
        print("All README files are up to date.")
        return

    verb = "Updated" if args.write else "Would update"
    print(f"{verb} {len(changed)} README file(s):")
    for relative in changed:
        print(f"- {relative}")

    if args.check:
        raise SystemExit(1)
    if not args.write:
        print("\nDry run only. Re-run with --write to apply these changes.")


if __name__ == "__main__":
    main()
