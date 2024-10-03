from pathlib import Path
from typing import Any
from yandex_music import Client, Track, Album, Artist
from settings import settings

yandex_token = settings.yandex_token
download_path = Path(__file__).parent / 'downloads'
Path(download_path).mkdir(parents=True, exist_ok=True)

client = Client(token=yandex_token)
client.init()


def search(item_type: str, query: str) -> list[Track | Album | Artist]:
    result = []
    page_count = 5
    for current_page in range(page_count):
        page = client.search(query, page=current_page, type_=item_type)

        if item_type == 'track':
            page = page.tracks
        elif item_type == 'album':
            page = page.albums
        elif item_type == 'artist':
            page = page.artists

        if not page:
            break
        result.extend(page.results)

    return result


def get_telegram_file_name(track_id: int) -> str:
    track = client.tracks([track_id])[0]
    return f"{', '.join(track.artists_name())} — {track.title}.mp3"


def download_track(track_id: int | str, path: Path = download_path) -> str:
    track = client.tracks([track_id])[0]

    file_path = path / f'{track_id}.mp3'
    if not file_path.exists():
        track.download(str(file_path), bitrate_in_kbps=320)
    print(f"{', '.join(track.artists_name())} — {track.title}")
    return str(file_path)


def delete_track(track_id: int | str, path: Path = download_path) -> None:
    file_path = path / f'{track_id}.mp3'
    if file_path.exists():
        file_path.unlink()


def get_track_ids(album_id: int | str) -> list[int]:
    album = client.albums([album_id])[0].with_tracks().volumes

    track_ids: list[int] = []
    for volume in album:
        for track in volume:
            track_ids.append(int(track.id))
    return track_ids


def download_album(album_id: int | str) -> list[str]:
    track_ids = get_track_ids(album_id)
    tracks_path: list[str] = []
    for track_id in track_ids:
        tracks_path.append(download_track(track_id, download_path / album_id))
    return tracks_path


def delete_album(album_id: int | str) -> None:
    album_volumes = client.albums([album_id])[0].volumes

    for volume in album_volumes:
        for track in volume:
            download_track(track.id, download_path / album_id)


def get_artist_info(artist_id: int | str) -> dict[str, Any]:
    return client.artists([artist_id])[0].__dict__


def get_artist_tracks(artist_id: int) -> list[Track]:
    artist = client.artists([artist_id])[0]
    return artist.getTracks(page_size=100).tracks


def get_artist_cover(artist_id: int) -> str:
    artist = client.artists([artist_id])[0]
    return artist.cover.get_url(size='1000x1000')
