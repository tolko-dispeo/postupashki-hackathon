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
