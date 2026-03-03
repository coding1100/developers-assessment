from datetime import date
from typing import Any

from fastapi import APIRouter, Query

from app.api.deps import SessionDep
from app.api.routes.worklogs.service import WorkLogService
from app.models import (
    RemittanceSettlementsPublic,
    WorkLogAmountsPublic,
    WorkLogRemittanceStatus,
)

router = APIRouter(tags=["worklogs"])


@router.post(
    "/generate-remittances-for-all-users",
    response_model=RemittanceSettlementsPublic,
)
def generate_remittances_for_all_users(
    session: SessionDep,
    as_of_date: date | None = Query(default=None, alias="asOfDate"),
) -> Any:
    return WorkLogService.generate_remittances_for_all_users(session, as_of_date)


@router.get("/list-all-worklogs", response_model=WorkLogAmountsPublic)
def list_all_worklogs(
    session: SessionDep,
    remittance_status: WorkLogRemittanceStatus | None = Query(
        default=None,
        alias="remittanceStatus",
    ),
) -> Any:
    return WorkLogService.list_all_worklogs(session, remittance_status)
