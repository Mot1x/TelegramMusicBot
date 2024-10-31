import asyncio
import html
import logging

from pathlib import Path
from typing import Any

import yandex_music.exceptions
from yandex_music import ClientAsync, Track, Album, Artist, Chart, ChartInfo, Playlist, TrackShort
from settings import settings
from additional_classes import setup_logger

setup_logger()
yandex_token = settings.yandex_token
download_path = Path(__file__).parent / 'downloads'
Path(download_path).mkdir(parents=True, exist_ok=True)


async def init_client():
    cli = ClientAsync(token=yandex_token)
    await cli.init()
    return cli


client = asyncio.run(init_client())


async def search(item_type: str, query: str, start_page=0, page_count=5) -> list[Track | Album | Artist]:
    result = []

    for current_page in range(start_page, start_page + page_count):
        try:
            page = await client.search(query, page=current_page, type_=item_type)
        except yandex_music.exceptions.BadRequestError as e:
            logging.info(f'{e}: Inline query was started')
            break

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


async def get_chart():
    chart: ChartInfo = await client.chart()
    tracks = [track.track for track in chart.chart.tracks]
    return tracks


async def get_telegram_file_name(track_id: int) -> str:
    tracks: list[Track] = await client.tracks([track_id])
    track: Track = tracks[0]
    return html.escape(f"{', '.join(track.artists_name())} — {track.title}")


async def get_title(track_id: int) -> str:
    tracks: list[Track] = await client.tracks([track_id])
    track: Track = tracks[0]
    return html.escape(f"{track.title}")


async def get_performers(track_id: int) -> str:
    tracks: list[Track] = await client.tracks([track_id])
    track: Track = tracks[0]
    return html.escape(f"{', '.join(track.artists_name())}")


async def download_track(track_id: int | str, path: Path = download_path) -> str:
    tracks: list[Track] = await client.tracks([track_id])
    track: Track = tracks[0]

    file_path = path / f'{track_id}.mp3'

    if not file_path.exists():
        await track.download_async(str(file_path), bitrate_in_kbps=320)
    logging.info(f"{', '.join(track.artists_name())} — {track.title}")
    return str(file_path)


async def delete_track(track_id: int | str, path: Path = download_path) -> None:
    file_path = path / f'{track_id}.mp3'
    if file_path.exists():
        file_path.unlink()


async def delete_thumb(track_id: int | str, path: Path = download_path) -> None:
    file_path = path / f'{track_id}.jpg'
    if file_path.exists():
        file_path.unlink()


async def get_track_ids(album_id: int | str) -> list[int]:
    albums_list: list[Album] = await client.albums([album_id])
    album_with_tracks: Album = await albums_list[0].with_tracks_async()
    album: list[list[Track]] = album_with_tracks.volumes

    track_ids: list[int] = []
    for volume in album:
        for track in volume:
            track_ids.append(int(track.id))
    return track_ids


async def get_track_thumb(track_id: int | str) -> str:
    tracks: list[Track] = await client.tracks([track_id])
    return tracks[0].get_cover_url(size='200x200')


async def download_album(album_id: int | str) -> list[str]:
    track_ids = await get_track_ids(album_id)
    tracks_path: list[str] = []
    for track_id in track_ids:
        tracks_path.append(await download_track(track_id, download_path / album_id))
    return tracks_path


async def delete_album(album_id: int | str) -> None:
    albums_list: list[Album] = await client.albums([album_id])
    album_volumes: list[list[Track]] = albums_list[0].volumes

    for volume in album_volumes:
        for track in volume:
            await download_track(track.id, download_path / album_id)


async def get_artist_info(artist_id: int | str) -> str:
    info_text: str = ''
    artists_list = await client.artists([artist_id])
    artist: Artist = artists_list[0]

    info_text += f'Исполнитель: {artist.name}\n' if artist.name else ''
    info_text += f'Треков: {artist.counts.tracks}\n' if artist.counts and artist.counts.tracks else ''
    info_text += f'{artist.ratings.month} место в топе артистов\n' if artist.ratings and artist.ratings.month else ''
    info_text += f'Описание: {artist.description.text}' if artist.description else ''

    return info_text


async def get_artist_tracks(artist_id: int) -> list[Track]:
    artists_list: list[Artist] = await client.artists([artist_id])
    tracks = await artists_list[0].getTracksAsync(page_size=100)
    return tracks.tracks


async def get_artist_cover(artist_id: int) -> str:
    artists_list: list[Artist] = await client.artists([artist_id])
    return artists_list[0].cover.get_url(size='1000x1000')
