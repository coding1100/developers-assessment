import uuid
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlmodel import Session, select

from app.models import (
    Remittance,
    RemittanceLine,
    RemittanceLinePublic,
    RemittanceSettlementPublic,
    RemittanceSettlementsPublic,
    RemittanceStatus,
    User,
    WorkAdjustment,
    WorkLog,
    WorkLogAmountPublic,
    WorkLogAmountsPublic,
    WorkLogRemittanceStatus,
    WorkSegment,
)


class WorkLogService:
    @staticmethod
    def _quantize_amount(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _calculate_total_segment_amount(session: Session, worklog_id: uuid.UUID) -> Decimal:
        total = Decimal("0.00")
        statement = select(WorkSegment).where(WorkSegment.worklog_id == worklog_id)
        statement = statement.where(WorkSegment.is_active)
        segments = session.exec(statement).all()
        for segment in segments:
            hours = Decimal(segment.minutes) / Decimal("60")
            total += hours * segment.hourly_rate
        return WorkLogService._quantize_amount(total)

    @staticmethod
    def _calculate_total_adjustment_amount(session: Session, worklog_id: uuid.UUID) -> Decimal:
        total = Decimal("0.00")
        statement = select(WorkAdjustment).where(WorkAdjustment.worklog_id == worklog_id)
        statement = statement.where(WorkAdjustment.is_active)
        adjustments = session.exec(statement).all()
        for adjustment in adjustments:
            total += adjustment.amount
        return WorkLogService._quantize_amount(total)

    @staticmethod
    def _calculate_worklog_amounts(
        session: Session, worklog: WorkLog
    ) -> tuple[Decimal, Decimal, Decimal, WorkLogRemittanceStatus]:
        segment_total = WorkLogService._calculate_total_segment_amount(session, worklog.id)
        adjustment_total = WorkLogService._calculate_total_adjustment_amount(
            session, worklog.id
        )
        total_amount = WorkLogService._quantize_amount(segment_total + adjustment_total)
        settled_amount = WorkLogService._quantize_amount(worklog.settled_amount)
        unremitted_amount = WorkLogService._quantize_amount(total_amount - settled_amount)
        status = WorkLogRemittanceStatus.REMITTED
        if unremitted_amount != Decimal("0.00"):
            status = WorkLogRemittanceStatus.UNREMITTED
        return total_amount, settled_amount, unremitted_amount, status

    @staticmethod
    def list_all_worklogs(
        session: Session,
        remittance_status: WorkLogRemittanceStatus | None = None,
    ) -> WorkLogAmountsPublic:
        statement = select(WorkLog).where(WorkLog.is_active)
        worklogs = session.exec(statement).all()
        results: list[WorkLogAmountPublic] = []
        for worklog in worklogs:
            total_amount, settled_amount, unremitted_amount, status = (
                WorkLogService._calculate_worklog_amounts(session, worklog)
            )
            if remittance_status and status != remittance_status:
                continue
            results.append(
                WorkLogAmountPublic(
                    id=worklog.id,
                    user_id=worklog.user_id,
                    title=worklog.title,
                    total_amount=total_amount,
                    settled_amount=settled_amount,
                    unremitted_amount=unremitted_amount,
                    remittance_status=status,
                )
            )
        return WorkLogAmountsPublic(data=results, count=len(results))

    @staticmethod
    def _resolve_remittance_status(
        user_is_active: bool,
        amount: Decimal,
    ) -> tuple[RemittanceStatus, str | None]:
        if not user_is_active:
            return RemittanceStatus.FAILED, "Payout failed because user is inactive"
        if amount <= Decimal("0.00"):
            return (
                RemittanceStatus.CANCELLED,
                "Payout cancelled because amount is non-positive",
            )
        return RemittanceStatus.REMITTED, None

    @staticmethod
    def generate_remittances_for_all_users(
        session: Session,
        as_of_date: date | None = None,
    ) -> RemittanceSettlementsPublic:
        run_date = as_of_date or date.today()
        period_start = run_date.replace(day=1)
        results: list[RemittanceSettlementPublic] = []

        users = session.exec(select(User)).all()
        for user in users:
            statement = select(WorkLog).where(WorkLog.user_id == user.id)
            statement = statement.where(WorkLog.is_active)
            user_worklogs = session.exec(statement).all()

            pending_lines: list[tuple[WorkLog, Decimal]] = []
            total_amount = Decimal("0.00")

            for worklog in user_worklogs:
                _, _, unremitted_amount, _ = WorkLogService._calculate_worklog_amounts(
                    session, worklog
                )
                if unremitted_amount == Decimal("0.00"):
                    continue
                pending_lines.append((worklog, unremitted_amount))
                total_amount += unremitted_amount

            if not pending_lines:
                continue

            total_amount = WorkLogService._quantize_amount(total_amount)
            remittance = Remittance(
                user_id=user.id,
                period_start=period_start,
                period_end=run_date,
                status=RemittanceStatus.PENDING.value,
                total_amount=total_amount,
            )
            session.add(remittance)
            session.commit()
            session.refresh(remittance)

            line_items: list[RemittanceLinePublic] = []
            for worklog, amount in pending_lines:
                remittance_line = RemittanceLine(
                    remittance_id=remittance.id,
                    worklog_id=worklog.id,
                    amount=WorkLogService._quantize_amount(amount),
                )
                session.add(remittance_line)
                session.commit()
                session.refresh(remittance_line)
                line_items.append(
                    RemittanceLinePublic(
                        worklog_id=worklog.id,
                        amount=remittance_line.amount,
                    )
                )

            resolved_status, failure_reason = WorkLogService._resolve_remittance_status(
                user.is_active,
                total_amount,
            )

            remittance.status = resolved_status.value
            remittance.failure_reason = failure_reason
            remittance.processed_at = datetime.utcnow()
            session.add(remittance)
            session.commit()
            session.refresh(remittance)

            if resolved_status == RemittanceStatus.REMITTED:
                for worklog, amount in pending_lines:
                    worklog.settled_amount = WorkLogService._quantize_amount(
                        worklog.settled_amount + amount
                    )
                    session.add(worklog)
                    session.commit()
                    session.refresh(worklog)

            results.append(
                RemittanceSettlementPublic(
                    id=remittance.id,
                    user_id=remittance.user_id,
                    status=remittance.status,
                    total_amount=remittance.total_amount,
                    period_start=remittance.period_start,
                    period_end=remittance.period_end,
                    failure_reason=remittance.failure_reason,
                    line_items=line_items,
                )
            )

        return RemittanceSettlementsPublic(data=results, count=len(results))
