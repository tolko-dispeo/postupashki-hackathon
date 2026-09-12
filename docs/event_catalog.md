# Каталог событий MVP «Поступашки»

## Назначение

Документ задаёт контракт событий для проверки цепочки `placement_id → visitor_id → lead_id → payment_id`. Технические имена и значения идентификаторов не содержат персональных данных. Временные метки передаются в ISO 8601. Если идентификатор ещё не создан или неприменим к событию, поле остаётся пустым.

## Категории событий

- **Действие пользователя:** `ad_click`, `landing_view`, `course_view`, `course_selected`, `manager_click`.
- **Системное событие:** `lead_created`, `order_created`, `course_access_granted`.
- **Действие менеджера:** `conversation_started`.
- **Факт оплаты:** `payment_succeeded`.

`manager_click` и `conversation_started` разделены намеренно: нажатие кнопки не доказывает, что сообщение было отправлено и принято менеджером.

## События

Общий обязательный конверт события: `event_id`, `scenario_id`, `occurred_at`, `event_name`, `visitor_id`, `session_id`, `placement_id`, `properties`, `is_synthetic`. Если идентификатор неприменим или неизвестен, соответствующее поле присутствует, но остаётся пустым. `properties` всегда содержит валидный JSON-объект.

| event_name | Категория | Бизнес-смысл | Триггер | Источник | Обязательные поля | Дополнительные поля в `properties` | Пример `properties` | Способ наблюдения | Использование | Воронка | Атрибуция | Риск потери |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ad_click` | Действие пользователя | Пользователь перешёл по рекламной tracking-ссылке | Запрос tracking_url с placement_id и UTM | `tracking_backend` | Общий конверт; заполнены `visitor_id`, `session_id`, `placement_id` | `course_id`, destination_url, UTM, referrer, request_id | `{"course_id":"course_ml_start","utm_source":"telegram"}` | Автоматически | Клики, CTR и переход к визиту | Да | Да, рекламное касание | Ссылка ведёт напрямую на сайт, редирект заблокирован или параметры удалены |
| `landing_view` | Действие пользователя | Пользователь открыл сайт после рекламы | Загрузка первой страницы с трекером | `web_tracker` | Общий конверт; заполнены `visitor_id`, `session_id`, `placement_id` | `course_id`, URL, referrer, UTM, user_agent | `{"course_id":"course_ml_start","url":"https://postupashki.example/landing"}` | Автоматически | Количество визитов и конверсия landing → выбор курса | Да | Нет | Cookie или JavaScript отключены, запрос заблокирован, placement_id потерян |
| `course_view` | Действие пользователя | Пользователь открыл страницу курса | Загрузка или показ страницы курса | `web_tracker` | Общий конверт; заполнены `visitor_id`, `session_id`, `placement_id` | `course_id`, URL, referrer, dwell_time_ms | `{"course_id":"course_ml_start"}` | Автоматически | Интерес к курсам и конверсия landing → просмотр курса | Да | Нет | Трекер заблокирован или SPA-переход не отправил событие |
| `course_selected` | Действие пользователя | Пользователь выбрал курс | Подтверждение выбора курса | `web_tracker` | Общий конверт; заполнены `visitor_id`, `session_id`, `placement_id` | `course_id`, selection_method, URL | `{"course_id":"course_ml_start","selection_method":"button"}` | Автоматически | Конверсия landing → course_selected | Да | Нет | Интерфейс не отправил событие или выбор сделан вне сайта |
| `manager_click` | Действие пользователя | Пользователь нажал кнопку перехода к менеджеру | Нажатие «Написать в Telegram» | `tracking_backend` | Общий конверт; заполнены `visitor_id`, `session_id`, `placement_id` | `course_id`, page_url, destination_type | `{"course_id":"course_ml_start","destination_type":"telegram"}` | Автоматически | Конверсия course_selected → manager_click | Да | Нет | Пользователь не отправил сообщение или Telegram не открылся |
| `lead_created` | Системное событие | После перехода к менеджеру создана заявка | Система создаёт `lead_id` после `manager_click` | `tracking_backend` | Общий конверт; заполнены `visitor_id`, `session_id`, `placement_id` | `lead_id`, `course_id`, created_at | `{"lead_id":"lead_control_001","course_id":"course_ml_start"}` | Автоматически | Связь визита с лидом и CPL | Да | Да, задаёт visitor и момент создания лида | Ошибка backend или lead_id не сохранён |
| `conversation_started` | Действие менеджера | Менеджер получил первое сообщение и связал диалог с заявкой | Подтверждён первый диалог | `manager_tool` | Общий конверт; заполнены `visitor_id`, `session_id`, `placement_id` | `lead_id`, `course_id`, started_at, manager_queue | `{"lead_id":"lead_control_001","course_id":"course_ml_start"}` | Автоматически при интеграции; иначе вручную | Конверсия manager_click → conversation_started | Да | Нет | Код удалён, изменён или менеджер не зафиксировал диалог |
| `order_created` | Системное событие | Для лида создан заказ на курс | CRM сохранила новый заказ перед оплатой | `crm` | Общий конверт; заполнены `visitor_id`, `session_id`, `placement_id` | `lead_id`, `order_id`, `course_id`, amount, currency, status, created_at | `{"lead_id":"lead_control_001","order_id":"order_control_001","course_id":"course_ml_start","amount":42900,"currency":"RUB"}` | Автоматически | Связь лида с будущей оплатой | Да | Нет, служебное звено | Заказ создан вне CRM или потерян lead_id |
| `payment_succeeded` | Факт оплаты | Платёж за курс успешно подтверждён | `status == "succeeded"`, `amount > 0`, `paid_at` заполнено | `payment_system` | Общий конверт; заполнены `visitor_id`, `session_id`, `placement_id` | `lead_id`, `order_id`, `payment_id`, `course_id`, amount, currency, status, paid_at | `{"payment_id":"payment_control_001","order_id":"order_control_001","amount":42900,"currency":"RUB","status":"succeeded","paid_at":"2026-09-08T12:30:00Z"}` | Автоматически или импортом | Revenue, attributed revenue, CAC и ROMI | Да | Да, атрибутируемый результат | В платеже отсутствует order_id, импорт задержан или статус не синхронизирован |
| `course_access_granted` | Системное событие | Покупателю выдан доступ к курсу | CRM получила успешный платёж и активировала доступ | `crm` | Общий конверт; заполнены `visitor_id`, `session_id`, `placement_id` | `lead_id`, `order_id`, `payment_id`, `course_id`, access_status, granted_at | `{"order_id":"order_control_001","course_id":"course_ml_start","access_status":"granted"}` | Автоматически; при ручной выдаче вручную | Завершение операционной воронки | Да | Нет | Ошибка интеграции CRM или ручная выдача не зарегистрирована |

## Будущие расширения

Следующие события зарезервированы для возможного развития measurement system, но **не входят в Contract v1**. Сейчас API их не принимает, в контрольном `events.csv` их нет, и отправители не должны использовать эти названия в текущем потоке событий.

| event_name | Бизнес-смысл | Возможный источник | Статус |
|---|---|---|---|
| `placement_created` | Маркетолог зарегистрировал рекламное размещение и получил tracking-ссылку | `ad_registry` | Будущее расширение; не принимается API и отсутствует в контрольном `events.csv` |
| `post_published` | Рекламный пост фактически опубликован | `telegram_collector` | Будущее расширение; не принимается API и отсутствует в контрольном `events.csv` |
| `post_stats_collected` | Получена агрегированная статистика Telegram-поста | `telegram_collector` | Будущее расширение; не принимается API и отсутствует в контрольном `events.csv` |

## Полная последовательность воронки

```text
ad_click
→ landing_view
→ course_view
→ course_selected
→ manager_click
→ lead_created
→ conversation_started
→ order_created
→ payment_succeeded
→ course_access_granted
```

Не каждое реальное прохождение обязано содержать все события. Например, посетитель может уйти после просмотра страницы.

## Правила идентификаторов

| Идентификатор | Назначение и правило |
|---|---|
| `channel_id` | Псевдоним Telegram-канала. Один канал может иметь много размещений. |
| `campaign_id` | Общая рекламная кампания, объединяющая размещения. |
| `placement_id` | Уникальное рекламное размещение. Должно существовать в реестре до событий трафика. |
| `visitor_id` | Анонимный браузерный идентификатор. Сохраняется между визитами, пока доступна cookie. |
| `session_id` | Один визит. Новый визит того же `visitor_id` получает новый `session_id`. |
| `course_id` | Технический идентификатор выбранного или просматриваемого курса. |
| `lead_id` | Создаётся событием `lead_created`; во всех последующих событиях обращения используется без изменения. |
| `order_id` | Создаётся событием `order_created` и связывает лид с последующей оплатой. |
| `payment_id` | Идентификатор подтверждённого платежа. В контрольном CSV появляется в `properties` события `payment_succeeded`. |
| `user_key` | Необязательный псевдонимный ключ для будущего бота или авторизации. Не равен Telegram ID, телефону или username. |

## Контракт для разработчика и проверка полной цепочки

### Что принимать

Каждое событие должно содержать общий конверт: `event_id`, `scenario_id`, `occurred_at`, `event_name`, `visitor_id`, `session_id`, `placement_id`, `properties`, `is_synthetic`. Поля `event_id` и `payment_id` уникальны в пределах системы, `occurred_at` передаётся в UTC в формате ISO 8601, а `event_name` принимает только значение из каталога выше. Остальные обязательные поля зависят от этапа:

| Этап | Событие для проверки | Минимальные поля, которые нужно сохранить | Связь с предыдущим этапом |
|---|---|---|---|
| Placement | Запись в `placements.csv` | `channel_id`, `campaign_id`, `placement_id`, `course_id`, publication time, cost | `placement_id` уникален и создаётся до трафика; отдельное событие Contract v1 не предусмотрено |
| Ad click | `ad_click` | `event_id`, `occurred_at`, `visitor_id`, `session_id`, `placement_id` | `placement_id` должен существовать в реестре размещений |
| Visit | `landing_view` | `event_id`, `occurred_at`, `visitor_id`, `session_id`, `placement_id` | Сохраняются идентификаторы клика и визита |
| Course interest | `course_view`, `course_selected` | `visitor_id`, `session_id`, `placement_id`, `course_id` | В рамках сессии сохраняются те же `visitor_id`, `session_id` и `placement_id` |
| Manager click | `manager_click` | `visitor_id`, `session_id`, `placement_id`; `course_id` в `properties` | Клик фиксируется до создания лида и не заменяет факт разговора |
| Lead | `lead_created`, `conversation_started` | `visitor_id`, `session_id`, `placement_id`; `lead_id`, `course_id` в `properties` | `lead_id` создаётся после `manager_click` и сохраняется в событиях лида |
| Order | `order_created` | `visitor_id`, `session_id`, `placement_id`; `lead_id`, `order_id`, `course_id` в `properties` | `order_id` связывается с ранее созданным `lead_id` |
| Payment | `payment_succeeded` | `visitor_id`, `session_id`, `placement_id`; `order_id`, `payment_id`, `amount`, `currency`, `status`, `paid_at` в `properties` | `order_id` должен находиться в ранее созданном заказе |

### Как собрать цепочку

1. Найти `ad_click` по `placement_id` и получить `visitor_id` и `session_id`.
2. Найти `landing_view` с теми же идентификаторами визита.
3. Найти `lead_created` по `visitor_id`; получить `lead_id` из `properties`.
4. Найти `order_created` с тем же `properties.lead_id`; получить `order_id`.
5. Найти `payment_succeeded` с тем же `properties.order_id`; получить `payment_id` и `amount`.

Минимальная логика соединения данных:

```text
placements.placement_id
  = ad_click.placement_id
