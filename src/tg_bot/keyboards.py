from collections.abc import Sequence

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from tg_bot.models import PRIORITY_NAMES, Category, Issue, Priority


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Создать заявку")],
            [KeyboardButton(text="📋 Мои заявки")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def cancel_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить создание")]],
        resize_keyboard=True,
    )


def category_keyboard(categories: Sequence[Category]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=item.name, callback_data=f"category:{item.id}")]
        for item in categories
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def priority_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=name, callback_data=f"priority:{priority.value}")
        for priority, name in PRIORITY_NAMES.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Зарегистрировать", callback_data="issue:confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="issue:abort"),
            ]
        ]
    )


def issues_keyboard(issues: Sequence[Issue]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"№{issue.number} · {issue.status_name}",
                callback_data=f"issue:view:{issue.id}",
            )
        ]
        for issue in issues
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def issue_actions_keyboard(issue: Issue) -> InlineKeyboardMarkup | None:
    if issue.status != "new":
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отменить заявку", callback_data=f"issue:cancel:{issue.id}")]
        ]
    )


def priority_from_callback(value: str) -> Priority | None:
    try:
        return Priority(value)
    except ValueError:
        return None
