from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.models import (
    Remittance,
    RemittanceStatus,
    UserCreate,
    WorkAdjustment,
    WorkLog,
    WorkSegment,
)
from tests.utils.utils import random_email, random_lower_string


def _to_decimal(value: str | float | int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _create_user(db: Session, is_active: bool = True):
    user_in = UserCreate(email=random_email(), password=random_lower_string())
    user = crud.create_user(session=db, user_create=user_in)
    if not is_active:
        user.is_active = False
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _create_worklog_with_amount(
    db: Session,
    user_id,
    title: str,
    minutes: int,
    hourly_rate: Decimal,
    adjustment_amount: Decimal | None = None,
) -> WorkLog:
    worklog = WorkLog(user_id=user_id, title=title)
    db.add(worklog)
    db.commit()
    db.refresh(worklog)

    segment = WorkSegment(
        worklog_id=worklog.id,
        minutes=minutes,
        hourly_rate=hourly_rate,
    )
    db.add(segment)
    db.commit()

    if adjustment_amount is not None:
        adjustment = WorkAdjustment(
            worklog_id=worklog.id,
            amount=adjustment_amount,
            reason="Adjustment",
        )
        db.add(adjustment)
        db.commit()

    db.refresh(worklog)
    return worklog


def test_list_all_worklogs_with_amounts(client: TestClient, db: Session) -> None:
    user = _create_user(db)
    worklog = _create_worklog_with_amount(
        db,
        user.id,
        "Worklog A",
        minutes=120,
        hourly_rate=Decimal("50.00"),
        adjustment_amount=Decimal("-10.00"),
    )

    response = client.get(
        f"{settings.API_V1_STR}/list-all-worklogs",
        params={"remittanceStatus": "UNREMITTED"},
    )

    assert response.status_code == 200
    payload = response.json()
    target_items = [item for item in payload["data"] if item["id"] == str(worklog.id)]
    assert len(target_items) == 1

    target = target_items[0]
    assert _to_decimal(target["total_amount"]) == Decimal("90.00")
    assert _to_decimal(target["settled_amount"]) == Decimal("0.00")
    assert _to_decimal(target["unremitted_amount"]) == Decimal("90.00")
    assert target["remittance_status"] == "UNREMITTED"


def test_generate_remittances_for_all_users_is_idempotent(
    client: TestClient, db: Session
) -> None:
    user = _create_user(db)
    worklog = _create_worklog_with_amount(
        db,
        user.id,
        "Worklog B",
        minutes=60,
        hourly_rate=Decimal("120.00"),
    )

    before = len(
        db.exec(select(Remittance).where(Remittance.user_id == user.id)).all()
    )

    first_response = client.post(f"{settings.API_V1_STR}/generate-remittances-for-all-users")
    assert first_response.status_code == 200

    first_payload = first_response.json()
    first_user_entries = [
        item for item in first_payload["data"] if item["user_id"] == str(user.id)
    ]
    assert len(first_user_entries) == 1
    assert first_user_entries[0]["status"] == RemittanceStatus.REMITTED.value
    assert _to_decimal(first_user_entries[0]["total_amount"]) == Decimal("120.00")

    db.refresh(worklog)
    assert _to_decimal(worklog.settled_amount) == Decimal("120.00")

    second_response = client.post(
        f"{settings.API_V1_STR}/generate-remittances-for-all-users"
    )
    assert second_response.status_code == 200

    after = len(db.exec(select(Remittance).where(Remittance.user_id == user.id)).all())
    assert after == before + 1


def test_generate_remittances_handles_inactive_user_failure(
    client: TestClient, db: Session
) -> None:
    user = _create_user(db, is_active=False)
    worklog = _create_worklog_with_amount(
        db,
        user.id,
        "Worklog C",
        minutes=30,
        hourly_rate=Decimal("100.00"),
    )

    response = client.post(f"{settings.API_V1_STR}/generate-remittances-for-all-users")
    assert response.status_code == 200

    payload = response.json()
    user_entries = [item for item in payload["data"] if item["user_id"] == str(user.id)]
    assert len(user_entries) == 1
    assert user_entries[0]["status"] == RemittanceStatus.FAILED.value

    db.refresh(worklog)
    assert _to_decimal(worklog.settled_amount) == Decimal("0.00")

    remittances = db.exec(select(Remittance).where(Remittance.user_id == user.id)).all()
    assert len(remittances) >= 1
    assert remittances[-1].status == RemittanceStatus.FAILED.value
