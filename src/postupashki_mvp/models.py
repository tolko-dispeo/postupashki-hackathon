
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from postupashki_mvp.database import Base


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Placement(Base):
    """One paid or owned advertising placement."""

    __tablename__ = "placements"

    placement_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    channel_name: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_product: Mapped[str | None] = mapped_column(String(255))
    landing_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Event(Base):
    """An immutable user action, for example ad_click or manager_click."""

    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_visitor_time", "visitor_id", "occurred_at"),
    )

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    visitor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(64))
    placement_id: Mapped[str | None] = mapped_column(
        ForeignKey("placements.placement_id"), index=True
    )
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Lead(Base):
    """A request sent to a manager and linked to an anonymous visitor."""

    __tablename__ = "leads"

    lead_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    lead_token: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, default=new_id
    )
    visitor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Order(Base):
    """A commercial order created for a lead."""

    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.lead_id"), nullable=False, index=True)
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="created")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Payment(Base):
    """A payment attempt associated with an order."""

    __tablename__ = "payments"

    payment_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.order_id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
