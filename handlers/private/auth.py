from aiogram import F, Bot, types
from datetime import time
from aiogram.types import CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from FSM import AuthGBookState, AuthEmailState
from handlers.helpers import email_auth_warning
from database import requests as rq
from database.models import Status
from keyboards import reply
from handlers.private import router
from parser.auth import student_authentication, InvalidDataError
from database.models import Auth
from parser.core import SiteUnavailableError


@router.callback_query(F.data == "gbook_auth")
async def gbook_auth(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Начало аутентификации по номеру зачётки."""
    await state.clear()
    if await rq.check_user_registration(callback.from_user.id):
        # TODO перевод в главное меню
        await callback.message.answer("Вы уже зарегистрированы в системе.")
        return
    await state.set_state(AuthGBookState.data)
    await callback.answer() # Очистка загрузки кнопки
    await callback.message.answer(
        "Отправьте свои данные для входа в систему по формату ниже:\n\n"
        "Фамилия Имя Отчество Номер_зачетки\n\n"
        "Пример: Магомедов Магомед Магомедович 10026"
    )


@router.message(AuthGBookState.data)
async def auth(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()

    data = message.text.split()
    if len(data) != 4:
        await state.set_state(AuthGBookState.data)
        await message.answer("Неверный формат данных. Пожалуйста, введите данные по формату:\n\n"
                             "Фамилия Имя Отчество Номер_зачетки\n\n"
                             "Пример: Магомедов Магомед Магомедович 10026")
        return

    surname, name, patronymic, gradebook_number = data
    try:
        profile_data = await student_authentication(
            auth_type=Auth.GBook(),
            auth_data=[surname, name, patronymic, gradebook_number],
            is_student_data=True,
        )
    except InvalidDataError as err:
        msg = str(err) or "Неверные данные или вход заблокирован. Проверьте ФИО и номер зачётки."
        if "e-mail" in msg.lower() or "email" in msg.lower():
            await email_auth_warning(message, state)
            return
        await message.answer(msg, reply_markup=reply.retry_gbook_auth_keyboard)
        return
    except SiteUnavailableError:
        await message.answer(
            "Сайт временно недоступен. Попробуйте снова через пару минут.",
            reply_markup=reply.retry_gbook_auth_keyboard
        )
        # TODO отправка уведомления админу
        return

    if not profile_data and await rq.check_user_registration(message.from_user.id):
        await message.answer("Не удалось войти в аккаунт. Проверьте данные и попробуйте снова.", reply_markup=reply.retry_gbook_auth_keyboard)
        return

    created = await rq.create_student_user(
        user_id=message.from_user.id,
        role_id=1,
        status_id=Status.status_by_str(profile_data["status"]),
        daily_limit=3,
        name=profile_data["name"],
        surname=profile_data["surname"],
        patronymic=profile_data["patronymic"],
        gradebook_number=profile_data["gradebook_number"],
        branch=profile_data["branch"],
        faculty=profile_data["faculty"],
        study_program=profile_data["study_program"],
        current_semester=profile_data["current_semester"],
        schedule_send_time=time(8, 0),
    )

    if not created:
        await message.answer("Вы уже зарегистрированы. Данные аккаунта уже есть в системе.")
        return

    await message.answer(
        "Вот ваши данные:\n"
        f"Филиал: {profile_data['branch']}\n"
        f"Факультет: {profile_data['faculty']}\n"
        f"Учебная программа: {profile_data['study_program']}\n"
        f"Текущий семестр: {profile_data['current_semester']}"
    )


@router.callback_query(F.data == "email_auth")
async def email_auth(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    if await rq.check_user_registration(callback.from_user.id):
        # TODO перевод в главное меню
        await callback.message.answer("Вы уже зарегистрированы в системе.")
        return

    await state.set_state(AuthEmailState.data)
    await callback.answer()
    await callback.message.answer(
        "Отправьте данные для входа через E-mail в формате:\n\n"
        "Email Пароль\n\n"
        "Пример: ivanov@mail.ru qwerty123"
    )


@router.message(AuthEmailState.data)
async def auth_email_password(message: types.Message, state: FSMContext):
    creds = message.text.split()
    if len(creds) != 2:
        await message.answer(
            "Неверный формат. Отправьте данные в формате:\n\n"
            "Email Пароль\n\n"
            "Пример: ivanov@mail.ru qwerty123"
        )
        return
    email, password = creds

    try:
        profile_data = await student_authentication(
            auth_type=Auth.Email(),
            auth_data=[email, password],
            is_student_data=True,
        )
    except InvalidDataError as err:
        msg = str(err) or "Неверные данные для входа через E-mail."
        await message.answer(msg)
        return
    except SiteUnavailableError:
        await message.answer(
            "Сайт временно недоступен. Попробуйте снова через пару минут."
        )
        return

    if not profile_data and await rq.check_user_registration(message.from_user.id):
        await message.answer("Не удалось войти в аккаунт. Проверьте данные и попробуйте снова.")
        return

    created = await rq.create_student_user(
        user_id=message.from_user.id,
        role_id=1,
        status_id=Status.status_by_str(profile_data["status"]),
        daily_limit=3,
        name=profile_data["name"],
        surname=profile_data["surname"],
        patronymic=profile_data["patronymic"],
        gradebook_number=profile_data["gradebook_number"],
        branch=profile_data["branch"],
        faculty=profile_data["faculty"],
        study_program=profile_data["study_program"],
        current_semester=profile_data["current_semester"],
        schedule_send_time=time(8, 0),
    )

    await state.clear()

    if not created:
        await message.answer("Вы уже зарегистрированы. Данные аккаунта уже есть в системе.")
        return

    await message.answer(
        "Вот ваши данные:\n"
        f"Филиал: {profile_data['branch']}\n"
        f"Факультет: {profile_data['faculty']}\n"
        f"Учебная программа: {profile_data['study_program']}\n"
        f"Текущий семестр: {profile_data['current_semester']}"
    )