ad_click.visitor_id
  = lead_created.visitor_id
lead_created.properties.lead_id
  = order_created.properties.lead_id
order_created.properties.order_id
  = payment_succeeded.properties.order_id
```

### Приёмочные проверки

- Каждый `placement_id` из событий существует в `placements.csv`.
- Время событий внутри сценария не убывает.
- `lead_id` впервые появляется в `lead_created` и не меняется в последующих событиях этой заявки.
- `manager_click` идёт перед `lead_created`, а `conversation_started` — после создания лида.
- `order_id` появляется в `order_created`; `payment_id` и `amount` заполнены в `properties` события `payment_succeeded`, причём `amount` больше нуля.
- Для полного сценария присутствует последовательность `ad_click → landing_view → course_view → course_selected → manager_click → lead_created → conversation_started → order_created → payment_succeeded → course_access_granted`.
- Для сценария без оплаты отсутствует `payment_succeeded`; для просмотра без обращения отсутствуют `lead_id`, `order_id`, `payment_id` и события обращения.
- При нескольких касаниях один `visitor_id` может иметь несколько `session_id` и `placement_id`; история касаний сохраняется целиком.
- Если `placement_id`, `visitor_id` или `lead_id` нельзя надёжно связать, запись не присоединяется к цепочке и помечается как unattributed.

В контрольном наборе полная одноканальная цепочка находится в `scenario_01_full_funnel`. Сценарий `scenario_02_multi_touch` проверяет два placement для одного visitor, `scenario_03_lead_no_payment` — обращение без оплаты, `scenario_04_view_no_lead` — просмотр без обращения.


### Окно атрибуции

Для Contract v1 используется окно атрибуции 30 дней до создания лида.

Кандидатом считается только событие `ad_click` того же `visitor_id`, для которого выполняется условие:

`lead_created.occurred_at - 30 дней ≤ ad_click.occurred_at ≤ lead_created.occurred_at`

Если подходящих кликов несколько, по модели last-touch выбирается последний клик. Если подходящего клика нет, лид и последующая оплата остаются `unattributed`.


## Метрики

| Метрика | Числитель                                                             | Знаменатель | События и примечание |
|---|-----------------------------------------------------------------------|---|---|
| CTR | Количество кликов по tracking-ссылке                                  | Количество показов поста | В Contract v1 используется `ad_click`; автоматическая загрузка показов через `post_stats_collected` относится к будущему расширению |
| Конверсия landing → course_selected | Уникальные `visitor_id` или `session_id` с `course_selected`          | Уникальные `visitor_id` или `session_id` с `landing_view` | Единица подсчёта и окно времени должны совпадать |
| Конверсия course_selected → manager_click | Уникальные пары `visitor_id + session_id` с `manager_click`           | Уникальные выборы курса с `course_selected` | `course_selected`, `lead_created`, `manager_click` |
| Конверсия manager_click → conversation_started | Уникальные `lead_id` с `conversation_started`                         | Уникальные `lead_id` с `manager_click` | Не заменять разговор кликом |
| Конверсия conversation_started → payment | Уникальные `lead_id` с `payment_succeeded`                            | Уникальные `lead_id` с `conversation_started` | Использовать только подтверждённые платежи |
| CPL | Сумма стоимости размещений                                            | Уникальные `lead_id` с `lead_created` | В MVP лидом считается технически созданная заявка; бизнес может позже выбрать `conversation_started` как более строгий знаменатель |
| CAC | Сумма стоимости размещений                                            | Уникальные `lead_id` с `payment_succeeded` | Затраты и оплаты должны относиться к одному окну и правилу атрибуции |
| Revenue | Сумма `amount` успешных платежей                                      | Не применяется | `payment_succeeded`; без распределения по рекламе |
| Attributed revenue | Сумма `amount`, распределённая по placement согласно модели атрибуции | Не применяется | `ad_click`, `lead_created`, `order_created`, `payment_succeeded`; несвязанные оплаты остаются unattributed |
| ROMI | Attributed revenue минус стоимость размещений                         | Стоимость размещений | `(attributed revenue − cost) / cost`; считать только при `cost > 0` |

## Ограничения

- Сайт может зарегистрировать открытие страницы, но не просмотр Telegram-поста конкретным человеком.
- `manager_click` не подтверждает отправку сообщения.
- Для связи переписки с сайтом нужен `lead_id` в подготовленном сообщении либо бот/CRM.
- Пользователь может удалить код заявки из сообщения.
- Cookie может быть очищена, а пользователь может перейти с другого устройства.
- События без надёжной связи должны оставаться unattributed, а не связываться с рекламой по догадке.
- ROMI нельзя считать без стоимости размещения.
- Для собственного канала с нулевой стоимостью ROMI не рассчитывается обычным делением.

## Принятые решения и открытые вопросы

Принято, что `manager_click` фиксируется перед `lead_created`, а `lead_id` появляется только в `properties` события создания заявки и последующих событиях. Во втором сценарии один `visitor_id` используется в двух сессиях и с двумя placement_id; для last-touch-атрибуции выбирается последний подходящий `ad_click` до создания лида. Просмотр конкретным человеком в Telegram не моделируется. `placement_created`, `post_published` и `post_stats_collected` вынесены в будущие расширения и не входят в Contract v1.

Открытыми остаются правило дедупликации посетителей между устройствами, определение бизнес-лида для CPL (`lead_created` или `conversation_started`), валюта затрат и платежей, обработка возвратов и частичных оплат, а также источник фактических показов и кликов Telegram.
