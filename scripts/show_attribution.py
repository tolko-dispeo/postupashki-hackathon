from decimal import Decimal

from sqlalchemy import text

from postupashki_mvp.database import engine


LAST_TOUCH_QUERY = text(
    """
    WITH candidate_touches AS (
        SELECT
            payments.payment_id,
            payments.amount,
            leads.visitor_id,
            events.event_id,
            events.occurred_at AS touch_time,
            placements.placement_id,
            placements.channel_name,
            placements.campaign_name,
            placements.cost,
            ROW_NUMBER() OVER (
                PARTITION BY payments.payment_id
                ORDER BY events.occurred_at DESC
            ) AS touch_number
        FROM payments
        JOIN orders
            ON orders.order_id = payments.order_id
        JOIN leads
            ON leads.lead_id = orders.lead_id
        JOIN events
            ON events.visitor_id = leads.visitor_id
        JOIN placements
            ON placements.placement_id = events.placement_id
        WHERE payments.status = 'succeeded'
          AND events.event_name = 'ad_click'
          AND events.occurred_at <= leads.created_at
          AND events.occurred_at >= datetime(
              leads.created_at,
              '-30 days'
          )
    ),
    attributed_payments AS (
        SELECT *
        FROM candidate_touches
        WHERE touch_number = 1
    )
    SELECT
        placement_id,
        channel_name,
        campaign_name,
        cost,
        COUNT(DISTINCT payment_id) AS paid_orders,
        SUM(amount) AS attributed_revenue
    FROM attributed_payments
    GROUP BY
        placement_id,
        channel_name,
        campaign_name,
        cost
    ORDER BY attributed_revenue DESC
    """
)


def main() -> None:
    with engine.connect() as connection:
        rows = connection.execute(
            LAST_TOUCH_QUERY
        ).mappings().all()

    if not rows:
        print("Атрибутированных оплат пока нет")
        return

    print("Модель атрибуции: last-touch")
    print("Окно атрибуции: 30 дней")
    print()

    for row in rows:
        revenue = Decimal(str(row["attributed_revenue"]))
        cost = Decimal(str(row["cost"]))

        romi = None
        if cost > 0:
            romi = (revenue - cost) / cost * 100

        print(f"Размещение: {row['placement_id']}")
        print(f"Канал: {row['channel_name']}")
        print(f"Кампания: {row['campaign_name']}")
        print(f"Оплаченных заказов: {row['paid_orders']}")
        print(f"Атрибутированная выручка: {revenue:.2f} ₽")
        print(f"Расходы: {cost:.2f} ₽")

        if romi is None:
            print("ROMI_attr: нельзя рассчитать при нулевых расходах")
        else:
            print(f"ROMI_attr: {romi:.2f}%")

        print()


if __name__ == "__main__":
    main()