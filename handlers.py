import html
from typing import Any

import keyboards
import music_handlers
import re
import os

from re import Pattern
from database import add_row, get_ids_by_track_id
from aiogram import html, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaAudio, InputFile
from dataclasses import dataclass
from types import MappingProxyType

router = Router()
current_search_type = 'track'
search_result = None


@dataclass(frozen=True)
class Patterns:
    goto: Pattern[str] = re.compile(r'goto [0-9]+')
    download_track: Pattern[str] = re.compile(r'download track [0-9]+')
    download_album: Pattern[str] = re.compile(r'download album [0-9]+')
    view_artist: Pattern[str] = re.compile(r'view artist [0-9]+')


@dataclass(frozen=True)
class TrackMetadata:
    track_id: int
    track: InputMediaAudio
    is_from_db: bool


@dataclass(frozen=True)
class Labels:
    artist: str = 'artist'
    track: str = 'track'
    album: str = 'album'

    commands: dict[str, str] = MappingProxyType({
        'artist': 'Найти артиста 👤',
        'track': 'Найти песню 🎧',
        'album': 'Найти альбом 💿'
    })

    no_results_messages: dict[str, str] = MappingProxyType({
        'artist': f"Такого исполнителя нет в каталоге :(",
        'track': f"Такой песни нет в каталоге :(",
        'album': f"Такого альбома нет в каталоге :("
    })

    selection_prompts: dict[str, str] = MappingProxyType({
        'artist': f"Выбери артиста из предложенных",
        'track': f"Выбери песню из предложенных",
        'album': f"Выбери альбом из предложенных"
    })

    input_prompts: dict[str, str] = MappingProxyType({
        'artist': f"Введи имя исполнителя, которого хочешь посмотреть",
        'track': f"Введи название песни, которую хочешь скачать",
        'album': f"Введи название альбома, который хочешь скачать"
    })

    def get_key_by_value(self, input_value: str) -> str:
        dictionaries = [elem for elem in vars(self).values() if isinstance(elem, MappingProxyType)]
        for dictionary in dictionaries:
            for pair in dictionary.items():
                if input_value == pair[1]:
                    return pair[0]


@router.message(CommandStart())
async def get_start_handler(message: Message) -> None:
    await message.answer(f"Привет, {html.bold(message.from_user.full_name)}!",
                         reply_markup=await keyboards.get_start_keyboard())


@router.message(Command('help'))
async def get_help(message: Message) -> None:
    await message.answer(f"Тут /help")


@router.message(F.text.in_(Labels.commands.values()))
async def request(message: Message) -> None:
    global current_search_type
    labels = Labels()
    current_search_type = labels.get_key_by_value(message.text)
    await message.answer(Labels.input_prompts[current_search_type])


@router.message()
async def get_list(message: Message) -> None:
    await get_list_of_items(current_search_type, message)


async def get_list_of_items(item_type: str, message: Message) -> None:
    if item_type not in Labels.__dict__.keys():
        raise ValueError('Item type is not valid')

    global search_result
    search_result = music_handlers.search(item_type, message.text)

    if not search_result:
        await message.answer(Labels.no_results_messages[item_type])
        return

    await message.answer(Labels.selection_prompts[item_type],
                         reply_markup=await keyboards.get_search_result_keyboard(search_result))


@router.callback_query(lambda callback: re.fullmatch(Patterns.view_artist, callback.data))
async def view_artist(callback: CallbackQuery) -> None:
    await callback.answer('')
    global search_result

    artist_id = int(callback.data.split()[-1])
    search_result = music_handlers.get_artist_tracks(artist_id)
    info = music_handlers.get_artist_info(artist_id)
    photo_url = music_handlers.get_artist_cover(artist_id)

    await callback.bot.send_photo(chat_id=callback.message.chat.id, photo=photo_url, caption=await get_info_text(info))
    await callback.message.answer(Labels.selection_prompts[Labels.track],
                         reply_markup=await keyboards.get_search_result_keyboard(search_result))


async def get_info_text(info: dict[str, Any]) -> str:
    return f'Исполнитель: {info['name']}\n'


@router.callback_query(lambda callback: re.fullmatch(Patterns.goto, callback.data))
async def get_previous_page(callback: CallbackQuery) -> None:
    global search_result
    page = int(callback.data.split()[-1])
    result = await keyboards.get_search_result_keyboard(search_result, page)

    if result:
        await callback.message.edit_text(callback.message.text, reply_markup=result)

    await callback.answer('')


@router.callback_query(lambda callback: re.fullmatch(Patterns.download_track, callback.data))
async def send_track(callback: CallbackQuery) -> None:
    await callback.answer('')

    track_id = int(callback.data.split()[-1])
    await callback.message.answer(f'Скачиваем {music_handlers.get_telegram_file_name(track_id)}')
    track, is_track_from_db = await get_track(track_id)

    message = await callback.bot.send_media_group(media=[track], chat_id=callback.message.chat.id)
    message = message[0]

    if not is_track_from_db:
        message_id = message.message_id
        chat_id = message.chat.id
        file_id = message.audio.file_id
        await add_row(track_id, chat_id, message_id, file_id)
        music_handlers.delete_track(track_id)


