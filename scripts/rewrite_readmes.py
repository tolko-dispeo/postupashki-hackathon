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
        .\\.venv\\Scripts\\Activate.ps1
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
        .\\.venv\\Scripts\\Activate.ps1
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
        """
    ),
    "frontend/README.md": markdown(
        """
        # Frontend «Поступашки»

        JavaScript/Vite-интерфейс для маркетинговой аналитики и реестра рекламы.
        Визуализации построены на Chart.js. Экономические формулы выполняются на
        backend; frontend запрашивает готовые метрики и форматирует их для показа.

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

        Затем в другом терминале:

        ```powershell
        cd frontend
        Copy-Item .env.example .env.local
        notepad .env.local
        npm ci
        npm run dev -- --port 5174
        ```

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
        - mock-аналитика не пересчитывается после создания записей;
        - единый автозапуск frontend и backend пока не реализован.

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

        | Скрипт | Назначение |
        | --- | --- |
        | `init_db.py` | Создать текущие таблицы SQLAlchemy в выбранной БД |
        | `seed_demo.py` | Пересоздать небольшой synthetic-набор: 3 кампании, 6 размещений, 497 кликов, 63 лида и 23 оплаты |
        | `seed_large_demo.py` | Пересоздать большую synthetic-базу по `data/mock/large_demo/placements_plan.csv` |
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

        ## Диагностика

        ```powershell
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

        ## Создание базы

        Из корня репозитория:

        ```powershell
        $env:DATABASE_URL = "sqlite:///data/postupashki_mvp_large_demo.sqlite3"
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
