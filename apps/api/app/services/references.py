"""Yearly document numbers. The counter update locks the series row."""

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.security import utcnow
from app.models.workflow import DocumentCounter


def next_reference(db: Session, series: str, prefix: str) -> str:
    year = utcnow().year
    statement = (
        pg_insert(DocumentCounter)
        .values(series=series, year=year, last_value=1)
        .on_conflict_do_update(
            index_elements=[DocumentCounter.series, DocumentCounter.year],
            set_={"last_value": DocumentCounter.last_value + 1},
        )
        .returning(DocumentCounter.last_value)
    )
    value = int(db.execute(statement).scalar_one())
    return f"{prefix}-{year}-{value:06d}"
