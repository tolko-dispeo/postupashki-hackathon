# Проверки качества и бизнес-метрики: Contract v1

Модули принимают DataFrame (также допустимы списки словарей), копируют входные
таблицы и не обращаются к БД, API или Streamlit. Существующая ORM-модель пока не
содержит Campaign и Placement.campaign_id: интеграционный слой должен передать
таблицы Contract v1. Группировать по campaign_name вместо campaign_id нельзя.

## Вызов и входные данные

```python
from postupashki_mvp.services.data_quality import validate_data_quality
from postupashki_mvp.services.business_metrics import calculate_business_metrics

tables = dict(campaigns=campaigns, placements=placements, events=events,
              leads=leads, orders=orders, payments=payments)
issues = validate_data_quality(tables, is_synthetic=False)
result = calculate_business_metrics(
    tables, attribution, is_synthetic=False, attribution_model="last_touch",
)
campaigns_for_dashboard = result["campaign_metrics"]
overall = result["overall_funnel"]
unattributed = result["unattributed_payments"]
```

Обязательные поля непустых таблиц:

| Таблица | Поля (помимо is_synthetic во всех таблицах) |
| --- | --- |
| campaigns | campaign_id; campaign_name необязателен, только для отображения |
| placements | placement_id, campaign_id, cost |
| events | event_id, occurred_at, event_name, visitor_id, session_id, placement_id, properties |
| leads | lead_id, visitor_id, created_at |
| orders | order_id, lead_id, created_at |
| payments | payment_id, order_id, amount, status, paid_at |

Отсутствующая таблица/пустой DataFrame означает ноль строк; непустая таблица
без обязательных столбцов — ошибка. IDs должны быть скалярными, стабильными и
одного типа в связанных таблицах. Пустые ID запрещены; дубликаты не удаляются
молча. Расход — сумма placement.cost, один раз на размещение, без соединения
с событиями. Суммы предполагаются в одной валюте; конвертация валют не выполняется.
Отсутствующий расход нельзя подменять нулём. Ноль — явный корректный расход.

Метки real/synthetic: bool или числовые 0/1. Строки `"false"`, `"true"`, `"0"`,
null и прочие значения неизвестны. Метрики требуют bool-параметр is_synthetic,
сначала проверяют метки, затем фильтруют **все шесть таблиц** и валидируют выбранный
набор. Ошибки выбранного набора вызывают ValueError; предупреждения не блокируют.
Связи на исключённую когорту не используются и проявляются как unknown_reference.
Для аудита всех когорт отдельно вызывайте validate_data_quality на исходных данных.
У валидатора параметр is_synthetic подавляет только предупреждение о смешивании,
но не скрывает остальные проблемы исходных данных.

Даты приводятся к UTC; даты без часового пояса считаются UTC. `now` у валидатора
можно задать явно для воспроизводимости. Некорректные даты не заменяются текущими.

## Каталог правил

Выход: DataFrame с колонками `rule_id, severity, table_name, entity_id, message`.
Пустой результат сохраняет эти колонки. Уровни только error и warning; quality
score отсутствует. Одна сущность может иметь несколько независимых проблем.

| rule_id | Уровень | Проверка |
| --- | --- | --- |
| missing_column | error | Обязательный столбец отсутствует |
| missing_id | error | Пустой первичный ID |
| duplicate_id | error | Повтор event/campaign/placement/lead/order/payment ID |
| unknown_reference | error | Неизвестные campaign у placement, placement у event, lead у order, order у payment; также lead/order/payment из properties |
| cross_cohort_reference | error | Связанные сущности имеют разные real/synthetic метки |
| unknown_event_name | error | Событие не входит в Contract v1 |
| missing_visitor_id | error | Пустой visitor_id у события или лида |
| invalid_payment_amount | error | Сумма нечисловая, бесконечная, bool, отсутствует или ≤ 0 |
| succeeded_without_paid_at | error | succeeded без корректного paid_at |
| invalid_timestamp | error | Некорректное время; nullable paid_at допустим для неуспешной оплаты |
| payment_before_order | error | paid_at раньше order.created_at |
| order_before_lead | error | order.created_at раньше lead.created_at |
| ad_click_after_lead | error | Клик с явным lead_id позже создания этого лида |
| unknown_is_synthetic | error | Невозможно определить когорту |
| invalid_cost | error | Расход отсутствует, нечисловой, бесконечный или отрицательный |
| invalid_properties | error | properties не объект и не JSON-строка объекта |
| lead_visitor_mismatch | error | Явно связанный лид принадлежит другому visitor |
| mixed_real_synthetic | warning | Есть обе когорты без явного фильтра |
| future_date | warning | Валидная дата позже now; не автоматическая ошибка |
| lead_without_event | warning | Для visitor лида нет событий в той же когорте |

