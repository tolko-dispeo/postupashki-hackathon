from datetime import UTC, datetime, timedelta
from decimal import Decimal

from postupashki_mvp.database import SessionLocal
from postupashki_mvp.models import (
    Campaign,
    Event,
    Lead,
    Order,
    Payment,
    Placement,
)

DEMO_CAMPAIGNS = [
    {
        "campaign_id": "cmp_autumn_ml",
        "campaign_name": "Осенний запуск ML",
    },
    {
        "campaign_id": "cmp_career_intensive",
        "campaign_name": "Карьерный интенсив",
    },
    {
        "campaign_id": "cmp_exam_prep",
        "campaign_name": "Подготовка к поступлению",
    },
]

DEMO_PLACEMENTS = [
    {
        "placement_id": "plc_demo_001",
        "channel_name": "Data Science Jobs",
        "campaign_id": "cmp_autumn_ml",
        "campaign_slug": "autumn_ml",
        "target_product": "ML Start",
        "cost": Decimal("25000.00"),
        "payment_amount": Decimal("8950.00"),
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
        "campaign_id": "cmp_autumn_ml",
        "campaign_slug": "autumn_ml",
        "target_product": "ML Start",
        "cost": Decimal("18000.00"),
        "payment_amount": Decimal("8950.00"),
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
        "campaign_id": "cmp_career_intensive",
        "campaign_slug": "career_intensive",
        "target_product": "Career Pro",
        "cost": Decimal("30000.00"),
        "payment_amount": Decimal("12900.00"),
        "clicks": 110,
        "landings": 90,
        "courses": 45,
        "leads": 15,
        "orders": 9,
        "payments": 5,
    },
    {
        "placement_id": "plc_demo_004",
        "channel_name": "Стажировки IT",
        "campaign_id": "cmp_career_intensive",
        "campaign_slug": "career_intensive",
        "target_product": "Career Pro",
        "cost": Decimal("22000.00"),
        "payment_amount": Decimal("12900.00"),
        "clicks": 75,
        "landings": 61,
        "courses": 28,
        "leads": 9,
        "orders": 5,
        "payments": 4,
    },
    {
        "placement_id": "plc_demo_005",
        "channel_name": "Студенты IT",
        "campaign_id": "cmp_exam_prep",
        "campaign_slug": "exam_prep",
        "target_product": "Exam Start",
        "cost": Decimal("15000.00"),
        "payment_amount": Decimal("6950.00"),
        "clicks": 70,
        "landings": 58,
        "courses": 16,
        "leads": 5,
        "orders": 2,
        "payments": 1,
    },
    {
        "placement_id": "plc_demo_006",
        "channel_name": "Абитуриенты 2027",
        "campaign_id": "cmp_exam_prep",
        "campaign_slug": "exam_prep",
        "target_product": "Exam Start",
        "cost": Decimal("20000.00"),
        "payment_amount": Decimal("6950.00"),
        "clicks": 95,
        "landings": 76,
        "courses": 34,
        "leads": 11,
        "orders": 6,
        "payments": 3,
    },
]


def clear_synthetic_data(session) -> None:
    # Удаляем только synthetic-данные.
    # Порядок важен: сначала дочерние сущности.
    session.query(Payment).filter(Payment.is_synthetic.is_(True)).delete(synchronize_session=False)

    session.query(Order).filter(Order.is_synthetic.is_(True)).delete(synchronize_session=False)

    session.query(Lead).filter(Lead.is_synthetic.is_(True)).delete(synchronize_session=False)

    session.query(Event).filter(Event.is_synthetic.is_(True)).delete(synchronize_session=False)

    session.query(Placement).filter(Placement.is_synthetic.is_(True)).delete(
        synchronize_session=False
    )

    session.query(Campaign).filter(Campaign.is_synthetic.is_(True)).delete(
        synchronize_session=False
    )

    session.commit()


