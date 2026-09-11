from decimal import Decimal

from postupashki_mvp.database import SessionLocal
from postupashki_mvp.models import Placement


PLACEMENT_ID = "plc_demo_001"


def main() -> None:
    with SessionLocal() as session:
        placement = session.get(Placement, PLACEMENT_ID)

        if placement is None:
            placement = Placement(
                placement_id=PLACEMENT_ID,
                channel_name="Поступашки Олимпиады",
                campaign_name="Осенний запуск",
                target_product="ML Start",
                landing_url=(
                    "https://postupashki.ru/"
                    "?utm_source=telegram"
                    "&utm_medium=post"
                    "&utm_campaign=autumn_launch"
                    "&utm_content=plc_demo_001"
                ),
                cost=Decimal("15000.00"),
                is_synthetic=True,
            )

            session.add(placement)
            session.commit()

            print("Размещение создано")
        else:
            print("Размещение уже существует")

        saved_placement = session.get(Placement, PLACEMENT_ID)

        print(f"ID: {saved_placement.placement_id}")
        print(f"Канал: {saved_placement.channel_name}")
        print(f"Кампания: {saved_placement.campaign_name}")
        print(f"Продукт: {saved_placement.target_product}")
        print(f"Стоимость: {saved_placement.cost}")
        print(f"Ссылка: {saved_placement.landing_url}")
        print(f"Синтетические данные: {saved_placement.is_synthetic}")


if __name__ == "__main__":
    main()