Допустимые события: ad_click, landing_view, course_view, course_selected,
lead_created, manager_click, conversation_started, order_created,
payment_succeeded, course_access_granted. У всех требуется visitor_id.
session_id и placement_id могут быть null (в частности, органический трафик).
properties принимает dict либо JSON-строку объекта. lead_id/order_id/payment_id
читаются из отдельного поля, если заполнено, иначе из properties. course_id может
храниться в properties; справочника курсов во входном контракте нет, его FK не проверяется.

Поздний клик того же visitor сам по себе не ошибка: посетитель может вернуться
после создания лида или иметь несколько лидов. Валидатор отмечает нарушение только
при явной связи клика с lead_id. Модуль метрик дополнительно проверяет окно для
каждой переданной атрибуционной связи, даже если lead_id не записан в событии.

## Атрибуция — вход, а не алгоритм этого модуля

Обязательные столбцы непустого результата атрибуции:

```text
payment_id, lead_id, campaign_id, placement_id, attribution_model,
weight, payment_amount, attributed_revenue, attribution_status
```

Модель явно выбирается параметром attribution_model; строки других моделей
исключаются. Модуль не рассчитывает first/last/linear и не выбирает касание.
Поддерживаются статусы `attributed` и `unattributed`. Сумма весов по оплате и
выбранной модели не может превышать 1 (допуск 1e-9). Вес конечный, в [0, 1],
для attributed строго положительный. Дубликаты allocation по
payment/lead/campaign/placement в одной модели — ошибка.

Проверяются payment -> order -> lead, placement -> campaign, совпадение
payment_amount с суммой оплаты и attributed_revenue = payment_amount × weight
(абсолютный допуск 1e-8). Атрибуция другого real/synthetic набора отбрасывается по
связанной оплате/лиду; неизвестные IDs и связи между когортами не допускаются.
У unattributed campaign_id/placement_id должны быть null, attributed_revenue = 0.

Для attributed необходим ad_click того же visitor и указанного placement в
интервале **[lead.created_at − 30 дней, lead.created_at]**, включая обе границы.
Просмотры не заменяют ad_click. Дата оплаты не сдвигает это окно. Если такого клика
нет, доля остаётся unattributed; перераспределения на другую кампанию нет.

Оплата считается успешной только при status == "succeeded", amount > 0 и валидном
paid_at. Неуспешные попытки не дают выручку и не входят в число оплат. Без атрибуции
вся успешная оплата остаётся unattributed; при частичном покрытии туда попадает
остаток веса. Контроль: сумма выручки кампаний + unattributed_revenue = total_revenue.

**Неоплаченные лиды:** одних payment-строк недостаточно, чтобы распределить все
лиды и заказы. Производитель атрибуции может передать отдельные lead-level строки
с теми же согласованными колонками: заполнены lead/campaign/placement/model/weight,
status = attributed, а payment_id/payment_amount/attributed_revenue = null.
Это явное расширение допустимости null, а не новая модель. Оно нуждается в
поддержке интеграционного слоя. Без таких строк неоплаченные лиды остаются только
в общей воронке; модуль не выдумывает их кампании. Payment-строки также дают
принадлежность лида кампании. В кампании лид и все его заказы считаются уникально.

## Выходные таблицы и формулы

campaign_metrics: строка на каждый campaign_id выбранной когорты, включая
кампании без размещений/событий/продаж. campaign_name — только подпись.
is_synthetic и attribution_model присутствуют в результате.

