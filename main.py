from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import logging
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("🤖 NovaGPTtrade работает в облаке! Всё 24/7 💡")

@dp.message_handler(commands=['сигнал'])
async def signal(message: types.Message):
    await message.answer("📡 Сигнал: BUY PYTH/USDT\nTP1: 0.3550 | TP2: 0.3740 | SL: 0.3150")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
