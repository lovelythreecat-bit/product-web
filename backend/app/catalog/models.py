"""Append-only catalog versions plus transactionally advanced current heads."""

from sqlalchemy import JSON, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AgentRecord(Base):
    __tablename__ = "agent_versions"
    agent_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[str] = mapped_column(String(128), primary_key=True)
    snapshot: Mapped[dict] = mapped_column(JSON)
    endpoint: Mapped[str] = mapped_column(String(2048))
    secret_ref: Mapped[str | None] = mapped_column(String(1024))


class SpecRecord(Base):
    __tablename__ = "generation_specs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["agent_id", "agent_version"], ["agent_versions.agent_id", "agent_versions.version"]
        ),
        ForeignKeyConstraint(
            ["spec_id", "agent_id"],
            ["spec_identities.spec_id", "spec_identities.agent_id"],
            name="fk_spec_identity",
        ),
    )
    spec_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[str] = mapped_column(String(128), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(36))
    agent_version: Mapped[str] = mapped_column(String(128))
    snapshot: Mapped[dict] = mapped_column(JSON)


class PriceRecord(Base):
    __tablename__ = "price_versions"
    __table_args__ = (
        ForeignKeyConstraint(["spec_id"], ["spec_identities.spec_id"], name="fk_price_identity"),
    )
    spec_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[str] = mapped_column(String(128), primary_key=True)
    snapshot: Mapped[dict] = mapped_column(JSON)


class SpecIdentity(Base):
    """Stable unique identity; existing-version publication never mutates this row."""

    __tablename__ = "spec_identities"
    __table_args__ = (
        UniqueConstraint("spec_id", "agent_id", name="uq_spec_identity_owner"),
        ForeignKeyConstraint(["agent_id"], ["agent_heads.agent_id"], name="fk_identity_agent"),
    )
    spec_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(36))


class AgentHead(Base):
    __tablename__ = "agent_heads"
    __table_args__ = (
        ForeignKeyConstraint(
            ["agent_id", "version"], ["agent_versions.agent_id", "agent_versions.version"]
        ),
    )
    agent_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[str] = mapped_column(String(128))


class SpecHead(Base):
    __tablename__ = "spec_heads"
    __table_args__ = (
        ForeignKeyConstraint(
            ["spec_id", "version"], ["generation_specs.spec_id", "generation_specs.version"]
        ),
    )
    spec_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[str] = mapped_column(String(128))


class PriceHead(Base):
    __tablename__ = "price_heads"
    __table_args__ = (
        ForeignKeyConstraint(
            ["spec_id", "version"], ["price_versions.spec_id", "price_versions.version"]
        ),
    )
    spec_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[str] = mapped_column(String(128))