| Метрика | Определение |
| --- | --- |
| clicks | Количество событий ad_click |
| unique_click_users | Уникальные visitor_id с ad_click |
| landing_users | Уникальные visitor_id с landing_view |
| course_users | Уникальные visitor_id с course_view **или** course_selected, без удвоения |
| leads | Уникальные lead_id из валидных переданных атрибуционных связей |
| orders | Уникальные order_id этих лидов |
| lead_equivalents | Для linear сумма весов lead-level атрибуции кампании; для first_touch/last_touch равно leads |
| order_equivalents | Для linear каждый заказ наследует вес своего лида; для first_touch/last_touch равно orders |
| successful_payments | Уникальные payment_id успешных оплат с долей этой кампании |
| payment_equivalents | Сумма валидных весов успешных оплат |
| attributed_revenue | Сумма переданных и проверенных долей выручки |
| cost | Сумма cost размещений кампании |
| click_to_landing_pct | landing_users / unique_click_users × 100 |
| landing_to_course_pct | course_users / landing_users × 100 |
| course_to_lead_pct | L / course_users × 100 |
| lead_to_order_pct | O / L × 100 |
| order_to_payment_pct | P / orders × 100 |
| cpl | cost / L |
| cpo | cost / O |
| cac | cost / P |
| average_payment | attributed_revenue / P |
| romi_pct | (attributed_revenue − cost) / cost × 100 |

Для linear P = payment_equivalents; для остальных моделей P = successful_payments.
Для linear L = lead_equivalents и O = order_equivalents; для first_touch/last_touch
L = leads и O = orders. Формула order_to_payment_pct остаётся прежней.

При linear поля **leads и orders неаддитивны между кампаниями**: один лид и его
заказ могут присутствовать в каждой из нескольких кампаний. Для суммирования
используются lead_equivalents и order_equivalents. При полном валидном распределении
весов лида (сумма 1) суммы эквивалентов сохраняют количество атрибутированных лидов
и их заказов. Например, один лид и один заказ с весами 0.5/0.5 дают каждой из двух
кампаний по 0.5 лида и заказа; overall_funnel по-прежнему содержит один лид и заказ.
Каждый дополнительный заказ наследует то же распределение своего лида.

Явные lead-level строки определяют веса лида независимо от количества его оплат.
Для совместимости с прежним payment-only входом используется одно уже переданное
распределение весов на лид, без суммирования по повторным оплатам. Если распределения
его оплат различаются, требуются явные lead-level строки (иначе ValueError).
Веса нескольких размещений одной кампании складываются внутри одного распределения.
Модуль не выбирает касания и не вычисляет веса самостоятельно. При неполной
атрибуции или исключении касания вне окна учитываются только валидные переданные
доли, без нормализации остатка до единицы.

Сырой distinct successful_payments неаддитивен при linear: одна оплата может
присутствовать в двух кампаниях. Для суммирования распределённых оплат используется
**только payment_equivalents**. Здесь CAC имеет заданный в задаче смысл цены оплаты,
а не стоимости первого уникального покупателя. ROMI — revenue-based proxy,
не оценка маржи или причинного эффекта рекламы.

Любой нулевой знаменатель возвращает **Python None**, не inf/NaN (выходные таблицы
имеют dtype object). Проценты не ограничиваются 100: это отношения объёмов этапов,
а не строгая последовательная когортная воронка; несколько заказов у лида допустимы.

overall_funnel — одна строка, посчитанная по уникальным ID во всём выбранном
наборе, включая органические лиды/оплаты и события без placement. Это не сумма
кампаний. Дополнительные поля total_revenue и unattributed_revenue показывают
полную выручку и её неприписанную часть. successful_payments, конверсия в оплату
и CAC здесь используют distinct оплаты; average_payment = total_revenue /
successful_payments. payment_equivalents показывает только приписанные доли,
ROMI использует attributed_revenue и весь cost.

unattributed_payments содержит payment_id, lead_id, attribution_model,
is_synthetic, attribution_status, payment_amount, unattributed_weight и
unattributed_revenue. Частично атрибутированная оплата также может попасть сюда.

## Проверка

```text
python -m pytest -q
```

Тесты охватывают все обязательные правила качества, одинаковые названия разных
кампаний, разные расходы/конверсии, общего посетителя двух кампаний, точные
формулы, нулевые знаменатели, UTC, обе границы 30 дней, поздние/старые клики,
отсутствующую и линейную атрибуцию, неоплаченные лиды, неуспешные оплаты,
неверные веса/суммы/ссылки, дубли распределения, раздельные когорты и неизменность
исходных таблиц. Фикстуры локальны в тестах, контрольные CSV не используются.
