import html
import keyboards
import music_handlers
import re
import os

from settings import settings
from database import add_row, get_ids_by_track_id
from aiogram import html, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaAudio, URLInputFile, InlineQuery, \
    InlineQueryResultArticle, InputTextMessageContent, InlineQueryResultAudio, InlineKeyboardMarkup, \
    InlineKeyboardButton, InlineQueryResultCachedAudio
from additional_classes import Patterns, TrackMetadata, Labels

router = Router()
current_search_type = 'track'
search_result = None
storage_chat_id = f'-{settings.storage_chat_id}'


@router.message(CommandStart())
async def get_start_handler(message: Message) -> None:
    await message.answer(f"Привет, {html.bold(message.from_user.full_name)}!",
                         reply_markup=await keyboards.get_start_keyboard())


@router.message(Command('help'))
async def get_help(message: Message) -> None:
    await message.answer(f"Тут /help")


@router.message(F.text == Labels.commands[Labels.chart])
async def send_chart(message: Message) -> None:
    global search_result
    search_result = await music_handlers.get_chart()
    await message.answer("Чарт Яндекс Музыка:",
                         reply_markup=await keyboards.get_search_result_keyboard(search_result))


@router.message(F.text.in_(Labels.commands.values()))
async def request(message: Message) -> None:
    if message.text == Labels.commands[Labels.chart]:
        return
    global current_search_type
    labels = Labels()
    current_search_type = labels.get_key_by_value(message.text)
    await message.answer(Labels.input_prompts[current_search_type])


@router.message()
async def get_list(message: Message) -> None:
    if message.audio:
        print(0, message.chat.id, message.message_id, message.audio.file_id)
    await get_list_of_items(current_search_type, message)


@router.callback_query(lambda callback: re.fullmatch(Patterns.view_artist, callback.data))
async def view_artist(callback: CallbackQuery) -> None:
    await callback.answer('')
    global search_result

    artist_id = int(callback.data.split()[-1])
    search_result = await music_handlers.get_artist_tracks(artist_id)
    info = await music_handlers.get_artist_info(artist_id)
    photo_url = await music_handlers.get_artist_cover(artist_id)

    await callback.bot.send_photo(chat_id=callback.message.chat.id, photo=photo_url, caption=info)
    await callback.message.answer(Labels.selection_prompts[Labels.track],
                                  reply_markup=await keyboards.get_search_result_keyboard(search_result))


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
    loading_message = await callback.bot.send_message(chat_id=callback.message.chat.id,
                                                      text=f'Скачиваем {await music_handlers.get_telegram_file_name(track_id)}')
    track, is_track_from_db = await get_track(track_id)

    message = await callback.bot.send_media_group(media=[track], chat_id=callback.message.chat.id)
    await loading_message.delete()
    message = message[0]

    if not is_track_from_db:
        await add_row(track_id, message.chat.id, message.message_id, message.audio.file_id)
        await music_handlers.delete_track(track_id)


@router.callback_query(lambda callback: re.fullmatch(Patterns.download_inline, callback.data))
async def download_inline_track(callback: CallbackQuery) -> None:
    await callback.answer('')
    track_id = int(callback.data.split()[-1])
    track, is_track_from_db = await get_track(track_id)

    if not is_track_from_db:
        message = await callback.bot.send_media_group(media=[track], chat_id=storage_chat_id)
        message = message[0]
        await add_row(track_id, message.chat.id, message.message_id, message.audio.file_id)
        await music_handlers.delete_track(track_id)


@router.callback_query(lambda callback: re.fullmatch(Patterns.download_album, callback.data))
async def send_album(callback: CallbackQuery) -> None:
    await callback.answer('')
    album_id = int(callback.data.split()[-1])
    track_ids = await music_handlers.get_track_ids(album_id)
    await send_tracks(track_ids, callback)


@router.inline_query()
async def inline_send_track(query: InlineQuery):
    current_page = int(query.offset) if query.offset else 0

    result = await music_handlers.search(Labels.track, query.query, current_page, 1)
    results: list[InlineQueryResultCachedAudio | InlineQueryResultAudio | InlineQueryResultArticle] = []

    for track in result:
        ids = await get_ids_by_track_id(track.id)
        search_id = str(track.id)
        performers = ', '.join(track.artists_name())
        thumb_url = music_handlers.get_track_thumb(track.id)
        print(track.title, ', '.join(track.artists_name()))
        if ids:
            results.append(InlineQueryResultAudio(
                id=search_id,
                audio_url=ids.file_id,
                title=track.title,
                performer=performers
            ))
        else:
            results.append(InlineQueryResultArticle(
                id=search_id,
                title=track.title,
                description=performers,
                thumbnail_url=await thumb_url,
                input_message_content=InputTextMessageContent(
                    message_text=f"{performers} — {track.title}\n"
                                 f"Трек ещё никто не скачивал. Нажмите на кнопку ниже, "
                                 f"найдите этот трек снова и отправьте"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Скачать",
                        callback_data=f"download inline {track.id}"
                    )
                ]]
                ),
                callback_data=f"download track {track.id}"
            ))
    await query.answer(results, cache_time=1, next_offset=str(current_page + 1))


async def get_list_of_items(item_type: str, message: Message) -> None:
    if item_type not in Labels.__dict__.keys():
        raise ValueError('Item type is not valid')

    global search_result
    search_result = await music_handlers.search(item_type, message.text)

    if not search_result:
        await message.answer(Labels.no_results_messages[item_type])
        return

    await message.answer(Labels.selection_prompts[item_type],
                         reply_markup=await keyboards.get_search_result_keyboard(search_result))


async def get_track(track_id: int) -> (InputMediaAudio | None, bool):
    other_ids = await get_ids_by_track_id(track_id)

    if other_ids:
        file_id = other_ids.file_id
        return InputMediaAudio(media=file_id), True

    title = await music_handlers.get_title(track_id)
    performers = await music_handlers.get_performers(track_id)
    file_path = await music_handlers.download_track(track_id)
    thumb_url = await music_handlers.get_track_thumb(track_id)

    return InputMediaAudio(media=FSInputFile(file_path), title=title, performer=performers,
                           thumbnail=(URLInputFile(thumb_url))), False


async def send_tracks(track_ids: list[int], callback: CallbackQuery) -> None:
    tracks_data = await get_tracks_data(track_ids, callback)
    messages = await get_group_messages(tracks_data, callback)

    for index, message in enumerate(messages):
        track_data = tracks_data[index]
        if not track_data.is_from_db:
            await add_track_to_db(track_data, message)
            await music_handlers.delete_track(track_data.track_id)


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
        filename = await music_handlers.get_telegram_file_name(track_id)
        await message.edit_text(
            f'Скачиваем {filename} ({index + 1}/{len(track_ids)})')
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
