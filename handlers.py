import requests
import os
import json
import pandas as pd
import logging
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import shapiro, pearsonr
from aiogram import F, Router
from dotenv import load_dotenv
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile

load_dotenv()


API_TOKEN = os.getenv("API_TOKEN")

router = Router()

data = pd.read_csv("weather_data.csv")
data['date'] = pd.to_datetime(data['date'])
is_awaiting_city = False

keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🏙️Выбрать город")],
    [KeyboardButton(text="📍Отправить геолокацию", request_location=True)],
    [KeyboardButton(text="🌤️ Моя погода")]
], resize_keyboard=True)


@router.message(Command(commands=["help"]))
async def help_command(message: Message):
    await message.answer(
        "Доступные команды:\n"
        "/start - Запуск бота\n"
        "/info - Информация о боте\n"
        "/analyze - берем некий датасет и анализируем его\n"
        "Используйте кнопки для выбора функций.\n"
    )


@router.message(Command(commands=["info"]))
async def info_command(message: Message):
    await message.answer(
        "Я бот, который может показывать текущую погоду в выбранном городе(сохранять ваш выбор), а также у меня есть некий датасет, который я могу проанализировать"
        "Вы можете:\n"
        "1. Ввести название города для получения информации.\n"
        "2. Отправить свою геолокацию, чтобы я определил погоду в вашем районе.\n"
        "3. Посмотреть сохраненную погоду с помощью команды 🌤️ Моя погода.\n"
        "4. Изучить информацию о командах.\n"
    )


@router.message(CommandStart())
async def start_bot(message: Message):
    first_name = message.from_user.first_name if message.from_user.first_name is not None else ""
    last_name = message.from_user.last_name if message.from_user.last_name is not None else ""
    await message.answer(f"Привет {first_name} {last_name}. Я бот, который может определить погоду в твоем городе. Для начала работы выбери пункт меню.\nПодсказка: используйте команду /help, если не можете разобраться, как работать со мной. ", reply_markup=keyboard)

@router.message(Command("analyze"))
async def send_analysis(message: Message):
    plot_avg_temp_humidity()
    photo = FSInputFile("avg_temp_humidity.png")
    await message.answer_photo(photo, caption="Средняя температура и влажность для каждого города.")
    
    plot_wind_speed_distribution()
    photo = FSInputFile("wind_speed_distribution.png")
    await message.answer_photo(photo, caption="Распределение скорости ветра.")
    
    normality_result, p_value_normality = test_temperature_normality()
    await message.answer(f"Проверка гипотезы о нормальности распределения температуры:\n"
                         f"{normality_result}\nP-value: {p_value_normality:.4f}")
    
    correlation_result, correlation_value = calculate_correlation()
    await message.answer(f"Анализ корреляции между температурой и влажностью:\n"
                         f"{correlation_result}\nКоэффициент корреляции: {correlation_value:.2f}")

@router.message(F.text == "🏙️Выбрать город")
async def ask_city(message: Message):
    global is_awaiting_city
    is_awaiting_city = True
    await message.answer("Введите название города")


@router.message(F.text == "📍Отправить геолокацию")
async def ask_city(message: Message):
    global is_awaiting_city
    is_awaiting_city = False
    await message.answer("Отправьте свою геолокацию")


@router.message(F.text == "🌤️ Моя погода")
async def find_my_weather(message: Message):
    global is_awaiting_city
    is_awaiting_city = False
    data = load_user_data(message.from_user.id)
    if data:
        await message.answer(
            f"Найдена информация о вашем городе/районе: {data['city']}\n"
            f"Температура: {data['temp']} ℃\n"
            f"Ощущается как: {data['temp_feels']} ℃\n"
            f"Давление: {data['pressure']} гПа\n"
            f"Скорость ветра: {data['wind_speed']} м/с"
        )
    else:
        await message.answer("Сохраненной информации о вашем городе/районе нет.")


@router.message(F.text)
async def find_city_weather(message: Message):
    global is_awaiting_city
    if is_awaiting_city:
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
            city = city[0].upper() + city[1:]
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
        except Exception as e:
            logging.error(f"Ошибка при запросе погоды: {e}")
            await message.reply("Возможно вы ввели не тот город, попробуйте еще раз")
        finally:
            is_awaiting_city = False  # Сбрасываем флаг после обработки
    else:
        await message.reply("Если вы хотите ввести город, выберите пункт 🏙️Выбрать город.")


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
        city = data["name"]
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


def plot_avg_temp_humidity():
    avg_data = data.groupby(
        'city')[['temperature', 'humidity']].mean().reset_index()
    plt.figure(figsize=(10, 6))
    bar_width = 0.35
    x = range(len(avg_data['city']))

    plt.bar(x, avg_data['temperature'], width=bar_width,
            label='Avg Temperature (°C)', color='blue')
    plt.bar([i + bar_width for i in x], avg_data['humidity'],
            width=bar_width, label='Avg Humidity (%)', color='orange')

    plt.xlabel("City")
    plt.ylabel("Values")
    plt.title("Average Temperature and Humidity by City")
    plt.xticks([i + bar_width / 2 for i in x], avg_data['city'])
    plt.legend()
    plt.grid(True)
    plt.savefig("avg_temp_humidity.png")
    plt.close()


def plot_wind_speed_distribution():
    plt.figure(figsize=(10, 6))
    sns.histplot(data['wind_speed'], kde=True, color='green', bins=10)
    plt.xlabel("Wind Speed (m/s)")
    plt.ylabel("Frequency")
    plt.title("Wind Speed Distribution")
    plt.grid(True)
    plt.savefig("wind_speed_distribution.png")
    plt.close()


def test_temperature_normality():
    stat, p_value = shapiro(data['temperature'])
    if p_value > 0.05:
        result = "Распределение температуры является нормальным."
    else:
        result = "Распределение температуры отличается от нормального."
    return result, p_value


def calculate_correlation():
    correlation, p_value = pearsonr(data['temperature'], data['humidity'])
    if p_value < 0.05:
        result = f"Есть значимая корреляция между температурой и влажностью: {
            correlation:.2f}."
    else:
        result = "Корреляция между температурой и влажностью не является значимой."
    return result, correlation
