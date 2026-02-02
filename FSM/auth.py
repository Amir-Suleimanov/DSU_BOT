from aiogram.fsm.state import State, StatesGroup

class AuthGBookState(StatesGroup):
    data = State()


class AuthEmailState(StatesGroup):
    data = State()