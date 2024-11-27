from loguru import logger
import telebot
import requests
import openai
import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Настройки
TELEGRAM_BOT_TOKEN = "ВАШ_ТОКЕН_БОТА"
ALTEG_API_BASE_URL = "https://api.alteg.io"
ALTEG_API_KEY = "ВАШ_КЛЮЧ_ДОСТУПА_К_ALTEG"
OPENAI_API_KEY = "ВАШ_КЛЮЧ_ОТ_OPENAI"

openai.api_key = OPENAI_API_KEY

# Настройка Loguru
logger.add("bot_logs.log", format="{time} {level} {message}", level="INFO", rotation="10 MB", compression="zip")

# Инициализация Telebot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Пример доступных слотов времени
available_slots = [
    "10:00 - 11:00",
    "12:00 - 13:00",
    "15:00 - 16:00"
]

# Получение свободных слотов
def get_free_time():
    logger.info("Запрос на получение доступного времени.")
    return "\n".join(available_slots)

# Запись клиента через API Alteg.io
def schedule_appointment(client_name, time_slot):
    logger.info(f"Попытка записи клиента {client_name} на время {time_slot}.")
    url = f"{ALTEG_API_BASE_URL}/appointments"
    headers = {"Authorization": f"Bearer {ALTEG_API_KEY}"}
    payload = {
        "client_name": client_name,
        "time_slot": time_slot,
        "created_at": datetime.datetime.now().isoformat()
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            logger.success(f"Запись клиента {client_name} успешно создана на {time_slot}.")
            return "Запись успешно создана!"
        else:
            logger.error(f"Ошибка при записи клиента {client_name}: {response.text}")
            return f"Ошибка при создании записи: {response.json().get('message', 'Неизвестная ошибка')}"
    except Exception as e:
        logger.exception(f"Исключение при записи клиента: {e}")
        return "Произошла ошибка при попытке записи."

# Проверка сообщения через GPT
def validate_message(message):
    logger.info(f"Обработка сообщения через GPT-4o: {message}")
    messages = [
        {"role": "system", "content": "Вы — помощник, который помогает с расписанием и записью на прием."},
        {"role": "user", "content": message}
    ]
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=100,
            temperature=0.7
        )
        gpt_response = response.choices[0].message['content'].strip()
        logger.info(f"Ответ GPT-4o: {gpt_response}")
        return gpt_response
    except Exception as e:
        logger.exception(f"Ошибка при обращении к GPT-4o: {e}")
        return "Извините, произошла ошибка при обработке вашего запроса."

# Генерация кнопок выбора времени
def generate_time_buttons():
    keyboard = InlineKeyboardMarkup()
    for slot in available_slots:
        keyboard.add(InlineKeyboardButton(slot, callback_data=f"choose_time:{slot}"))
    return keyboard

# Обработчик команды /start
@bot.message_handler(commands=["start"])
def start(message):
    logger.info(f"Пользователь {message.chat.username} начал диалог.")
    bot.reply_to(message, "Добро пожаловать! Чем я могу помочь?")

# Обработчик текстовых сообщений
@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    user_message = message.text
    user_name = message.chat.username
    logger.info(f"Получено сообщение от {user_name}: {user_message}")
    gpt_response = validate_message(user_message)

    if "свободное время" in gpt_response.lower():
        free_times = get_free_time()
        bot.reply_to(message, f"Вот доступные слоты:\n{free_times}", reply_markup=generate_time_buttons())
    elif "записаться" in gpt_response.lower():
        bot.reply_to(message, "Выберите удобное время из списка:", reply_markup=generate_time_buttons())
    else:
        logger.warning(f"Нераспознанный запрос от {user_name}: {user_message}")
        bot.reply_to(message, "Извините, я не понял ваш запрос.")

# Обработчик выбора времени
@bot.callback_query_handler(func=lambda call: call.data.startswith("choose_time:"))
def handle_time_selection(call):
    user_name = call.from_user.username
    time_slot = call.data.split(":")[1]
    logger.info(f"Пользователь {user_name} выбрал время {time_slot}.")
    result = schedule_appointment(user_name, time_slot)
    bot.send_message(call.message.chat.id, result)

# Запуск бота
if __name__ == "__main__":
    logger.info("Запуск Telegram-бота...")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logger.exception(f"Ошибка в основном процессе: {e}")
