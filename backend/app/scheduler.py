import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session

from app.db.session import engine
from app.services.recurring_expense_service import materialize_all

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone="UTC")


def _run_recurring_expenses_job() -> None:
    today = date.today()
    logger.info("Running recurring expenses job for %s-%02d", today.year, today.month)
    with Session(engine) as session:
        created = materialize_all(session, today.year, today.month)
    logger.info("Recurring expenses job created %d expense(s)", created)


def start_scheduler() -> None:
    _scheduler.add_job(
        _run_recurring_expenses_job,
        CronTrigger(day=1, hour=2, minute=0, timezone="UTC"),
        id="recurring_expenses_monthly",
        replace_existing=True,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("APScheduler started — recurring expenses job scheduled for day=1 02:00 UTC")


def stop_scheduler() -> None:
    _scheduler.shutdown(wait=False)
    logger.info("APScheduler stopped")