def seed_placement(session, config: dict, placement_number: int) -> None:
    placement = Placement(
        placement_id=config["placement_id"],
        campaign_id=config["campaign_id"],
        channel_name=config["channel_name"],
        target_product=config["target_product"],
        landing_url=(
            "https://postupashki.ru/"
            f"?utm_source=telegram"
            f"&utm_medium=post"
            f"&utm_campaign={config['campaign_slug']}"
            f"&utm_content={config['placement_id']}"
        ),
        cost=config["cost"],
        is_synthetic=True,
    )

    session.add(placement)
    session.flush()

    base_time = datetime.now(UTC) - timedelta(days=7) + timedelta(hours=placement_number * 4)

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
            manager_clicked_at = click_time + timedelta(minutes=10)
            lead_created_at = manager_clicked_at + timedelta(seconds=1)

            lead = Lead(
                visitor_id=visitor_id,
                created_at=lead_created_at,
                is_synthetic=True,
            )

            session.add(lead)
            session.flush()

            session.add_all(
                [
                    Event(
                        event_name="manager_click",
                        occurred_at=manager_clicked_at,
                        visitor_id=visitor_id,
                        session_id=session_id,
                        placement_id=config["placement_id"],
                        properties={
                            "course_name": config["target_product"],
                            "lead_id": lead.lead_id,
                        },
                        is_synthetic=True,
                    ),
                    Event(
                        event_name="lead_created",
                        occurred_at=lead_created_at,
                        visitor_id=visitor_id,
                        session_id=session_id,
                        placement_id=config["placement_id"],
                        properties={
                            "course_name": config["target_product"],
                            "lead_id": lead.lead_id,
                        },
                        is_synthetic=True,
                    ),
                ]
            )

            if i < config["orders"]:
                order_created_at = lead_created_at + timedelta(minutes=30)
                order = Order(
                    lead_id=lead.lead_id,
                    course_name=config["target_product"],
                    status="created",
                    created_at=order_created_at,
                    is_synthetic=True,
                )

                session.add(order)
                session.flush()
                session.add(
                    Event(
                        event_name="order_created",
                        occurred_at=order_created_at,
                        visitor_id=visitor_id,
                        session_id=session_id,
                        placement_id=config["placement_id"],
                        properties={
                            "lead_id": lead.lead_id,
                            "order_id": order.order_id,
                            "course_name": config["target_product"],
                            "status": "created",
                        },
                        is_synthetic=True,
                    )
                )

                if i < config["payments"]:
                    order.status = "paid"
                    paid_at = lead_created_at + timedelta(hours=1)
                    payment = Payment(
                        order_id=order.order_id,
                        amount=config["payment_amount"],
                        status="succeeded",
                        paid_at=paid_at,
                        is_synthetic=True,
                    )
                    session.add(payment)
                    session.flush()
                    session.add(
                        Event(
                            event_name="payment_succeeded",
                            occurred_at=paid_at,
                            visitor_id=visitor_id,
                            session_id=session_id,
                            placement_id=config["placement_id"],
                            properties={
                                "lead_id": lead.lead_id,
                                "order_id": order.order_id,
                                "payment_id": payment.payment_id,
                                "amount": str(payment.amount),
                                "currency": "RUB",
                                "status": payment.status,
                                "paid_at": paid_at.isoformat(),
                            },
                            is_synthetic=True,
                        )
                    )


