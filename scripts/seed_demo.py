from datetime import datetime, timedelta, timezone
from decimal import Decimal

from postupashki_mvp.database import SessionLocal
from postupashki_mvp.models import (
    Event,
    Lead,
    Order,
    Payment,
    Placement,
)


DEMO_PLACEMENTS = [
    {
        "placement_id": "plc_demo_001",
        "channel_name": "Data Science Jobs",
        "campaign_name": "Осенний запуск",
        "target_product": "ML Start",
        "cost": Decimal("25000.00"),
        "clicks": 80,
        "landings": 70,
        "courses": 35,
        "leads": 14,
        "orders": 8,
        "payments": 6,
    },
    {
        "placement_id": "plc_demo_002",
        "channel_name": "Python для всех",
        "campaign_name": "Осенний запуск",
        "target_product": "ML Start",
        "cost": Decimal("18000.00"),
        "clicks": 65,
        "landings": 52,
        "courses": 24,
        "leads": 8,
        "orders": 5,
        "payments": 3,
    },
    {
        "placement_id": "plc_demo_003",
        "channel_name": "Карьера BigTech",
        "campaign_name": "Осенний запуск",
        "target_product": "ML Start",
        "cost": Decimal("30000.00"),
        "clicks": 110,
        "landings": 90,
        "courses": 45,
        "leads": 15,
        "orders": 9,
        "payments": 5,
    },
    {
        "placement_id": "plc_demo_004",
        "channel_name": "Студенты IT",
        "campaign_name": "Осенний запуск",
        "target_product": "ML Start",
        "cost": Decimal("15000.00"),
        "clicks": 70,
        "landings": 58,
        "courses": 16,
        "leads": 5,
        "orders": 2,
        "payments": 1,
    },
]


def clear_synthetic_data(session) -> None:
    # Удаляем только synthetic-данные.
    # Порядок важен: сначала дочерние сущности.
    session.query(Payment).filter(
        Payment.is_synthetic.is_(True)
    ).delete(synchronize_session=False)

    session.query(Order).filter(
        Order.is_synthetic.is_(True)
    ).delete(synchronize_session=False)

    session.query(Lead).filter(
        Lead.is_synthetic.is_(True)
    ).delete(synchronize_session=False)

    session.query(Event).filter(
        Event.is_synthetic.is_(True)
    ).delete(synchronize_session=False)

    session.query(Placement).filter(
        Placement.is_synthetic.is_(True)
    ).delete(synchronize_session=False)

    session.commit()


def seed_placement(session, config: dict, placement_number: int) -> None:
    placement = Placement(
        placement_id=config["placement_id"],
        channel_name=config["channel_name"],
        campaign_name=config["campaign_name"],
        target_product=config["target_product"],
        landing_url=(
            "https://postupashki.ru/"
            f"?utm_source=telegram"
            f"&utm_medium=post"
            f"&utm_campaign=autumn_launch"
            f"&utm_content={config['placement_id']}"
        ),
        cost=config["cost"],
        is_synthetic=True,
    )

    session.add(placement)
    session.flush()

    base_time = (
        datetime.now(timezone.utc)
        - timedelta(days=7)
        + timedelta(hours=placement_number * 4)
    )

    for i in range(config["clicks"]):
        visitor_id = f"{config['placement_id']}_visitor_{i:03d}"
        session_id = f"{config['placement_id']}_session_{i:03d}"

        click_time = base_time + timedelta(minutes=i)

        session.add(
            Event(
                event_name="ad_click",
                occurred_at=click_time,
                visitor_id=visitor_id,
                session_id=session_id,
                placement_id=config["placement_id"],
                properties={"source": "synthetic_demo"},
                is_synthetic=True,
            )
        )

        if i < config["landings"]:
            session.add(
                Event(
                    event_name="landing_view",
                    occurred_at=click_time + timedelta(minutes=2),
                    visitor_id=visitor_id,
                    session_id=session_id,
                    placement_id=config["placement_id"],
                    properties={"page": "landing"},
                    is_synthetic=True,
                )
            )

        if i < config["courses"]:
            session.add(
                Event(
                    event_name="course_selected",
                    occurred_at=click_time + timedelta(minutes=5),
                    visitor_id=visitor_id,
                    session_id=session_id,
                    placement_id=config["placement_id"],
                    properties={"course_name": config["target_product"]},
                    is_synthetic=True,
                )
            )

        if i < config["leads"]:
            lead_time = click_time + timedelta(minutes=10)

            lead = Lead(
                visitor_id=visitor_id,
                created_at=lead_time,
                is_synthetic=True,
            )

            session.add(lead)
            session.flush()

            session.add(
                Event(
                    event_name="manager_click",
                    occurred_at=lead_time,
                    visitor_id=visitor_id,
                    session_id=session_id,
                    placement_id=config["placement_id"],
                    properties={
                        "course_name": config["target_product"],
                        "lead_id": lead.lead_id,
                    },
                    is_synthetic=True,
                )
            )

            if i < config["orders"]:
                order = Order(
                    lead_id=lead.lead_id,
                    course_name=config["target_product"],
                    status="created",
                    created_at=lead_time + timedelta(minutes=30),
                    is_synthetic=True,
                )

                session.add(order)
                session.flush()

                if i < config["payments"]:
                    order.status = "paid"

                    session.add(
                        Payment(
                            order_id=order.order_id,
                            amount=Decimal("8950.00"),
                            status="succeeded",
                            paid_at=lead_time + timedelta(hours=1),
                            is_synthetic=True,
                        )
                    )


def main() -> None:
    with SessionLocal() as session:
        clear_synthetic_data(session)

        for number, placement_config in enumerate(DEMO_PLACEMENTS):
            seed_placement(
                session,
                placement_config,
                number,
            )

        session.commit()

    print("Synthetic demo data created successfully.")
    print("Placements: 4")
    print("Clicks: 325")
    print("Leads: 42")
    print("Payments: 15")


if __name__ == "__main__":
    main()