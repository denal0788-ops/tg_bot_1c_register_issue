import asyncio
import logging
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from tg_bot.config import Settings, get_settings
from tg_bot.gateway import IssueGateway, MockGateway, OneCGateway
from tg_bot.handlers import router


def build_gateway(settings: Settings) -> IssueGateway:
    if settings.bot_mode == "mock":
        return MockGateway()
    return OneCGateway(
        base_url=settings.onec_base_url,
        api_token=settings.onec_api_token.get_secret_value(),
        timeout=settings.onec_timeout_seconds,
    )


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    gateway = build_gateway(settings)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    try:
        await dispatcher.start_polling(bot, gateway=gateway)
    finally:
        with suppress(Exception):
            await gateway.close()
        await bot.session.close()


def run() -> None:
    asyncio.run(main())
