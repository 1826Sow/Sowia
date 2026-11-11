"""FINAL TEC AI Gateway — isolated prototype API.

This prototype provides tenant registration, API-key authentication and
atomic usage reservations. It does not call an AI model or charge money.
"""
import uuid
from collections.abc import Generator

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker

from .models import Application, Base, Organization, UsageRecord
from .security import generate_api_key, hash_api_key, token_matches

class RegisterApplication(BaseModel):
    organization_name: str = Field(min_length=2, max_length=160)
    application_name: str = Field(min_length=2, max_length=160)
    budget_units: int = Field(gt=0, le=10_000_000)

class RegistrationResult(BaseModel):
    organization_id: str
    application_id: str
    api_key: str
    budget_units: int
    note: str

class ReservationRequest(BaseModel):
    units: int = Field(gt=0, le=1_000_000)

def create_app(database_url: str = "sqlite:///./final_tec_dev.db", admin_token: str | None = None) -> FastAPI:
    """Create an isolated app instance; tests can inject a temporary database."""
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    # Prototype convenience only. Production deployment must use reviewed migrations.
    Base.metadata.create_all(engine)

    api = FastAPI(
        title="FINAL TEC AI Gateway",
        version="0.1.0-prototype",
        description="Isolated prototype: application registration, API-key auth and simulated usage quotas.",
    )
    api.state.engine = engine

    def get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    def authenticated_application(
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
        db: Session = Depends(get_db),
    ) -> tuple[Application, Organization]:
        if not x_api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")
        row = db.execute(
            select(Application, Organization)
            .join(Organization, Application.organization_id == Organization.id)
            .where(Application.api_key_hash == hash_api_key(x_api_key))
        ).first()
        if row is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        application, organization = row
        if not application.active or not organization.active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Application or organization disabled")
        return application, organization

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "final-tec-ai-gateway", "stage": "prototype"}

    @api.post("/v1/applications", response_model=RegistrationResult, status_code=201)
    def register_application(
        payload: RegisterApplication,
        x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
        db: Session = Depends(get_db),
    ) -> RegistrationResult:
        if not token_matches(x_admin_token, admin_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bootstrap administrator token required")
        organization_id, application_id = str(uuid.uuid4()), str(uuid.uuid4())
        raw_api_key = generate_api_key()
        db.add_all([
            Organization(id=organization_id, name=payload.organization_name, budget_units=payload.budget_units, used_units=0),
            Application(id=application_id, organization_id=organization_id, name=payload.application_name, api_key_hash=hash_api_key(raw_api_key)),
        ])
        db.commit()
        return RegistrationResult(
            organization_id=organization_id,
            application_id=application_id,
            api_key=raw_api_key,
            budget_units=payload.budget_units,
            note="Store this API key securely; it cannot be retrieved later.",
        )

    @api.get("/v1/usage")
    def get_usage(identity: tuple[Application, Organization] = Depends(authenticated_application)) -> dict[str, int | str]:
        application, organization = identity
        return {
            "application_id": application.id,
            "budget_units": organization.budget_units,
            "used_units": organization.used_units,
            "remaining_units": max(organization.budget_units - organization.used_units, 0),
        }

    @api.post("/v1/usage/reservations", status_code=201)
    def reserve_usage(
        payload: ReservationRequest,
        identity: tuple[Application, Organization] = Depends(authenticated_application),
        db: Session = Depends(get_db),
    ) -> dict[str, int | str]:
        application, organization = identity
        # Conditional UPDATE makes quota validation and reservation a single DB operation.
        reserved_id = db.execute(
            update(Organization)
            .where(
                Organization.id == organization.id,
                Organization.active.is_(True),
                Organization.used_units + payload.units <= Organization.budget_units,
            )
            .values(used_units=Organization.used_units + payload.units)
            .returning(Organization.id)
        ).scalar_one_or_none()
        if reserved_id is None:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Budget limit reached")
        record = UsageRecord(
            id=str(uuid.uuid4()),
            organization_id=organization.id,
            application_id=application.id,
            units=payload.units,
        )
        db.add(record)
        db.commit()
        refreshed = db.get(Organization, organization.id)
        return {
            "reservation_id": record.id,
            "reserved_units": payload.units,
            "used_units": refreshed.used_units,
            "remaining_units": max(refreshed.budget_units - refreshed.used_units, 0),
            "billing": "simulated_only",
        }

    return api

app = create_app()
