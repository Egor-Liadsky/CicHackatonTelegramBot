import asyncio
import logging
import typing

import aiogram.utils.keyboard
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram import F

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import requests

import setting
import io

import base64

from aiogram.filters.callback_data import CallbackData


class NumbersCallbackFactory(CallbackData, prefix="fabnum"):
    action: str
    value: types.Optional[int] = None


class Problems(StatesGroup):
    send_geo = State()
    send_photo = State()
    send_current_info_text = State()
    send_status = State()


logging.basicConfig(level=logging.INFO)
bot = Bot(token=setting.TOKEN)
dp = Dispatcher()


# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
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
async def handle_photo(message: types.Message, state: FSMContext):
    await state.set_state(Problems.send_status)
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
    await state.set_state(Problems.send_current_info_text)

    data = await state.get_data()
    data.update({'description': message.text})
    await state.set_data(data)

    status: typing.List[dict] = requests.get(setting.SERVER_IP + '/api/status').json()
    # await state.set_data(data)

    builder = aiogram.utils.keyboard.InlineKeyboardBuilder()

    for status_key in status:
        builder.button(
            text=status_key['name'],
            callback_data=NumbersCallbackFactory(action=status_key['name'], value=status_key['id'])
        )

    await message.answer(
        "Выбери статус разрушения обьекта",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(NumbersCallbackFactory.filter())
async def send_random_value(callback, callback_data: NumbersCallbackFactory, state: FSMContext):
    data = await state.get_data()
    json_data = {
        "description": data.get('description'),
        "city": 'Бахмут',
        "latitude": data.get('lat'),
        "longitude": data.get('lon'),
        "image": data.get('photo'),
        "userCreatedId": callback.message.chat.username,
        "statusId": callback_data.value
    }
    result = requests.post(setting.SERVER_IP + '/api/markers', json=json_data)

    await state.clear()
    await callback.message.answer("Хорошо! Мы внесли все данные в нашу базу."
                                  "\nЕсли будут какие-то вопросы, тебе напишет куратор Азовского моря."
                                  "\nСпасибо за вклад в чистое море!"
                                  "\nНаберите /start для вноса нового обьекта.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
