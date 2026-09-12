from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal
from urllib.parse import quote
from uuid import uuid4

from fastapi import Cookie, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import AnyHttpUrl, BaseModel, Field
from sqlalchemy import func, select

from postupashki_mvp.database import SessionLocal
from postupashki_mvp.models import (
    Campaign,
    Event,
    Lead,
    Order,
    Payment,
    Placement,
)

app = FastAPI(
    title="Postupashki Marketing Measurement MVP",
    version="0.1.0",
)


class EventCreate(BaseModel):
    event_name: Literal[
        "landing_view",
        "course_view",
        "course_selected",
    ]
    placement_id: str | None = None
    session_id: str | None = None
    properties: dict[str, object] = Field(default_factory=dict)


class CampaignCreate(BaseModel):
    campaign_name: str = Field(min_length=1, max_length=255)
    is_synthetic: bool = False


class PlacementCreate(BaseModel):
    campaign_id: str = Field(min_length=1, max_length=64)
    channel_name: str = Field(min_length=1, max_length=255)
    target_product: str | None = Field(default=None, max_length=255)
    landing_url: AnyHttpUrl
    cost: Decimal = Field(ge=0)


class PaymentCreate(BaseModel):
    order_id: str
    amount: Decimal = Field(gt=0)
    currency: Literal["RUB"] = "RUB"


class ManagerLinkCreate(BaseModel):
    placement_id: str
    session_id: str | None = Field(default=None, max_length=64)
    course_id: str | None = Field(default=None, max_length=64)
    course_name: str = Field(min_length=1, max_length=255)


class OrderCreate(BaseModel):
    lead_token: str = Field(min_length=10, max_length=64)
    course_id: str | None = Field(default=None, max_length=64)
    course_name: str = Field(min_length=1, max_length=255)


def tracking_url(request: Request, placement_id: str) -> str:
    return str(request.url_for("track_click", placement_id=placement_id))


def iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def campaign_content(campaign: Campaign, placements_count: int = 0) -> dict[str, object]:
    return {
        "campaign_id": campaign.campaign_id,
        "campaign_name": campaign.campaign_name,
        "placements_count": placements_count,
        "created_at": iso_utc(campaign.created_at),
        "is_synthetic": campaign.is_synthetic,
    }


def placement_content(
    placement: Placement,
    campaign_name: str,
    request: Request,
) -> dict[str, object]:
    return {
        "placement_id": placement.placement_id,
        "campaign_id": placement.campaign_id,
        "campaign_name": campaign_name,
        "channel_name": placement.channel_name,
        "target_product": placement.target_product,
        "landing_url": placement.landing_url,
        "tracking_url": tracking_url(request, placement.placement_id),
        "cost": str(placement.cost),
        "created_at": iso_utc(placement.created_at),
        "is_synthetic": placement.is_synthetic,
    }


def compact_properties(**values: object) -> dict[str, object]:
    return {key: value for key, value in values.items() if value is not None}


def latest_visitor_context(session, visitor_id: str) -> Event | None:
    return session.scalar(
        select(Event)
        .where(
            Event.visitor_id == visitor_id,
            Event.placement_id.is_not(None),
        )
        .order_by(Event.occurred_at.desc(), Event.event_id.desc())
    )


def set_visitor_cookie(
    response: JSONResponse | RedirectResponse,
    visitor_id: str,
) -> None:
    response.set_cookie(
        key="postupashki_vid",
        value=visitor_id,
        max_age=60 * 60 * 24 * 90,
        httponly=True,
        samesite="lax",
    )


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/campaigns", tags=["registry"], status_code=201)
def create_campaign(payload: CampaignCreate) -> JSONResponse:
    campaign = Campaign(
        campaign_name=payload.campaign_name,
        is_synthetic=payload.is_synthetic,
    )

    with SessionLocal() as session:
        session.add(campaign)
        session.commit()
        session.refresh(campaign)

    return JSONResponse(status_code=201, content=campaign_content(campaign))


@app.get("/campaigns", tags=["registry"])
def list_campaigns() -> dict[str, object]:
    with SessionLocal() as session:
        rows = session.execute(
            select(Campaign, func.count(Placement.placement_id))
            .outerjoin(Placement)
            .group_by(Campaign.campaign_id)
            .order_by(Campaign.created_at, Campaign.campaign_id)
        ).all()

        items = [campaign_content(campaign, count) for campaign, count in rows]

    return {"items": items, "count": len(items)}


