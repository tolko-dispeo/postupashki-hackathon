# Локальная проверка frontend + FastAPI

Дата проверки: 12 сентября 2026 года.

Ветка `experiment/frontend-integration` создана от `origin/integration/hackathon-v2`.
Frontend добавлен коммитом из `feature/frontend-prototype`. Ветка локальная и не
отправлена на GitHub.

## Что потребовалось для интеграции

FastAPI получил CORS-разрешение для локальных Vite-origin:

- `http://127.0.0.1:5173`;
- `http://127.0.0.1:5174`.

Разрешены `GET`, `POST`, `OPTIONS` и заголовок `Content-Type`. Это позволяет
читать аналитику и отправлять формы из браузера. Добавлен тест preflight-запроса.

Локальный `frontend/.env.local` (игнорируется Git):

```dotenv
VITE_DATA_SOURCE=api
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Подтверждённые сценарии

- загрузка summary, campaign metrics, funnel, placements и data quality;
- фильтры synthetic/real, campaign_id и linear;
- отображение `payment_equivalents` и рассчитанных backend CPL/CPO/CAC/ROMI;
- создание synthetic-кампании через `POST /campaigns`;
- создание размещения через `POST /placements`;
- получение tracking URL и переход с редиректом 302 на landing URL;
- новый `ad_click` после перехода виден в аналитике выбранной кампании;
- пустой real-срез отображается без ошибки.

Тестовая кампания «Интеграционный тест» создана только в локальной SQLite этой
рабочей папки. После одного перехода её срез показал: 1 размещение, 1 клик,
0 лидов, cost 1000.00, revenue 0.00, ROMI -100%.

## Проверки

- backend: 120 тестов прошли;
- frontend: 69 тестов прошли;
- frontend ESLint прошёл;
- production-сборка frontend прошла;
- Ruff для изменённых `api.py` и `test_health.py` прошёл.

Полный `ruff check .` общей ветки сейчас находит существующие замечания в
ноутбуке и нескольких файлах, не связанных с интеграцией. Они не исправлялись,
чтобы не расширять эксперимент.

## Локальный запуск

Из корня рабочей папки после установки Python-зависимостей:

```powershell
python scripts/init_db.py
python scripts/seed_demo.py
uvicorn postupashki_mvp.api:app --host 127.0.0.1 --port 8000
```

В другом терминале:

```powershell
cd frontend
npm ci
npm run dev -- --port 5174
```

Открыть `http://127.0.0.1:5174/`. Индикатор источника должен показывать `API`.
