from math import ceil
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from yandex_music import Track


async def get_start_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text='Найти песню 🎧'))
    return keyboard.as_markup(resize_keyboard=True)


async def get_search_result_keyboard(tracks: list[Track] | None, current_page=1,
                                     track_count_per_page=5) -> InlineKeyboardMarkup | None:
    if not tracks or track_count_per_page <= 0:
        return None

    tracks_per_message = 5
    keyboard = InlineKeyboardBuilder()
    page_count = ceil(len(tracks) / track_count_per_page)

    if current_page > page_count or current_page <= 0:
        return None

    for number, track in enumerate(tracks):
        if track_count_per_page * (current_page - 1) > number:
            continue

        keyboard.add(InlineKeyboardButton(text=f"{', '.join(track.artists_name())} — {track.title}",
                                          callback_data=f'download {track.id}'))
        if (number + 1) % tracks_per_message == 0:
            break

    keyboard.add(InlineKeyboardButton(text='<', callback_data=f'goto {current_page - 1}'))
    keyboard = keyboard.adjust(1)
    keyboard.add(InlineKeyboardButton(text=f'{current_page}/{page_count}',
                                      callback_data='nothing'))
    keyboard.add(InlineKeyboardButton(text='>', callback_data=f'goto {current_page + 1}'))
    return keyboard.as_markup(resize_keyboard=True)
