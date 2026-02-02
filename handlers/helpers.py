from aiogram import F, Bot, types
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from FSM.auth import AuthEmailState

async def email_auth_warning(msg: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(AuthEmailState.data)
    await msg.answer(
        "Для вашего аккаунта требуется вход через E-mail.\n"
        "Отправьте данные в формате:\n"
        "Email Пароль\n\n"
        "Пример: ivanov@mail.ru qwerty123"
    )
    return
    