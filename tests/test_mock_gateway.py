import pytest

from tg_bot.gateway import GatewayError, MockGateway
from tg_bot.models import IssueCreate, Priority


def payload(user_id: int = 42) -> IssueCreate:
    return IssueCreate(
        telegram_user_id=user_id,
        telegram_username="student",
        telegram_full_name="Иван Иванов",
        category_id="technical",
        subject="Не открывается база",
        description="При запуске появляется сообщение об ошибке",
        priority=Priority.NORMAL,
    )


@pytest.mark.asyncio
async def test_create_list_and_cancel_issue() -> None:
    gateway = MockGateway()

    issue = await gateway.create_issue(payload())
    items = await gateway.list_issues(42)
    cancelled = await gateway.cancel_issue(issue.id, 42)

    assert issue.number == "000000001"
    assert [item.id for item in items] == [issue.id]
    assert cancelled.status == "cancelled"


@pytest.mark.asyncio
async def test_user_cannot_read_another_users_issue() -> None:
    gateway = MockGateway()
    issue = await gateway.create_issue(payload())

    with pytest.raises(GatewayError, match="не найдена"):
        await gateway.get_issue(issue.id, telegram_user_id=100500)