def seed_cross_campaign_journey(session) -> None:
    """Create one visitor whose sale belongs to the latest campaign touch."""
    visitor_id = "shared_cross_campaign_001"
    session_id = "shared_cross_campaign_session_001"
    started_at = datetime.now(UTC) - timedelta(days=2)

    session.add_all(
        [
            Event(
                event_name="ad_click",
                occurred_at=started_at,
                visitor_id=visitor_id,
                session_id=session_id,
                placement_id="plc_demo_001",
                properties={"source": "synthetic_cross_campaign"},
                is_synthetic=True,
            ),
            Event(
                event_name="landing_view",
                occurred_at=started_at + timedelta(minutes=2),
                visitor_id=visitor_id,
                session_id=session_id,
                placement_id="plc_demo_001",
                properties={"page": "landing"},
                is_synthetic=True,
            ),
            Event(
                event_name="ad_click",
                occurred_at=started_at + timedelta(days=1),
                visitor_id=visitor_id,
                session_id=session_id,
                placement_id="plc_demo_003",
                properties={"source": "synthetic_cross_campaign"},
                is_synthetic=True,
            ),
            Event(
                event_name="landing_view",
                occurred_at=started_at + timedelta(days=1, minutes=2),
                visitor_id=visitor_id,
                session_id=session_id,
                placement_id="plc_demo_003",
                properties={"page": "landing"},
                is_synthetic=True,
            ),
            Event(
                event_name="course_selected",
                occurred_at=started_at + timedelta(days=1, minutes=5),
                visitor_id=visitor_id,
                session_id=session_id,
                placement_id="plc_demo_003",
                properties={"course_name": "Career Pro"},
                is_synthetic=True,
            ),
        ]
    )

    manager_clicked_at = started_at + timedelta(days=1, minutes=10)
    lead_created_at = manager_clicked_at + timedelta(seconds=1)
    lead = Lead(
        visitor_id=visitor_id,
        created_at=lead_created_at,
        is_synthetic=True,
    )
    session.add(lead)
    session.flush()

    session.add_all(
        [
            Event(
                event_name="manager_click",
                occurred_at=manager_clicked_at,
                visitor_id=visitor_id,
                session_id=session_id,
                placement_id="plc_demo_003",
                properties={"course_name": "Career Pro", "lead_id": lead.lead_id},
                is_synthetic=True,
            ),
            Event(
                event_name="lead_created",
                occurred_at=lead_created_at,
                visitor_id=visitor_id,
                session_id=session_id,
                placement_id="plc_demo_003",
                properties={"course_name": "Career Pro", "lead_id": lead.lead_id},
                is_synthetic=True,
            ),
        ]
    )

    order_created_at = lead_created_at + timedelta(minutes=30)
    order = Order(
        lead_id=lead.lead_id,
        course_name="Career Pro",
        status="paid",
        created_at=order_created_at,
        is_synthetic=True,
    )
    session.add(order)
    session.flush()
    session.add(
        Event(
            event_name="order_created",
            occurred_at=order_created_at,
            visitor_id=visitor_id,
            session_id=session_id,
            placement_id="plc_demo_003",
            properties={
                "lead_id": lead.lead_id,
                "order_id": order.order_id,
                "course_name": "Career Pro",
                "status": "created",
            },
            is_synthetic=True,
        )
    )

    paid_at = lead_created_at + timedelta(hours=1)
    payment = Payment(
        order_id=order.order_id,
        amount=Decimal("12900.00"),
        status="succeeded",
        paid_at=paid_at,
        is_synthetic=True,
    )
    session.add(payment)
    session.flush()
    session.add(
        Event(
            event_name="payment_succeeded",
            occurred_at=paid_at,
            visitor_id=visitor_id,
            session_id=session_id,
            placement_id="plc_demo_003",
            properties={
                "lead_id": lead.lead_id,
                "order_id": order.order_id,
                "payment_id": payment.payment_id,
                "amount": str(payment.amount),
                "currency": "RUB",
                "status": payment.status,
                "paid_at": paid_at.isoformat(),
            },
            is_synthetic=True,
        )
    )


def main() -> None:
    with SessionLocal() as session:
        clear_synthetic_data(session)

        session.add_all(
            [
                Campaign(
                    campaign_id=config["campaign_id"],
                    campaign_name=config["campaign_name"],
                    is_synthetic=True,
                )
                for config in DEMO_CAMPAIGNS
            ]
        )
        session.flush()

        for number, placement_config in enumerate(DEMO_PLACEMENTS):
            seed_placement(
                session,
                placement_config,
                number,
            )

        seed_cross_campaign_journey(session)

        session.commit()

    print("Synthetic demo data created successfully.")
    print("Campaigns: 3")
    print("Placements: 6")
    print("Clicks: 497")
    print("Leads: 63")
    print("Payments: 23")


if __name__ == "__main__":
    main()
