import asyncio
import logging
import sys

from database import create_table
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from handlers import router
from settings import settings
from additional_classes import setup_logger
bot_token = settings.bot_token
bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


async def main() -> None:
    dp.include_router(router)
    await create_table()
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        setup_logger()
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Program interrupted by KeyboardInterrupt")
