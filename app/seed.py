"""Insert Persian demo data.

Run it with ``make seed``. The script refuses to touch a database that
already holds tasks, unless it is called with ``--force``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session_factory
from app.models.task import Task
from app.services import learning as learning_service
from app.services import reviews as review_service
from app.services import tasks as task_service
from app.services import time_entries as time_service
from app.utils.time import utcnow

DEMO_DOMAINS = (
    "پروژهٔ اصلی",
    "یادگیری",
    "خانه",
    "سلامتی",
)

DEMO_TASKS = (
    ("نوشتن گزارش ماهانه", "work", "company", 1),
    ("بازبینی کدهای هسته", "work", "company", 2),
    ("آماده‌سازی جلسهٔ هفتگی", "work", "company", 0),
    ("پاسخ به ایمیل‌های باز", "work", "company", 3),
    ("مطالعهٔ فصل سوم کتاب", "study", "learning", 2),
    ("تمرین ورزشی", "work", "personal", 3),
    ("خرید خانه", "work", "personal", 3),
    ("مرتب کردن دفتر کار", "work", "personal", 2),
    ("طراحی صفحهٔ تنظیمات", "work", "company", 1),
    ("رفع اشکال گزارش‌گیری", "work", "company", 0),
)

DEMO_LEARNING = (
    ("توسعهٔ وب با FastAPI", "book", "فصل اول: آشنایی", "فصل دوم: مسیرها", "فصل سوم: وابستگی‌ها"),
    ("مبانی طراحی داده", "course", "کارگاه اول", "کارگاه دوم"),
    ("مقالهٔ معماری مدرن", "article", "مقدمه", "بدنه", "جمع‌بندی"),
)

# The marks that tell the demo rows from the rows of the user: the seed may
# run again at any time, and it must only ever remove what it wrote itself.
DEMO_TASK_MARK = "یادداشت نمونه"
DEMO_ENTRY_NOTE = "ثبت نمونه"
DEMO_LEARNING_NOTE = "مورد نمونه."
DEMO_REVIEW_TEXT = "این یک ارزیابی نمونه است."
DEMO_JOURNAL_TEXTS = (
    "امروز روی گزارش ماهانه کار کردم و در پایان یک نسخهٔ اولیه آماده شد.",
    "جلسهٔ هفتگی برگزار شد؛ سه تصمیم گرفته شد و یک تسک جدید ساخته شد.",
    "کمی کتاب خواندم و دو فصل را جلو رفتم.",
)


def _seed_tasks(session: Session, now: dt.datetime) -> None:
    """Create the demo domains and tasks."""
    domains = []
    for name in DEMO_DOMAINS:
        existing = task_service.find_domain_by_name(session, name)
        domains.append(existing or task_service.create_domain(session, name))

    for index, (title, _context, task_context, priority) in enumerate(DEMO_TASKS):
        created_at = now - dt.timedelta(days=index + 1)
        task = task_service.create_task(
            session,
            title=title,
            now=created_at,
            description_md=f"یادداشت نمونه برای «{title}».",
            context=task_context,
            priority=priority,
            effort_minutes_estimate=45 + index * 15,
        )
        task_service.set_task_domains(session, task, [domains[index % len(domains)].id], now)
        if index % 3 == 0:
            # A task that is done is done a few hours after it was opened:
            # the elapsed time of the demo stays a working one.
            task_service.set_status(
                session, task, "done", created_at + dt.timedelta(hours=3, minutes=20 * index)
            )


def _seed_time_entries(session: Session, now: dt.datetime) -> None:
    """Create the demo time entries of the last three weeks."""
    policy = time_service.policy_from_settings(session)
    random.seed(1403)
    for day_offset in range(21):
        day = now - dt.timedelta(days=day_offset)
        if day.weekday() == 4:  # Friday
            continue
        for _ in range(random.randint(1, 3)):
            hour = random.randint(9, 16)
            started_at = day.replace(hour=hour, minute=random.choice([0, 15, 30]))
            minutes = random.choice([45, 60, 90, 120])
            time_service.create_entry(
                session,
                kind=random.choice(["work", "work", "study"]),
                started_at=started_at,
                now=started_at + dt.timedelta(minutes=minutes),
                ended_at=started_at + dt.timedelta(minutes=minutes),
                duration_minutes=minutes,
                note=DEMO_ENTRY_NOTE,
                policy=policy,
            )
        if day_offset % 7 == 3:
            # A little overtime, with a reason, so the split has something to show.
            overtime_start = day.replace(hour=19, minute=0)
            time_service.create_entry(
                session,
                kind="overtime",
                started_at=overtime_start,
                now=overtime_start + dt.timedelta(minutes=90),
                ended_at=overtime_start + dt.timedelta(minutes=90),
                duration_minutes=90,
                reason="کار فوری",
                note=DEMO_ENTRY_NOTE,
                policy=policy,
            )


def _seed_journal(session: Session, now: dt.datetime) -> None:
    """Create the demo journal entries."""
    from app.models.timing import DailyJournal

    texts = DEMO_JOURNAL_TEXTS
    for offset, text in enumerate(texts):
        day = now.date() - dt.timedelta(days=offset)
        if session.scalars(select(DailyJournal).where(DailyJournal.date == day)).first():
            continue
        session.add(
            DailyJournal(
                date=day,
                raw_text=text,
                parsed={"entries": [{"text": text, "minutes": 60, "kind": "work"}]},
                confirmed=True,
            )
        )
    session.flush()


def _seed_learning(session: Session, now: dt.datetime) -> None:
    """Create the demo learning items with their units."""
    for title, kind, *units in DEMO_LEARNING:
        item = learning_service.create_item(
            session, title=title, kind=kind, now=now, notes_md="مورد نمونه."
        )
        learning_service.set_units(session, item, units)
        learning_service.set_status(session, item, "in_progress", now)
        learning_service.log_activity(session, item, now=now, minutes=30)


def _seed_review(session: Session, now: dt.datetime) -> None:
    """Create a demo review of the current month."""
    period = review_service.resolve_period(session, "month", now.date())
    stats = review_service.compute_stats(
        session, start=period.start, end=period.end, timezone="Asia/Tehran"
    )
    review_service.create_review(
        session,
        period=period,
        stats=stats,
        user_final_md="این یک ارزیابی نمونه است.",
        rating=4,
    )


def _clear_demo_data(session: Session, now: dt.datetime) -> None:
    """Remove the demo rows, and only those.

    The seed may run again at any time. Without this, every run would pile
    its demo rows on top of the ones of the previous run and the reports
    would count the same work over and over again. The rows of the user are
    never touched: only the ones the seed itself wrote are removed.
    """
    from app.models.learning import LearningItem
    from app.models.review import Review
    from app.models.timing import DailyJournal, TimeEntry

    demo_tasks = session.scalars(
        select(Task).where(Task.description_md.like(f"{DEMO_TASK_MARK}%"))
    ).all()
    for task in demo_tasks:
        task_service.soft_delete(session, task, now)
    session.flush()

    demo_entries = session.scalars(
        select(TimeEntry).where(TimeEntry.note == DEMO_ENTRY_NOTE)
    ).all()
    for entry in demo_entries:
        session.delete(entry)
    session.flush()

    demo_journals = session.scalars(
        select(DailyJournal).where(DailyJournal.raw_text.in_(DEMO_JOURNAL_TEXTS))
    ).all()
    for journal in demo_journals:
        session.delete(journal)
    session.flush()

    demo_items = session.scalars(
        select(LearningItem).where(LearningItem.notes_md == DEMO_LEARNING_NOTE)
    ).all()
    for item in demo_items:
        session.delete(item)
    session.flush()

    demo_reviews = session.scalars(
        select(Review).where(Review.user_final_md == DEMO_REVIEW_TEXT)
    ).all()
    for review in demo_reviews:
        session.delete(review)
    session.flush()


def seed(force: bool = False) -> int:
    """Insert the demo data; returns the number of tasks created."""
    session = get_session_factory()()
    try:
        existing = session.scalars(select(Task).limit(1)).first()
        if existing is not None and not force:
            print("the database already holds tasks; nothing was seeded (use --force)")
            return 0
        now = utcnow()
        if force:
            _clear_demo_data(session, now)
        _seed_tasks(session, now)
        _seed_time_entries(session, now)
        _seed_journal(session, now)
        _seed_learning(session, now)
        _seed_review(session, now)
        session.commit()
        count = len(
            session.scalars(select(Task).where(Task.deleted_at.is_(None))).all()
        )
        print(f"seeded {count} demo tasks")
        return count
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    """Entry point of ``python -m app.seed``."""
    parser = argparse.ArgumentParser(description="Insert Persian demo data.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="seed even when the database already holds tasks",
    )
    args = parser.parse_args()
    seed(force=args.force)


if __name__ == "__main__":
    main()
