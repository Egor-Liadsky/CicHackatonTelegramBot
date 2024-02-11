import asyncio
import base64
import io
import logging

import requests
from aiogram import Bot, Dispatcher, types
from aiogram import F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import setting


class Problems(StatesGroup):
    send_geo = State()
    send_photo = State()
    send_status = State()
    send_current_info_text = State()


# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)
# Объект бота
bot = Bot(token=setting.TOKEN)
# Диспетчер
dp = Dispatcher()


# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    # button = types.KeyboardButton(text="Share Position", request_location=True)
    # keyboard = types.InlineKeyboardMarkup(button)

    kb = [
        [types.KeyboardButton(text="Отправить текущую геолокацию", request_location=True)],
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await state.set_state(Problems.send_geo)
    await message.answer("Привет! Тут будет какой-то текст который Егор допишет обязательно", reply_markup=keyboard)


@dp.message(Problems.send_geo, F.content_type.in_({'location'}))
async def handle_location(message: types.Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude
    reply = "Хорошо, теперь отправь фотографию проблемного места\nlatitude:  {}\nlongitude: {}".format(lat, lon)
    await state.set_data({'lat': lat, 'lon': lon})
    await state.set_state(Problems.send_photo)
    await message.answer(reply, reply_markup=types.ReplyKeyboardRemove())


@dp.message(Problems.send_photo)
async def handle_location(message: types.Message, state: FSMContext):
    await state.set_state(Problems.send_current_info_text)
    data = await state.get_data()
    file_id = message.photo[-1].file_id

    file = await bot.get_file(file_id)
    file_path = file.file_path

    my_object: io.BytesIO = await bot.download_file(file_path)
    byte_obj = my_object.read()
    data.update({'photo': base64.b64encode(byte_obj).decode('utf-8')})

    await state.set_data(data)
    await message.answer("Отлично! Теперь опиши проблему, которую ты увидел")


@dp.message(Problems.send_status)
async def handle_status(message: types.Message, state: FSMContext):
    inline_btn_1 = InlineKeyboardButton(callback_data='button1', text="Первая кнопка!")
    inline_kb1 = InlineKeyboardMarkup.add(inline_btn_1)
    reply = "Выбери степень разрушения объекта"
    await message.answer(reply, reply_markup=inline_kb1)


@dp.message(Problems.send_current_info_text)
async def handle_location(message: types.Message, state: FSMContext):
    data = await state.get_data()
    json_data = {
        "description": message.text,
        "city": 'Бахмут',
        "latitude": data.get('lat'),
        "longitude": data.get('lon'),
        "image": data.get('photo'),
        "userCreatedId": message.from_user.id,
        "statusId": 12
    }
    result = requests.post(setting.SERVER_IP + '/api/markers', json=json_data)

    await state.clear()
    await message.answer("Хорошо! Мы внесли все данные в нашу базу."
                         "\nЕсли будут какие-то вопросы, тебе напишет куратор Азовского моря."
                         "\nСпасибо за вклад в чистое море!"
                         "\nНаберите /start для вноса нового обьекта.")


# Запуск процесса поллинга новых апдейтов
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
