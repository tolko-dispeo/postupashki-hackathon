from typing import Literal
from uuid import uuid4
from urllib.parse import quote
from sqlalchemy import select

from fastapi import Cookie, FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from postupashki_mvp.database import SessionLocal
from postupashki_mvp.models import (
    Event,
    Lead,
    Order,
    Payment,
    Placement,
)

from datetime import datetime, timezone
from decimal import Decimal

app = FastAPI(
    title="Postupashki Marketing Measurement MVP",
    version="0.1.0",
)


class EventCreate(BaseModel):
    event_name: Literal[
        "landing_view",
        "course_view",
        "course_selected",
        "manager_click",
    ]
    placement_id: str | None = None
    session_id: str | None = None
    properties: dict[str, object] = Field(default_factory=dict)

class PaymentCreate(BaseModel):
    order_id: str
    amount: Decimal = Field(gt=0)
class ManagerLinkCreate(BaseModel):
    placement_id: str
    course_name: str = Field(min_length=1, max_length=255)

class OrderCreate(BaseModel):
    lead_token: str = Field(min_length=10, max_length=64)
    course_name: str = Field(min_length=1, max_length=255)

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
            properties={"source": "tracking_redirect"},
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
            is_synthetic=(
                placement.is_synthetic
                if placement is not None
                else True
            ),
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

        lead = Lead(
            visitor_id=visitor_id,
            is_synthetic=placement.is_synthetic,
        )

        session.add(lead)
        session.flush()

        event = Event(
            event_name="manager_click",
            visitor_id=visitor_id,
            placement_id=placement.placement_id,
            properties={
                "course_name": payload.course_name,
                "lead_id": lead.lead_id,
            },
            is_synthetic=placement.is_synthetic,
        )

        session.add(event)
        session.commit()

        message = (
            f"Здравствуйте! Хочу узнать о курсе "
            f"{payload.course_name}. "
            f"Код заявки: {lead.lead_token}"
        )

        telegram_url = (
            f"https://t.me/{MANAGER_USERNAME}"
            f"?text={quote(message)}"
        )

        response = JSONResponse(
            status_code=201,
            content={
                "lead_id": lead.lead_id,
                "lead_token": lead.lead_token,
                "visitor_id": visitor_id,
                "telegram_url": telegram_url,
            },
        )

        if postupashki_vid is None:
            set_visitor_cookie(response, visitor_id)

        return response


@app.post("/orders", tags=["sales"], status_code=201)
def create_order(payload: OrderCreate) -> JSONResponse:
    with SessionLocal() as session:
        lead = session.scalar(
            select(Lead).where(
                Lead.lead_token == payload.lead_token
            )
        )

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
            is_synthetic=lead.is_synthetic,
        )

        session.add(order)
        session.commit()
        session.refresh(order)

        return JSONResponse(
            status_code=201,
            content={
                "order_id": order.order_id,
                "lead_id": order.lead_id,
                "course_name": order.course_name,
                "status": order.status,
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

        payment = Payment(
            order_id=order.order_id,
            amount=payload.amount,
            status="succeeded",
            paid_at=datetime.now(timezone.utc),
            is_synthetic=order.is_synthetic,
        )

        order.status = "paid"

        session.add(payment)
        session.commit()
        session.refresh(payment)

        return JSONResponse(
            status_code=201,
            content={
                "payment_id": payment.payment_id,
                "order_id": payment.order_id,
                "amount": str(payment.amount),
                "status": payment.status,
                "paid_at": payment.paid_at.isoformat(),
            },
        )