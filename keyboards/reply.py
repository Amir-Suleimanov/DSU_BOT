from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


auth_type_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Вход по номеру зачётки", callback_data="gbook_auth"),
            InlineKeyboardButton(text="Вход по E-mail", callback_data="email_auth"),
        ],
    ]
)