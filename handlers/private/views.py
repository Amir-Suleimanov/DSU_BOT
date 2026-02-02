from aiogram import F, Bot, types
from datetime import time
from aiogram.types import CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from FSM import AuthGBookState, AuthEmailState
from keyboards import reply
from database import requests as rq
from handlers.private import router
from parser.auth import student_authentication, InvalidDataError
from parser.core import SiteUnavailableError


@router.message(CommandStart())
async def start(message: types.Message, state: FSMContext = None):
    await state.clear()
    
    if await rq.check_user_registration(message.from_user.id):
        # TODO перевод в главное меню
        await message.answer("Вы уже зарегистрированы в системе.")
        return

    await message.answer(
        f"Добро пожаловать! {message.from_user.full_name}."
        "\nЭто бот для просмотра успеваемости студентов ДГУ."
        "\nВыбирите способ аутентификации:",
        reply_markup=reply.auth_type_keyboard
    )