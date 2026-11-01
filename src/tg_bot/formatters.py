from html import escape

from tg_bot.models import Issue


def issue_card(issue: Issue) -> str:
    created = issue.created_at.astimezone().strftime("%d.%m.%Y %H:%M")
    parts = [
        f"<b>Заявка №{escape(issue.number)}</b>",
        f"Статус: <b>{escape(issue.status_name)}</b>",
        f"Категория: {escape(issue.category_name)}",
        f"Приоритет: {escape(issue.priority_name)}",
        f"Тема: {escape(issue.subject)}",
    ]
    if issue.description:
        parts.append(f"Описание: {escape(issue.description)}")
    parts.append(f"Создана: {created}")
    return "\n".join(parts)
