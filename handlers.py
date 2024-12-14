import requests
import os
from aiogram import F, Router
from dotenv import load_dotenv
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, Location

load_dotenv()


API_TOKEN = os.getenv("API_TOKEN")

router = Router()

keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🏙️Выбрать город")],
    [KeyboardButton(
        text="📍Отправить геолокацию", request_location=True)]
], resize_keyboard=True)


@router.message(CommandStart())
async def start_bot(message: Message):
    first_name = message.from_user.first_name if message.from_user.first_name is not None else ""
    last_name = message.from_user.last_name if message.from_user.last_name is not None else ""
    await message.answer(f"Привет {first_name} {last_name}. Я бот, который может определить погоду в твоем городе. Для начала работы выбери пункт меню: ", reply_markup=keyboard)


@router.message(F.text == "🏙️Выбрать город")
async def ask_city(message: Message):
    await message.answer("Введите название города")


@router.message(F.text == "📍Отправить геолокацию")
async def ask_city(message: Message):
    await message.answer("Отправьте свою геолокацию")


@router.message(F.text)
async def find_city_weather(message: Message):
    try:
        city = message.text.strip()
        response = requests.get(f"http://api.openweathermap.org/data/2.5/weather?q={
                                city}&lang=ru&units=metric&appid={API_TOKEN}")
        data = response.json()
        await message.reply(f"В городе {city} погода: {str(data["main"]["temp"])} по цельсию")
    except:
        await message.reply("Возможно вы ввели не тот город, попробуйте еще раз")


@router.message(F.location)
async def find_city(message: Message):
    try:
        lat = message.location.latitude
        lon = message.location.longitude
        response = requests.get(
            f'http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&lang=ru&units=metric&appid={API_TOKEN}')
        data = response.json()
        await message.reply(f" погода: {str(data["main"]["temp"])} по цельсию")
    except:
        await message.reply("Не получается определить ваше местоположение")
