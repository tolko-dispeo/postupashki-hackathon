from sqlalchemy import select

from postupashki_mvp.database import SessionLocal
from postupashki_mvp.models import Event


def main() -> None:
    with SessionLocal() as session:
        events = session.scalars(
            select(Event).order_by(Event.occurred_at)
        ).all()

        if not events:
            print("Событий пока нет")
            return

        for event in events:
            print(
                f"{event.occurred_at} | "
                f"{event.event_name} | "
                f"visitor={event.visitor_id} | "
                f"placement={event.placement_id}"
            )


if __name__ == "__main__":
    main()