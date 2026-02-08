from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


auth_type_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Вход по номеру зачётки", callback_data="gbook_auth"),
            InlineKeyboardButton(text="Вход по E-mail", callback_data="email_auth"),
        ],
    ]
)

retry_gbook_auth_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Попробовать снова", callback_data="gbook_auth"),
        ],
    ]
)

retry_email_auth_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Попробовать снова", callback_data="email_auth"),
        ],
    ]
)