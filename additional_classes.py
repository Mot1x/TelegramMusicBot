import re
from re import Pattern
from dataclasses import dataclass
from types import MappingProxyType
from aiogram.types import InputMediaAudio


@dataclass(frozen=True)
class Patterns:
    goto: Pattern[str] = re.compile(r'goto [0-9]+')
    download_track: Pattern[str] = re.compile(r'download track [0-9]+')
    download_album: Pattern[str] = re.compile(r'download album [0-9]+')
    download_inline: Pattern[str] = re.compile(r'download inline [0-9]+')
    download_chart: Pattern[str] = re.compile(r'download chart')
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
    chart: str = 'chart'

    commands: dict[str, str] = MappingProxyType({
        artist: 'Найти артиста 👤',
        track: 'Найти песню 🎧',
        album: 'Найти альбом 💿',
        chart: 'Чарт 🏆'
    })

    no_results_messages: dict[str, str] = MappingProxyType({
        artist: 'Такого исполнителя нет в каталоге :(',
        track: 'Такой песни нет в каталоге :(',
        album: 'Такого альбома нет в каталоге :('
    })

    selection_prompts: dict[str, str] = MappingProxyType({
        artist: 'Выбери артиста из предложенных',
        track: 'Выбери песню из предложенных',
        album: 'Выбери альбом из предложенных'
    })

    input_prompts: dict[str, str] = MappingProxyType({
        artist: 'Введи имя исполнителя, которого хочешь посмотреть',
        track: 'Введи название песни, которую хочешь скачать',
        album: 'Введи название альбома, который хочешь скачать'
    })

    def get_key_by_value(self, input_value: str) -> str:
        dictionaries = [elem for elem in vars(self).values() if isinstance(elem, MappingProxyType)]
        for dictionary in dictionaries:
            for pair in dictionary.items():
                if input_value == pair[1]:
                    return pair[0]
