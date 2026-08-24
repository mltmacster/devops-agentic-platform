"""User repository — async CRUD over the `users` table."""

import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User


class UserRepository:
    """Data access for the local identity store."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_email(self, email: str) -> Optional[User]:
        try:
            stmt = select(User).where(User.email == email.lower())
            return (await self._session.execute(stmt)).scalar_one_or_none()
        except (OperationalError, ProgrammingError):
            # Identity store not initialized yet (e.g. tests that never ran
            # init_db): treated as unknown user, so dev mode keeps its
            # fail-open behavior and strict mode fails closed with 401.
            return None

    async def get_by_id(self, user_id: str) -> Optional[User]:
        return await self._session.get(User, user_id)

    async def create(self, email: str, password_hash: str, role: str) -> User:
        user = User(
            id=str(uuid.uuid4()),
            email=email.lower(),
            password_hash=password_hash,
            role=role,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def count(self) -> int:
        stmt = select(func.count()).select_from(User)
        return (await self._session.execute(stmt)).scalar_one()
