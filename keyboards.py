from math import ceil
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from yandex_music import Track, Album, Artist


async def get_start_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text='Найти песню 🎧'))
    keyboard.add(KeyboardButton(text='Найти альбом 💿'))
    keyboard.add(KeyboardButton(text='Найти артиста 👤'))
    keyboard.add(KeyboardButton(text='Чарт 🏆'))
    return keyboard.adjust(2).as_markup(resize_keyboard=True)


async def get_search_result_keyboard(items: list[Track | Album | Artist] | None, current_page=1,
                                     item_count_per_page=5) -> InlineKeyboardMarkup | None:
    if not items or item_count_per_page <= 0:
        return None

    items_per_message = 5
    keyboard = InlineKeyboardBuilder()
    page_count = ceil(len(items) / item_count_per_page)

    if current_page > page_count or current_page <= 0:
        return None

    for number, item in enumerate(items):
        if item_count_per_page * (current_page - 1) > number:
            continue

        if type(item) is Artist:
            keyboard.add(InlineKeyboardButton(text=f"{item.name}", callback_data=f'view artist {item.id}'))
        if type(item) is Album:
            artists_name = [i.name for i in item.artists]
            keyboard.add(InlineKeyboardButton(text=f"{', '.join(artists_name)} — {item.title}",
                                              callback_data=f'download album {item.id}'))
        if type(item) is Track:
            keyboard.add(InlineKeyboardButton(text=f"{', '.join(item.artists_name())} — {item.title}",
                                              callback_data=f'download track {item.id}'))

        if (number + 1) % items_per_message == 0:
            break

    keyboard.add(InlineKeyboardButton(text='<', callback_data=f'goto {current_page - 1}'))
    keyboard = keyboard.adjust(1)
    keyboard.add(InlineKeyboardButton(text=f'{current_page}/{page_count}',
                                      callback_data='nothing'))
    keyboard.add(InlineKeyboardButton(text='>', callback_data=f'goto {current_page + 1}'))
    return keyboard.as_markup(resize_keyboard=True)
