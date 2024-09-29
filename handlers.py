import html
import aiogram.types
import keyboards
import music_handlers
import re
import aiogram.filters

from aiogram import Bot, html, F, Router
from aiogram.filters import CommandStart, Command, Filter
from aiogram.types import Message, InlineKeyboardMarkup, CallbackQuery, FSInputFile

router = Router()
search_result = None


@router.message(CommandStart())
async def get_start_handler(message: Message) -> None:
    await message.answer(f"Привет, {html.bold(message.from_user.full_name)}!",
                         reply_markup=await keyboards.get_start_keyboard())


@router.message(Command('help'))
async def get_help(message: Message) -> None:
    await message.answer(f"Тут /help")


@router.message(F.text == 'Найти песню 🎧')
async def request_name(message: Message) -> None:
    await message.answer(f"Введи название песни, которую хочешь скачать")

    @router.message()
    async def get_tracks_list(message: Message) -> None:
        global search_result
        search_result = music_handlers.search_tracks(message.text)

        if not search_result:
            await message.answer(f"Такой песни нет в каталоге :(")
        else:
            await message.answer(f"Выбери песню из предложенных",
                                 reply_markup=await keyboards.get_search_result_keyboard(search_result))


@router.callback_query(lambda callback: re.fullmatch(r'goto [0-9]+', callback.data))
async def get_previous_page(callback: CallbackQuery) -> None:
    global search_result
    page = int(callback.data.split()[-1])
    result = await keyboards.get_search_result_keyboard(search_result, page)
    if result:
        await callback.answer('')
        await callback.message.edit_text(f"Выбери песню из предложенных",
                                         reply_markup=result)
    else:
        await callback.answer('')


@router.callback_query(lambda callback: re.fullmatch(r'download [0-9]+', callback.data))
async def download_track(callback: CallbackQuery) -> None:

    id = int(callback.data.split()[-1])
    file_path = music_handlers.download_track(id)
    telegram_file_name = music_handlers.get_telegram_file_name(id)
    if id:
        await callback.answer('')
        await callback.message.answer_audio(FSInputFile(file_path), title=telegram_file_name)
    else:
        await callback.answer('')


# @router.message()
# async def echo_handler(message: Message) -> None:
#    try:
#        await message.send_copy(chat_id=message.chat.id)
#    except TypeError:
#        await message.answer("Nice try!")
