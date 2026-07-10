from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]


def get_role(x_role: Annotated[str | None, Header()] = None) -> str:
    return x_role or "admin"
