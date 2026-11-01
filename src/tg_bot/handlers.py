import logging
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from pydantic import ValidationError

from tg_bot.formatters import issue_card
from tg_bot.gateway import GatewayError, IssueGateway
from tg_bot.keyboards import (
    cancel_menu,
    category_keyboard,
    confirmation_keyboard,
    issue_actions_keyboard,
    issues_keyboard,
    main_menu,
    priority_from_callback,
    priority_keyboard,
)
from tg_bot.models import PRIORITY_NAMES, IssueCreate
from tg_bot.states import CreateIssue

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    name = escape(message.from_user.full_name) if message.from_user else "пользователь"
    await message.answer(
        f"Здравствуйте, <b>{name}</b>!\nЯ помогу зарегистрировать заявку и проверить её статус.",
        reply_markup=main_menu(),
    )


@router.message(Command("cancel"))
@router.message(F.text == "❌ Отменить создание")
async def abort_creation(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Создание заявки отменено.", reply_markup=main_menu())


@router.message(F.text == "📝 Создать заявку")
async def begin_creation(message: Message, state: FSMContext, gateway: IssueGateway) -> None:
    await state.clear()
    try:
        categories = await gateway.get_categories()
    except GatewayError as error:
        await message.answer(str(error), reply_markup=main_menu())
        return
    await state.set_state(CreateIssue.category)
    await state.update_data(categories={item.id: item.name for item in categories})
    await message.answer("Выберите категорию заявки:", reply_markup=category_keyboard(categories))


@router.callback_query(CreateIssue.category, F.data.startswith("category:"))
async def choose_category(callback: CallbackQuery, state: FSMContext) -> None:
    category_id = callback.data.partition(":")[2] if callback.data else ""
    data = await state.get_data()
    category_name = data.get("categories", {}).get(category_id)
    if not category_name:
        await callback.answer("Категория устарела, начните заново", show_alert=True)
        return
    await state.update_data(category_id=category_id, category_name=category_name)
    await state.set_state(CreateIssue.subject)
    await callback.answer()
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "Кратко укажите тему заявки (от 3 до 120 символов):",
            reply_markup=cancel_menu(),
        )


@router.message(CreateIssue.subject, F.text)
async def receive_subject(message: Message, state: FSMContext) -> None:
    subject = (message.text or "").strip()
    if not 3 <= len(subject) <= 120:
        await message.answer("Тема должна содержать от 3 до 120 символов.")
        return
    await state.update_data(subject=subject)
    await state.set_state(CreateIssue.description)
    await message.answer("Подробно опишите проблему (от 5 до 2000 символов):")


@router.message(CreateIssue.description, F.text)
async def receive_description(message: Message, state: FSMContext) -> None:
    description = (message.text or "").strip()
    if not 5 <= len(description) <= 2000:
        await message.answer("Описание должно содержать от 5 до 2000 символов.")
        return
    await state.update_data(description=description)
    await state.set_state(CreateIssue.priority)
    await message.answer("Выберите приоритет:", reply_markup=priority_keyboard())


@router.callback_query(CreateIssue.priority, F.data.startswith("priority:"))
async def choose_priority(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.partition(":")[2] if callback.data else ""
    priority = priority_from_callback(value)
    if priority is None:
        await callback.answer("Неизвестный приоритет", show_alert=True)
        return
    await state.update_data(priority=priority.value, priority_name=PRIORITY_NAMES[priority])
    await state.set_state(CreateIssue.confirmation)
    data = await state.get_data()
    summary = (
        "<b>Проверьте заявку</b>\n"
        f"Категория: {escape(data['category_name'])}\n"
        f"Тема: {escape(data['subject'])}\n"
        f"Описание: {escape(data['description'])}\n"
        f"Приоритет: {escape(data['priority_name'])}"
    )
    await callback.answer()
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(summary, reply_markup=confirmation_keyboard())


@router.callback_query(CreateIssue.confirmation, F.data == "issue:abort")
async def abort_by_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("Создание заявки отменено.", reply_markup=main_menu())


@router.callback_query(CreateIssue.confirmation, F.data == "issue:confirm")
async def confirm_issue(callback: CallbackQuery, state: FSMContext, gateway: IssueGateway) -> None:
    user = callback.from_user
    data = await state.get_data()
    try:
        payload = IssueCreate(
            telegram_user_id=user.id,
            telegram_username=user.username,
            telegram_full_name=user.full_name,
            category_id=data["category_id"],
            subject=data["subject"],
            description=data["description"],
            priority=data["priority"],
        )
        issue = await gateway.create_issue(payload)
    except (GatewayError, ValidationError, KeyError) as error:
        logger.warning("Issue creation failed: %s", error)
        await callback.answer("Не удалось зарегистрировать заявку", show_alert=True)
        return
    await state.clear()
    await callback.answer()
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            f"✅ Заявка №{escape(issue.number)} зарегистрирована.\n"
            f"Текущий статус: <b>{escape(issue.status_name)}</b>",
            reply_markup=main_menu(),
        )


@router.message(F.text == "📋 Мои заявки")
async def list_my_issues(message: Message, gateway: IssueGateway) -> None:
    if not message.from_user:
        return
    try:
        issues = await gateway.list_issues(message.from_user.id)
    except GatewayError as error:
        await message.answer(str(error))
        return
    if not issues:
        await message.answer("У вас пока нет зарегистрированных заявок.")
        return
    await message.answer("Последние заявки:", reply_markup=issues_keyboard(issues))


@router.callback_query(F.data.startswith("issue:view:"))
async def view_issue(callback: CallbackQuery, gateway: IssueGateway) -> None:
    issue_id = callback.data.removeprefix("issue:view:") if callback.data else ""
    try:
        issue = await gateway.get_issue(issue_id, callback.from_user.id)
    except GatewayError as error:
        await callback.answer(str(error), show_alert=True)
        return
    await callback.answer()
    if callback.message:
        await callback.message.answer(issue_card(issue), reply_markup=issue_actions_keyboard(issue))


@router.callback_query(F.data.startswith("issue:cancel:"))
async def cancel_issue(callback: CallbackQuery, gateway: IssueGateway) -> None:
    issue_id = callback.data.removeprefix("issue:cancel:") if callback.data else ""
    try:
        issue = await gateway.cancel_issue(issue_id, callback.from_user.id)
    except GatewayError as error:
        await callback.answer(str(error), show_alert=True)
        return
    await callback.answer("Заявка отменена")
    if callback.message:
        await callback.message.edit_text(issue_card(issue), reply_markup=None)


@router.message()
async def fallback(message: Message) -> None:
    await message.answer("Используйте кнопки меню или команду /start.", reply_markup=main_menu())
