import asyncio
import logging
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import uuid4

import httpx

from tg_bot.models import (
    PRIORITY_NAMES,
    Category,
    CategoryList,
    Issue,
    IssueCreate,
    IssueList,
)

logger = logging.getLogger(__name__)


class GatewayError(RuntimeError):
    """The 1C service could not complete an operation."""


class IssueGateway(Protocol):
    async def get_categories(self) -> Sequence[Category]: ...

    async def create_issue(self, payload: IssueCreate) -> Issue: ...

    async def list_issues(self, telegram_user_id: int, limit: int = 10) -> Sequence[Issue]: ...

    async def get_issue(self, issue_id: str, telegram_user_id: int) -> Issue: ...

    async def cancel_issue(self, issue_id: str, telegram_user_id: int) -> Issue: ...

    async def close(self) -> None: ...


class OneCGateway:
    def __init__(self, base_url: str, api_token: str, timeout: float = 10) -> None:
        headers = {"Accept": "application/json"}
        if api_token:
            # 1C intercepts the standard Bearer header and treats its value as
            # a platform authentication token before the HTTP service runs.
            headers["X-API-Key"] = api_token
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            headers=headers,
            timeout=timeout,
        )

    async def _request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        try:
            response = await self._client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as error:
            response = error.response
            try:
                body = response.json()
                detail = (
                    body.get("error", response.text) if isinstance(body, dict) else response.text
                )
            except ValueError:
                detail = response.text
            detail = detail.strip() or f"HTTP {response.status_code}"
            logger.error("1C API returned HTTP %s: %s", response.status_code, detail)
            raise GatewayError(detail) from error
        except httpx.HTTPError as error:
            logger.error("1C API request failed: %s", error)
            raise GatewayError("Сервис 1С временно недоступен") from error

    async def get_categories(self) -> Sequence[Category]:
        response = await self._request("GET", "categories")
        return CategoryList.model_validate(response.json()).items

    async def create_issue(self, payload: IssueCreate) -> Issue:
        response = await self._request("POST", "issues", json=payload.model_dump(mode="json"))
        return Issue.model_validate(response.json())

    async def list_issues(self, telegram_user_id: int, limit: int = 10) -> Sequence[Issue]:
        response = await self._request(
            "GET",
            "issues",
            params={"telegram_user_id": telegram_user_id, "limit": limit},
        )
        return IssueList.model_validate(response.json()).items

    async def get_issue(self, issue_id: str, telegram_user_id: int) -> Issue:
        response = await self._request(
            "GET", f"issues/{issue_id}", params={"telegram_user_id": telegram_user_id}
        )
        return Issue.model_validate(response.json())

    async def cancel_issue(self, issue_id: str, telegram_user_id: int) -> Issue:
        response = await self._request(
            "POST", f"issues/{issue_id}/cancel", json={"telegram_user_id": telegram_user_id}
        )
        return Issue.model_validate(response.json())

    async def close(self) -> None:
        await self._client.aclose()


class MockGateway:
    def __init__(self) -> None:
        self._categories = [
            Category(id="technical", name="Техническая проблема"),
            Category(id="access", name="Доступ и учётные записи"),
            Category(id="software", name="Установка программ"),
            Category(id="other", name="Другое"),
        ]
        self._issues: dict[str, tuple[int, Issue]] = {}
        self._lock = asyncio.Lock()

    async def get_categories(self) -> Sequence[Category]:
        return self._categories.copy()

    async def create_issue(self, payload: IssueCreate) -> Issue:
        async with self._lock:
            issue_id = str(uuid4())
            category = next(
                (item for item in self._categories if item.id == payload.category_id), None
            )
            if category is None:
                raise GatewayError("Выбранная категория больше не существует")
            issue = Issue(
                id=issue_id,
                number=f"{len(self._issues) + 1:09d}",
                category_name=category.name,
                subject=payload.subject,
                description=payload.description,
                priority=payload.priority,
                priority_name=PRIORITY_NAMES[payload.priority],
                status="new",
                status_name="Новая",
                created_at=datetime.now().astimezone(),
            )
            self._issues[issue_id] = (payload.telegram_user_id, issue)
            return issue

    async def list_issues(self, telegram_user_id: int, limit: int = 10) -> Sequence[Issue]:
        items = [issue for owner, issue in self._issues.values() if owner == telegram_user_id]
        return list(reversed(items[-limit:]))

    async def get_issue(self, issue_id: str, telegram_user_id: int) -> Issue:
        stored = self._issues.get(issue_id)
        if stored is None or stored[0] != telegram_user_id:
            raise GatewayError("Заявка не найдена")
        return stored[1]

    async def cancel_issue(self, issue_id: str, telegram_user_id: int) -> Issue:
        issue = await self.get_issue(issue_id, telegram_user_id)
        if issue.status != "new":
            raise GatewayError("Можно отменить только новую заявку")
        updated = issue.model_copy(update={"status": "cancelled", "status_name": "Отменена"})
        self._issues[issue_id] = (telegram_user_id, updated)
        return updated

    async def close(self) -> None:
        return None
