import requests
import os
import json
from aiogram import F, Router
from dotenv import load_dotenv
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton


load_dotenv()


API_TOKEN = os.getenv("API_TOKEN")

router = Router()

keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🏙️Выбрать город")],
    [KeyboardButton(text="📍Отправить геолокацию", request_location=True)],
    [KeyboardButton(text="🌤️ Моя погода")]
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


@router.message(F.text == "🌤️ Моя погода")
async def find_my_weather(message: Message):
    data = load_user_data(message.from_user.id)
    if data:
        await message.answer(
            f"Найдена информация о вашем городе/районе: {data["city"]}"
            f"Температура: {data["temp"]} ℃\n"
            f"Ощущается как: {data["temp_feels"]} ℃\n"
            f"Давление: {data["pressure"]} гПа\n"
            f"Скорость ветра: {data["wind_speed"]} м/с"
        )
    else:
        await message.answer("Сохраненной информации о вашем городе/районе нет.")


@router.message(F.text)
async def find_city_weather(message: Message):
    try:
        user_id = message.from_user.id
        city = message.text.strip()
        response = requests.get(
            f"http://api.openweathermap.org/data/2.5/weather?q={city}&lang=ru&units=metric&appid={API_TOKEN}")
        data = response.json()
        temp = str(round(data['main']['temp']))
        temp_feels = str(round(data['main']['feels_like']))
        pressure = str(data['main']['pressure'])
        wind_speed = str(data['wind']['speed'])
        city = city[0].upper()+city[1:]
        data_to_save = {"user_id": user_id,
                        "city": city,
                        "temp": temp,
                        "temp_feels": temp_feels,
                        "pressure": pressure,
                        "wind_speed": wind_speed}
        save_weather_to_file(data_to_save)
        await message.reply(
            f"В городе/районе {city} погода такая:\n"
            f"Температура: {temp} ℃\n"
            f"Ощущается как: {temp_feels} ℃\n"
            f"Давление: {pressure} гПа\n"
            f"Скорость ветра: {wind_speed} м/с"
        )
    except:
        await message.reply("Возможно вы ввели не тот город, попробуйте еще раз")


@router.message(F.location)
async def find_city(message: Message):
    try:
        user_id = message.from_user.id
        lat = message.location.latitude
        lon = message.location.longitude
        response = requests.get(
            f'http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&lang=ru&units=metric&appid={API_TOKEN}')
        data = response.json()
        temp = str(round(data['main']['temp']))
        temp_feels = str(round(data['main']['feels_like']))
        pressure = str(data['main']['pressure'])
        wind_speed = str(data['wind']['speed'])
        city = data["sys"]["name"]
        data_to_save = {"user_id": user_id,
                        "city": city,
                        "temp": temp,
                        "temp_feels": temp_feels,
                        "pressure": pressure,
                        "wind_speed": wind_speed}
        save_weather_to_file(data_to_save)
        await message.reply(f" погода: {temp} по цельсию")
    except:
        await message.reply("Не получается определить ваше местоположение")


def save_weather_to_file(dict):
    file_name = "db.json"
    with open(file_name, "r", encoding="utf-8") as file:
        try:
            all_data = json.load(file)
        except json.JSONDecodeError:
            all_data = []
    user_id = dict["user_id"]
    for entry in all_data:
        if entry["user_id"] == user_id:
            entry.update(dict)
            break
    else:
        all_data.append(dict)
    with open(file_name, "w", encoding="utf-8") as file:
        json.dump(all_data, file, ensure_ascii=False, indent=4)


def load_user_data(user_id):
    file_name = "db.json"
    with open(file_name, "r", encoding="utf-8") as file:
        all_data = json.load(file)
        for entry in all_data:
            if entry["user_id"] == user_id:
                return entry
    return None
