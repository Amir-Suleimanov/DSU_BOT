from aiogram import Router

from filters.chat_types import ChatTypeFilter

router = Router()
router.message.filter(ChatTypeFilter(chat_types=["private"]))

from . import views
from . import auth