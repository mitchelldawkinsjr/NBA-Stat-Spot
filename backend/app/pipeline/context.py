"""Pipeline execution context."""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, Iterator, Optional

from sqlalchemy.orm import Session

from ..database import SessionLocal


@dataclass
class PipelineContext:
    job_name: str
    target_date: Optional[date] = None
    season: Optional[str] = None
    dry_run: bool = False
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    run_id: Optional[int] = None
    stats: Dict[str, Any] = field(default_factory=dict)


@contextmanager
def pipeline_session() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
