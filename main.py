import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from handlers import router
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")  # add your token

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def main() -> None:
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
