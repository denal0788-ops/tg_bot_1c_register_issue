from aiogram.fsm.state import State, StatesGroup


class CreateIssue(StatesGroup):
    category = State()
    subject = State()
    description = State()
    priority = State()
    confirmation = State()