@app.post("/placements", tags=["registry"], status_code=201)
def create_placement(payload: PlacementCreate, request: Request) -> JSONResponse:
    with SessionLocal() as session:
        campaign = session.get(Campaign, payload.campaign_id)
        if campaign is None:
            raise HTTPException(status_code=404, detail="Campaign not found")

        placement = Placement(
            campaign_id=campaign.campaign_id,
            channel_name=payload.channel_name,
            target_product=payload.target_product,
            landing_url=str(payload.landing_url),
            cost=payload.cost,
            is_synthetic=campaign.is_synthetic,
        )
        session.add(placement)
        session.commit()
        session.refresh(placement)

        content = placement_content(placement, campaign.campaign_name, request)

    return JSONResponse(status_code=201, content=content)


@app.get("/placements", tags=["registry"])
def list_placements(
    request: Request,
    campaign_id: str | None = None,
) -> dict[str, object]:
    with SessionLocal() as session:
        if campaign_id is not None and session.get(Campaign, campaign_id) is None:
            raise HTTPException(status_code=404, detail="Campaign not found")

        statement = (
            select(Placement, Campaign.campaign_name)
            .join(Campaign)
            .order_by(Placement.created_at, Placement.placement_id)
        )
        if campaign_id is not None:
            statement = statement.where(Placement.campaign_id == campaign_id)

        rows = session.execute(statement).all()
        items = [
            placement_content(placement, campaign_name, request)
            for placement, campaign_name in rows
        ]

    return {"items": items, "count": len(items)}


@app.get("/t/{placement_id}", tags=["tracking"])
def track_click(
    placement_id: str,
    postupashki_vid: str | None = Cookie(default=None),
) -> RedirectResponse:
    with SessionLocal() as session:
        placement = session.get(Placement, placement_id)

        if placement is None:
            raise HTTPException(
                status_code=404,
                detail="Placement not found",
            )

        visitor_id = postupashki_vid or str(uuid4())

        event = Event(
            event_name="ad_click",
            visitor_id=visitor_id,
            placement_id=placement.placement_id,
            properties={
                "source": "tracking_redirect",
                "campaign_id": placement.campaign_id,
            },
            is_synthetic=placement.is_synthetic,
        )

        session.add(event)
        session.commit()

        response = RedirectResponse(
            url=placement.landing_url,
            status_code=302,
        )

        if postupashki_vid is None:
            set_visitor_cookie(response, visitor_id)

        return response


@app.post("/events", tags=["tracking"], status_code=201)
def register_site_event(
    payload: EventCreate,
    postupashki_vid: str | None = Cookie(default=None),
) -> JSONResponse:
    visitor_id = postupashki_vid or str(uuid4())

    with SessionLocal() as session:
        placement = None

        if payload.placement_id is not None:
            placement = session.get(Placement, payload.placement_id)

            if placement is None:
                raise HTTPException(
                    status_code=404,
                    detail="Placement not found",
                )

        event = Event(
            event_name=payload.event_name,
            visitor_id=visitor_id,
            session_id=payload.session_id,
            placement_id=payload.placement_id,
            properties=payload.properties,
            is_synthetic=(placement.is_synthetic if placement is not None else True),
        )

        session.add(event)
        session.commit()
        session.refresh(event)

    response = JSONResponse(
        status_code=201,
        content={
            "event_id": event.event_id,
            "event_name": event.event_name,
            "visitor_id": event.visitor_id,
        },
    )

    if postupashki_vid is None:
        set_visitor_cookie(response, visitor_id)

    return response


MANAGER_USERNAME = "postupashki_manager"


@app.post("/manager-link", tags=["tracking"], status_code=201)
def create_manager_link(
    payload: ManagerLinkCreate,
    postupashki_vid: str | None = Cookie(default=None),
) -> JSONResponse:
    visitor_id = postupashki_vid or str(uuid4())

    with SessionLocal() as session:
        placement = session.get(Placement, payload.placement_id)

        if placement is None:
            raise HTTPException(
                status_code=404,
                detail="Placement not found",
            )

        manager_clicked_at = datetime.now(UTC)
        lead_created_at = manager_clicked_at + timedelta(microseconds=1)
        lead = Lead(
            visitor_id=visitor_id,
            created_at=lead_created_at,
            is_synthetic=placement.is_synthetic,
        )

        session.add(lead)
        session.flush()

        manager_click = Event(
            event_name="manager_click",
            occurred_at=manager_clicked_at,
            visitor_id=visitor_id,
            session_id=payload.session_id,
            placement_id=placement.placement_id,
            properties=compact_properties(
                lead_id=lead.lead_id,
                course_id=payload.course_id,
                course_name=payload.course_name,
            ),
            is_synthetic=placement.is_synthetic,
        )
        lead_created = Event(
            event_name="lead_created",
            occurred_at=lead_created_at,
            visitor_id=visitor_id,
            session_id=payload.session_id,
            placement_id=placement.placement_id,
            properties=compact_properties(
                lead_id=lead.lead_id,
                course_id=payload.course_id,
                course_name=payload.course_name,
            ),
            is_synthetic=placement.is_synthetic,
        )

        session.add_all([manager_click, lead_created])
        session.commit()

        message = (
            f"Здравствуйте! Хочу узнать о курсе "
            f"{payload.course_name}. "
            f"Код заявки: {lead.lead_token}"
        )

        telegram_url = f"https://t.me/{MANAGER_USERNAME}?text={quote(message)}"

        response = JSONResponse(
            status_code=201,
            content={
                "lead_id": lead.lead_id,
                "lead_token": lead.lead_token,
                "visitor_id": visitor_id,
                "manager_click_event_id": manager_click.event_id,
                "lead_created_event_id": lead_created.event_id,
                "telegram_url": telegram_url,
            },
        )

        if postupashki_vid is None:
            set_visitor_cookie(response, visitor_id)

        return response


