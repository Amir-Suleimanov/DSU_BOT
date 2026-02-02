from database.engine import session_maker
from database.models import User, Profile, StudentDetails
from sqlalchemy import select


async def create_student_user(
    user_id: int,
    role_id: int,
    name: str,
    surname: str,
    patronymic: str,
    gradebook_number: int,
    status_id: int,
    daily_limit: int,
    branch: str,
    faculty: str,
    study_program: str,
    current_semester: int,
    schedule_send_time,
) -> bool:
    """
    Создать нового пользователя-студента, если он не существует.
    Возвращает True если создан, False если уже был.
    """
    
    async with session_maker() as session:
        if await session.scalar(select(User).where(User.id == user_id)):
            return False

        profile = Profile(id=user_id, name=name, surname=surname, patronymic=patronymic)
        user = User(id=user_id, role_id=role_id, profile=profile)
        session.add(user)
        session.add(
            StudentDetails(
                user=user,
                gradebook_number=gradebook_number,
                status_id=status_id,
                daily_limit=daily_limit,
                branch=branch,
                faculty=faculty,
                study_program=study_program,
                current_semester=current_semester,
                schedule_send_time=schedule_send_time,
            )
        )
        await session.commit()
        return True

async def check_user_registration(user_id: int) -> bool:
    """
    Проверить, зарегистрирован ли пользователь в системе.
    Возвращает True если зарегистрирован, False если нет.
    """
    async with session_maker() as session:
        user = await session.scalar(select(User).where(User.id == user_id))
        return user is not None