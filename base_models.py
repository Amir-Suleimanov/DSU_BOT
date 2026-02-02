import asyncio
from typing import Type, TypeVar

from sqlalchemy.exc import IntegrityError

from database.engine import session_maker
from database import models

T = TypeVar("T")


async def create_object(model_cls: Type[T], **fields) -> T:
    """
    Универсальный helper для создания объекта любой модели.
    Пример: await create_object(models.Role, id=1, name="admin", description="Администратор")
    """
    async with session_maker() as session:
        obj = model_cls(**fields)
        session.add(obj)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise
        await session.refresh(obj)
        return obj


async def create_user_with_profile(
    user_id: int,
    role_id: int,
    name: str,
    surname: str = "",
    patronymic: str = "",
):
    """
    Пример составного создания связанных сущностей.
    """
    async with session_maker() as session:
        profile = models.Profile(
            id=user_id,
            name=name,
            surname=surname,
            patronymic=patronymic,
        )
        user = models.User(id=user_id, profile_id=user_id, role_id=role_id)
        session.add_all([profile, user])
        await session.commit()
        return user


async def create_default_roles_and_statuses() -> None:
    """
    Базовое наполнение: роли Student/Admin/Teacher и статусы Active/Graduated/Expelled.
    """
    async with session_maker() as session:
        roles = [
            models.Role(id=1, name="Student", description="Студент"),
            models.Role(id=2, name="Admin", description="Администратор"),
            models.Role(id=3, name="Teacher", description="Преподаватель"),
        ]
        statuses = [
            models.Status(id=1, name="Active", description="Активный"),
            models.Status(id=2, name="Graduated", description="Выпускник"),
            models.Status(id=3, name="Expelled", description="Отчислен"),
        ]
        session.add_all(roles + statuses)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise


if __name__ == "__main__":
    async def _demo():
        await create_default_roles_and_statuses()

    asyncio.run(_demo())
