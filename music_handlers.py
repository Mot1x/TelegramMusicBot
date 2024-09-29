import subprocess
import sys
import os

from pathlib import Path
from yandex_music import Client, Track, Album
from dotenv import load_dotenv

load_dotenv('.env')
TOKEN = os.getenv('YANDEX_TOKEN')
download_path = Path(__file__).parent / 'downloads'
Path(download_path).mkdir(parents=True, exist_ok=True)

client = Client(token=TOKEN)
client.init()


def search_tracks(query):
    result = []

    for current_page in range(5):
        page_tracks = client.search(query, page=current_page, type_='track').tracks
        if not page_tracks:
            break
        result.extend(page_tracks.results)

    return result


def get_telegram_file_name(track_id: int):
    track = client.tracks([track_id])[0]
    return f'{', '.join(track.artists_name())} — {track.title}.mp3'


def download_track(track_id: int | str):
    track = client.tracks([track_id])[0]
    file_path = download_path / f'{track_id}.mp3'
    track.download(str(file_path), bitrate_in_kbps=320)
    return str(file_path)


def delete_track(track_id: int | str):
    file_path = download_path / f'{track_id}.mp3'
    os.remove(str(file_path))