@router.callback_query(lambda callback: re.fullmatch(Patterns.download_album, callback.data))
async def send_album(callback: CallbackQuery) -> None:
    await callback.answer('')
    album_id = int(callback.data.split()[-1])
    track_ids = music_handlers.get_track_ids(album_id)
    await send_tracks(track_ids, callback)


async def get_track(track_id: int) -> (InputMediaAudio | None, bool):
    other_ids = await get_ids_by_track_id(track_id)

    if other_ids:
        file_id = other_ids.file_id
        return InputMediaAudio(media=file_id), True

    telegram_file_name = music_handlers.get_telegram_file_name(track_id)
    file_path = music_handlers.download_track(track_id)

    return InputMediaAudio(media=FSInputFile(file_path), title=telegram_file_name), False


async def send_tracks(track_ids: list[int], callback: CallbackQuery) -> None:
    tracks_data = await get_tracks_data(track_ids, callback)
    messages = await get_group_messages(tracks_data, callback)

    for index, message in enumerate(messages):
        track_data = tracks_data[index]
        if not track_data.is_from_db:
            await add_track_to_db(track_data, message)
            music_handlers.delete_track(track_data.track_id)


async def add_track_to_db(track_data: TrackMetadata, message: Message) -> None:
    message_id = message.message_id
    chat_id = message.chat.id
    file_id = message.audio.file_id
    await add_row(track_data.track_id, chat_id, message_id, file_id)


async def get_tracks_data(track_ids: list[int], callback: CallbackQuery) -> list[TrackMetadata]:
    tracks_data: list[TrackMetadata] = []
    message = await callback.bot.send_message(chat_id=callback.message.chat.id, text=f'Скачиваем альбом',
                                              disable_notification=True)
    for index, track_id in enumerate(track_ids):
        await message.edit_text(
            f'Скачиваем {music_handlers.get_telegram_file_name(track_id)[:-4]} ({index + 1}/{len(track_ids)})')
        track, is_track_from_db = await get_track(track_id)
        tracks_data.append(TrackMetadata(track_id, track, is_track_from_db))
    await message.delete()
    return tracks_data


async def get_group_messages(tracks_data: list[TrackMetadata], callback: CallbackQuery) -> list[Message]:
    messages: list[Message] = []
    chunks = list(split_tracks_into_chunks(tracks_data))
    for chunk in chunks:
        tracks = [item.track for item in chunk]
        messages.extend(await callback.bot.send_media_group(media=tracks, chat_id=callback.message.chat.id))
    return messages


def split_tracks_into_chunks(tracks_data: list[TrackMetadata]):
    tracks_data_copy = tracks_data.copy()

    while len(tracks_data_copy) > 0:
        chunk_size = get_chunk_size(tracks_data_copy)

        print(chunk_size, len(tracks_data_copy))
        yield tracks_data_copy[:chunk_size]
        tracks_data_copy = tracks_data_copy[chunk_size:]


def get_chunk_size(tracks_data):
    size = 0
    for index, track_data in enumerate(tracks_data):
        file: FSInputFile | str = track_data.track.media
        if isinstance(file, FSInputFile):
            size += os.path.getsize(file.path)
        if size >= 50 * 1024 * 1024 or index == 10:
            return index
    return len(tracks_data)

    # while size < 50 * 1024 * 1024 and index < len(tracks_data):
    #     file: FSInputFile | str = tracks_data[index].track.media
    #     if isinstance(file, FSInputFile):
    #         size += os.path.getsize(file.path)
    #     index += 1
    # return min(max(1, index), 10)

# def split_tracks_into_chunks(tracks_data: list[TrackMetadata]):
#     tracks_data_copy = tracks_data.copy()
#     chunk_size = get_chunk_size(tracks_data_copy)
#
#     while len(tracks_data_copy) > chunk_size or len(tracks_data_copy) != 0:
#         print(chunk_size, len(tracks_data_copy))
#         yield tracks_data_copy[:min(chunk_size, len(tracks_data_copy))]
#         tracks_data_copy = tracks_data_copy[chunk_size:]
#         chunk_size = get_chunk_size(tracks_data_copy)
#
#
# def get_chunk_size(tracks_data):
#     size = 0
#     index = 0
#     while size < 50 * 1024 * 1024 and index < len(tracks_data):
#         file: FSInputFile | str = tracks_data[index].track.media
#         if isinstance(file, FSInputFile):
#             size += os.path.getsize(file.path)
#         index += 1
#     return min(10, index - 1)
#
