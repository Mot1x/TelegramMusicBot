import html
import keyboards
import music_handlers
import re

from database import add_row, get_ids_by_track_id
from aiogram import html, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile

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
            return

        await message.answer(f"Выбери песню из предложенных",
                             reply_markup=await keyboards.get_search_result_keyboard(search_result))


@router.callback_query(lambda callback: re.fullmatch(r'goto [0-9]+', callback.data))
async def get_previous_page(callback: CallbackQuery) -> None:
    global search_result
    page = int(callback.data.split()[-1])
    result = await keyboards.get_search_result_keyboard(search_result, page)

    if result:
        await callback.message.edit_text(f"Выбери песню из предложенных", reply_markup=result)

    await callback.answer('')


@router.callback_query(lambda callback: re.fullmatch(r'download [0-9]+', callback.data))
async def download_track(callback: CallbackQuery) -> None:
    track_id = int(callback.data.split()[-1])
    other_ids = await get_ids_by_track_id(track_id)

    if other_ids:
        message_id = other_ids.message_id
        from_chat_id = other_ids.chat_id
        chat_id = callback.message.chat.id

        await callback.bot.forward_message(chat_id=chat_id, from_chat_id=from_chat_id,
                                           message_id=message_id)
    else:
        file_path = music_handlers.download_track(track_id)
        telegram_file_name = music_handlers.get_telegram_file_name(track_id)

        message = await callback.message.answer_audio(FSInputFile(file_path), title=telegram_file_name)
        message_id = message.message_id
        chat_id = message.chat.id

        await add_row(track_id, chat_id, message_id)
        music_handlers.delete_track(track_id)

    await callback.answer('')
