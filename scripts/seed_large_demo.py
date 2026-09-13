"""Generate a larger deterministic synthetic dataset for local dashboard demos."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from postupashki_mvp.database import SessionLocal, engine, init_db
from postupashki_mvp.models import Campaign, Event, Lead, Order, Payment, Placement


DEFAULT_CONFIG = Path("data/mock/large_demo/placements_plan.csv")
SAFE_DB_MARKERS = ("large_demo", "synthetic")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a larger local synthetic dataset for the dashboard."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Placement plan CSV (default: data/mock/large_demo/placements_plan.csv)",
    )
    parser.add_argument(
        "--multitouch",
        type=int,
        default=50,
        help="Number of additional paid multi-touch journeys (default: 50)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow clearing a database whose filename is not marked as demo/synthetic.",
    )
    return parser.parse_args()


def read_plan(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError(f"Placement plan is empty: {path}")

    integer_fields = ("clicks", "landings", "courses", "leads", "orders", "payments")
    decimal_fields = ("cost", "payment_amount")
    seen_placements: set[str] = set()

    for row in rows:
        for field in integer_fields:
            row[field] = int(row[field])
        for field in decimal_fields:
            row[field] = Decimal(row[field])

        counts = [row[field] for field in integer_fields]
        if counts != sorted(counts, reverse=True):
            raise ValueError(
                f"Funnel counts must decrease for {row['placement_id']}: {counts}"
            )
        if row["placement_id"] in seen_placements:
            raise ValueError(f"Duplicate placement_id: {row['placement_id']}")
        seen_placements.add(row["placement_id"])

    return rows


def ensure_safe_target(force: bool) -> None:
    if engine.dialect.name != "sqlite":
        raise SystemExit("Large demo seeding is allowed only for a local SQLite database.")

    database_name = Path(str(engine.url.database or "")).name.lower()
    if not force and not any(marker in database_name for marker in SAFE_DB_MARKERS):
        raise SystemExit(
            "Refusing to clear this database. Use a separate filename containing "
            "'large_demo' or 'synthetic', for example "
            "sqlite:///data/postupashki_mvp_large_demo.sqlite3."
        )


def clear_database(session) -> None:
    """Clear the selected demo database in foreign-key-safe order."""
    for model in (Payment, Order, Lead, Event, Placement, Campaign):
        session.query(model).delete(synchronize_session=False)
    session.commit()


def evenly_spaced(parent: list[int], count: int) -> set[int]:
    """Choose exactly count indices, spread across the parent sequence."""
    if count == 0:
        return set()
    if count == 1:
        return {parent[len(parent) // 2]}
    last = len(parent) - 1
    return {parent[round(i * last / (count - 1))] for i in range(count)}


def event_time(started_at: datetime, index: int, total: int, offset: int) -> datetime:
    span_seconds = int(timedelta(days=60).total_seconds())
    position = index / max(total - 1, 1)
    return started_at + timedelta(seconds=int(span_seconds * position), minutes=offset)


def seed_placement(session, config: dict, number: int, started_at: datetime) -> None:
    placement_id = config["placement_id"]
    session.add(
        Placement(
            placement_id=placement_id,
            campaign_id=config["campaign_id"],
            channel_name=config["channel_name"],
            target_product=config["target_product"],
            landing_url=(
                "https://postupashki.ru/"
                "?utm_source=telegram&utm_medium=post"
                f"&utm_campaign={config['campaign_slug']}"
                f"&utm_content={placement_id}"
            ),
            cost=config["cost"],
            created_at=started_at - timedelta(days=2),
            is_synthetic=True,
        )
    )
    # Events reference placement_id directly, so persist the parent first.
    session.flush()

    click_indices = list(range(config["clicks"]))
    landing_indices = evenly_spaced(click_indices, config["landings"])
    course_indices = evenly_spaced(sorted(landing_indices), config["courses"])
    lead_indices = evenly_spaced(sorted(course_indices), config["leads"])
    order_indices = evenly_spaced(sorted(lead_indices), config["orders"])
    payment_indices = evenly_spaced(sorted(order_indices), config["payments"])
    objects: list[object] = []

    for index in click_indices:
        visitor_id = f"v{number:02d}_{index:05d}"
        session_id = f"s{number:02d}_{index:05d}"
        click_time = event_time(started_at, index, config["clicks"], number * 3)

        objects.append(
            Event(
                event_name="ad_click",
                occurred_at=click_time,
                visitor_id=visitor_id,
                session_id=session_id,
                placement_id=placement_id,
                properties={"source": "synthetic_large_demo"},
                is_synthetic=True,
            )
        )

        if index in landing_indices:
            objects.append(
                Event(
                    event_name="landing_view",
                    occurred_at=click_time + timedelta(minutes=2),
                    visitor_id=visitor_id,
                    session_id=session_id,
                    placement_id=placement_id,
                    properties={"page": "landing"},
                    is_synthetic=True,
                )
            )

        if index in course_indices:
            objects.append(
                Event(
                    event_name="course_selected",
                    occurred_at=click_time + timedelta(minutes=5),
                    visitor_id=visitor_id,
                    session_id=session_id,
                    placement_id=placement_id,
                    properties={"course_name": config["target_product"]},
                    is_synthetic=True,
                )
            )

        if index not in lead_indices:
            continue

        lead_id = f"ld{number:02d}{index:05d}"
        manager_time = click_time + timedelta(minutes=10)
        lead_time = manager_time + timedelta(seconds=1)
        objects.extend(
            [
                Lead(
                    lead_id=lead_id,
                    lead_token=f"large_token_{number:02d}_{index:05d}",
                    visitor_id=visitor_id,
                    created_at=lead_time,
                    is_synthetic=True,
                ),
                Event(
                    event_name="manager_click",
                    occurred_at=manager_time,
                    visitor_id=visitor_id,
                    session_id=session_id,
                    placement_id=placement_id,
                    properties={"course_name": config["target_product"], "lead_id": lead_id},
                    is_synthetic=True,
                ),
                Event(
                    event_name="lead_created",
                    occurred_at=lead_time,
                    visitor_id=visitor_id,
                    session_id=session_id,
                    placement_id=placement_id,
                    properties={"course_name": config["target_product"], "lead_id": lead_id},
                    is_synthetic=True,
                ),
            ]
        )

        if index not in order_indices:
            continue

        order_id = f"or{number:02d}{index:05d}"
        order_time = lead_time + timedelta(minutes=30)
        is_paid = index in payment_indices
        objects.extend(
            [
                Order(
                    order_id=order_id,
                    lead_id=lead_id,
                    course_name=config["target_product"],
                    status="paid" if is_paid else "created",
                    created_at=order_time,
                    is_synthetic=True,
                ),
                Event(
                    event_name="order_created",
                    occurred_at=order_time,
                    visitor_id=visitor_id,
                    session_id=session_id,
                    placement_id=placement_id,
                    properties={
                        "lead_id": lead_id,
                        "order_id": order_id,
                        "course_name": config["target_product"],
                        "status": "created",
                    },
                    is_synthetic=True,
                ),
            ]
        )

        if not is_paid:
            continue

        payment_id = f"py{number:02d}{index:05d}"
        paid_at = lead_time + timedelta(hours=1)
        objects.extend(
            [
                Payment(
                    payment_id=payment_id,
                    order_id=order_id,
                    amount=config["payment_amount"],
                    status="succeeded",
                    paid_at=paid_at,
                    is_synthetic=True,
                ),
                Event(
                    event_name="payment_succeeded",
                    occurred_at=paid_at,
                    visitor_id=visitor_id,
                    session_id=session_id,
                    placement_id=placement_id,
                    properties={
                        "lead_id": lead_id,
                        "order_id": order_id,
                        "payment_id": payment_id,
                        "amount": str(config["payment_amount"]),
                        "currency": "RUB",
                        "status": "succeeded",
                        "paid_at": paid_at.isoformat(),
                    },
                    is_synthetic=True,
                ),
            ]
        )

    session.add_all(objects)
    session.flush()


def seed_multitouch(session, plan: list[dict], count: int, started_at: datetime) -> None:
    """Add paid paths with two campaign touches so attribution models visibly differ."""
    objects: list[object] = []
    total = len(plan)

    for index in range(count):
        first = plan[(index * 3) % total]
        last = plan[(index * 3 + 5) % total]
        if first["campaign_id"] == last["campaign_id"]:
            last = plan[(index * 3 + 7) % total]

        visitor_id = f"mt_v_{index:04d}"
        first_session = f"mt_s1_{index:04d}"
        last_session = f"mt_s2_{index:04d}"
        first_click = started_at + timedelta(days=index % 25, minutes=index)
        last_click = first_click + timedelta(days=2)
        lead_time = last_click + timedelta(minutes=11)
        order_time = lead_time + timedelta(minutes=30)
        paid_at = lead_time + timedelta(hours=1)
        lead_id = f"mtld{index:05d}"
        order_id = f"mtor{index:05d}"
        payment_id = f"mtpy{index:05d}"

        objects.extend(
            [
                Event(
                    event_name="ad_click",
                    occurred_at=first_click,
                    visitor_id=visitor_id,
                    session_id=first_session,
                    placement_id=first["placement_id"],
                    properties={"source": "synthetic_large_multitouch", "touch": "first"},
                    is_synthetic=True,
                ),
                Event(
                    event_name="landing_view",
                    occurred_at=first_click + timedelta(minutes=2),
                    visitor_id=visitor_id,
                    session_id=first_session,
                    placement_id=first["placement_id"],
                    properties={"page": "landing"},
                    is_synthetic=True,
                ),
                Event(
                    event_name="ad_click",
                    occurred_at=last_click,
                    visitor_id=visitor_id,
                    session_id=last_session,
                    placement_id=last["placement_id"],
                    properties={"source": "synthetic_large_multitouch", "touch": "last"},
                    is_synthetic=True,
                ),
                Event(
                    event_name="landing_view",
                    occurred_at=last_click + timedelta(minutes=2),
                    visitor_id=visitor_id,
                    session_id=last_session,
                    placement_id=last["placement_id"],
                    properties={"page": "landing"},
                    is_synthetic=True,
                ),
                Event(
                    event_name="course_selected",
                    occurred_at=last_click + timedelta(minutes=5),
                    visitor_id=visitor_id,
                    session_id=last_session,
                    placement_id=last["placement_id"],
                    properties={"course_name": last["target_product"]},
                    is_synthetic=True,
                ),
                Lead(
                    lead_id=lead_id,
                    lead_token=f"large_multitouch_token_{index:05d}",
                    visitor_id=visitor_id,
                    created_at=lead_time,
                    is_synthetic=True,
                ),
                Event(
                    event_name="manager_click",
                    occurred_at=lead_time - timedelta(seconds=1),
                    visitor_id=visitor_id,
                    session_id=last_session,
                    placement_id=last["placement_id"],
                    properties={"course_name": last["target_product"], "lead_id": lead_id},
                    is_synthetic=True,
                ),
                Event(
                    event_name="lead_created",
                    occurred_at=lead_time,
                    visitor_id=visitor_id,
                    session_id=last_session,
                    placement_id=last["placement_id"],
                    properties={"course_name": last["target_product"], "lead_id": lead_id},
                    is_synthetic=True,
                ),
                Order(
                    order_id=order_id,
                    lead_id=lead_id,
                    course_name=last["target_product"],
                    status="paid",
                    created_at=order_time,
                    is_synthetic=True,
                ),
                Event(
                    event_name="order_created",
                    occurred_at=order_time,
                    visitor_id=visitor_id,
                    session_id=last_session,
                    placement_id=last["placement_id"],
                    properties={
                        "lead_id": lead_id,
                        "order_id": order_id,
                        "course_name": last["target_product"],
                        "status": "created",
                    },
                    is_synthetic=True,
                ),
                Payment(
                    payment_id=payment_id,
                    order_id=order_id,
                    amount=last["payment_amount"],
                    status="succeeded",
                    paid_at=paid_at,
                    is_synthetic=True,
                ),
                Event(
                    event_name="payment_succeeded",
                    occurred_at=paid_at,
                    visitor_id=visitor_id,
                    session_id=last_session,
                    placement_id=last["placement_id"],
                    properties={
                        "lead_id": lead_id,
                        "order_id": order_id,
                        "payment_id": payment_id,
                        "amount": str(last["payment_amount"]),
                        "currency": "RUB",
                        "status": "succeeded",
                        "paid_at": paid_at.isoformat(),
                    },
                    is_synthetic=True,
                ),
            ]
        )

    session.add_all(objects)


def main() -> None:
    args = parse_args()
    ensure_safe_target(args.force)
    plan = read_plan(args.config)
    init_db()
    started_at = datetime.now(UTC) - timedelta(days=65)

    with SessionLocal() as session:
        clear_database(session)

        campaigns: dict[str, str] = {}
        for row in plan:
            campaigns.setdefault(row["campaign_id"], row["campaign_name"])
        session.add_all(
            Campaign(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                created_at=started_at - timedelta(days=3),
                is_synthetic=True,
            )
            for campaign_id, campaign_name in campaigns.items()
        )
        session.flush()

        for number, placement in enumerate(plan):
            seed_placement(session, placement, number, started_at)

        seed_multitouch(session, plan, args.multitouch, datetime.now(UTC) - timedelta(days=28))
        session.commit()

        counts = {
            "campaigns": session.query(Campaign).count(),
            "placements": session.query(Placement).count(),
            "events": session.query(Event).count(),
            "clicks": session.query(Event).filter(Event.event_name == "ad_click").count(),
            "leads": session.query(Lead).count(),
            "orders": session.query(Order).count(),
            "payments": session.query(Payment).count(),
        }
        revenue = sum(
            (payment.amount for payment in session.query(Payment).all()),
            Decimal("0"),
        )

    print("Large synthetic demo data created successfully.")
    print(f"Database: {engine.url}")
    for name, value in counts.items():
        print(f"{name.capitalize()}: {value}")
    print(f"Revenue: {revenue:.2f} RUB")


if __name__ == "__main__":
    main()