@app.post("/orders", tags=["sales"], status_code=201)
def create_order(payload: OrderCreate) -> JSONResponse:
    with SessionLocal() as session:
        lead = session.scalar(select(Lead).where(Lead.lead_token == payload.lead_token))

        if lead is None:
            raise HTTPException(
                status_code=404,
                detail="Lead not found",
            )

        existing_order = session.scalar(
            select(Order).where(
                Order.lead_id == lead.lead_id,
                Order.course_name == payload.course_name,
            )
        )

        if existing_order is not None:
            raise HTTPException(
                status_code=409,
                detail="Order already exists",
            )

        order = Order(
            lead_id=lead.lead_id,
            course_name=payload.course_name,
            status="created",
            created_at=datetime.now(UTC),
            is_synthetic=lead.is_synthetic,
        )

        session.add(order)
        session.flush()

        context = latest_visitor_context(session, lead.visitor_id)
        order_created = Event(
            event_name="order_created",
            occurred_at=order.created_at,
            visitor_id=lead.visitor_id,
            session_id=context.session_id if context is not None else None,
            placement_id=context.placement_id if context is not None else None,
            properties=compact_properties(
                lead_id=lead.lead_id,
                order_id=order.order_id,
                course_id=payload.course_id,
                course_name=payload.course_name,
                status=order.status,
            ),
            is_synthetic=order.is_synthetic,
        )
        session.add(order_created)
        session.commit()
        session.refresh(order)

        return JSONResponse(
            status_code=201,
            content={
                "order_id": order.order_id,
                "lead_id": order.lead_id,
                "course_name": order.course_name,
                "status": order.status,
                "event_id": order_created.event_id,
            },
        )


@app.post("/payments", tags=["sales"], status_code=201)
def create_payment(payload: PaymentCreate) -> JSONResponse:
    with SessionLocal() as session:
        order = session.get(Order, payload.order_id)

        if order is None:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        existing_payment = session.scalar(
            select(Payment).where(
                Payment.order_id == order.order_id,
                Payment.status == "succeeded",
            )
        )

        if existing_payment is not None:
            raise HTTPException(
                status_code=409,
                detail="Successful payment already exists",
            )

        lead = session.get(Lead, order.lead_id)
        paid_at = datetime.now(UTC)
        payment = Payment(
            order_id=order.order_id,
            amount=payload.amount,
            status="succeeded",
            paid_at=paid_at,
            is_synthetic=order.is_synthetic,
        )

        order.status = "paid"

        session.add(payment)
        session.flush()

        context = latest_visitor_context(session, lead.visitor_id)
        payment_succeeded = Event(
            event_name="payment_succeeded",
            occurred_at=paid_at,
            visitor_id=lead.visitor_id,
            session_id=context.session_id if context is not None else None,
            placement_id=context.placement_id if context is not None else None,
            properties={
                "lead_id": lead.lead_id,
                "order_id": order.order_id,
                "payment_id": payment.payment_id,
                "amount": str(payment.amount),
                "currency": payload.currency,
                "status": payment.status,
                "paid_at": iso_utc(paid_at),
            },
            is_synthetic=payment.is_synthetic,
        )
        session.add(payment_succeeded)
        session.commit()
        session.refresh(payment)

        return JSONResponse(
            status_code=201,
            content={
                "payment_id": payment.payment_id,
                "order_id": payment.order_id,
                "amount": str(payment.amount),
                "currency": payload.currency,
                "status": payment.status,
                "paid_at": iso_utc(payment.paid_at),
                "event_id": payment_succeeded.event_id,
            },
        )
