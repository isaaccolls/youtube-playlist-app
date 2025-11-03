import os
import time
import logging
from typing import Optional

import requests
from mutagen.id3 import ID3, USLT, ID3NoHeaderError
from mutagen.mp3 import MP3

from constants import pathForMusic

LYRICS_DIR = pathForMusic
REQUEST_TIMEOUT_SECONDS = 8
SLEEP_BETWEEN_REQUESTS_SECONDS = 0.5


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def list_mp3_files(directory: str) -> list[str]:
    if not os.path.isdir(directory):
        logging.error(f"🚫 Directorio no existe: {directory}")
        return []
    files = []
    for name in os.listdir(directory):
        if name.lower().endswith(".mp3"):
            files.append(os.path.join(directory, name))
    files.sort()
    return files


def get_id3_tags(mp3_path: str) -> Optional[ID3]:
    try:
        return ID3(mp3_path)
    except ID3NoHeaderError:
        return None
    except Exception as e:
        logging.warning(f"⚠️ Error leyendo ID3 de {os.path.basename(mp3_path)}: {e}")
        return None


def has_lyrics(tags: Optional[ID3]) -> bool:
    if not tags:
        return False
    # USLT frames contain unsynchronised lyrics/text transcription
    for frame in tags.getall("USLT"):
        if isinstance(frame, USLT) and frame.text and frame.text.strip():
            return True
    return False


def extract_title_artist_album(tags: Optional[ID3]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    if not tags:
        return None, None, None
    def _first_text(frame_key: str) -> Optional[str]:
        frame = tags.get(frame_key)
        if not frame:
            return None
        try:
            # Many text frames are T*** classes with .text list
            text = frame.text if hasattr(frame, "text") else None
            if not text:
                return None
            if isinstance(text, list):
                return text[0].strip() if text and isinstance(text[0], str) else None
            return str(text).strip()
        except Exception:
            return None
    title = _first_text("TIT2")
    artist = _first_text("TPE1")
    album = _first_text("TALB")
    return title, artist, album


def fetch_lyrics_lyrics_ovh(artist: str, title: str) -> Optional[str]:
    # Public, no-key API. May fail for some songs.
    url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        if resp.status_code != 200:
            return None
        data = resp.json()
        lyrics = data.get("lyrics")
        if lyrics and isinstance(lyrics, str) and lyrics.strip():
            return lyrics.strip()
        return None
    except Exception:
        return None


def fetch_lyrics(artist: str, title: str, album: Optional[str]) -> Optional[str]:
    # Try primary provider first
    lyrics = fetch_lyrics_lyrics_ovh(artist, title)
    if lyrics:
        return lyrics
    # Potential future fallbacks could be added here.
    return None


def save_lyrics_to_mp3(mp3_path: str, lyrics_text: str) -> bool:
    try:
        # Ensure file can be opened by mutagen
        _ = MP3(mp3_path)
        try:
            tags = ID3(mp3_path)
        except ID3NoHeaderError:
            tags = ID3()
        # Remove empty USLT frames to avoid duplicates
        for frame in list(tags.getall("USLT")):
            try:
                if not frame.text or not frame.text.strip():
                    tags.delall("USLT")
            except Exception:
                pass
        # Add lyrics
        tags.add(USLT(encoding=3, lang="eng", desc="", text=lyrics_text))
        tags.save(mp3_path)
        return True
    except Exception as e:
        logging.error(f"🚫 Error guardando letras en {os.path.basename(mp3_path)}: {e}")
        return False


def process_file(mp3_path: str) -> dict:
    filename = os.path.basename(mp3_path)
    result = {
        "file": filename,
        "status": "skipped",
        "reason": None,
        "provider": None,
    }

    tags = get_id3_tags(mp3_path)

    if has_lyrics(tags):
        result["status"] = "already_has_lyrics"
        logging.info(f"✅ Ya contiene letra: {filename}")
        return result

    title, artist, album = extract_title_artist_album(tags)
    if not title or not artist:
        result["status"] = "missing_tags"
        result["reason"] = "Faltan etiquetas ID3 requeridas (title/artist)"
        logging.warning(f"⚠️  Faltan etiquetas en {filename} (title/artist requeridos). Se omite.")
        return result

    logging.info(f"🔎 Buscando letra para: '{title}' - {artist}{f' | {album}' if album else ''}")
    lyrics_text = fetch_lyrics(artist, title, album)
    time.sleep(SLEEP_BETWEEN_REQUESTS_SECONDS)

    if not lyrics_text:
        result["status"] = "not_found"
        result["reason"] = "Letra no encontrada"
        logging.info(f"❌ Letra no encontrada: {filename}")
        return result

    ok = save_lyrics_to_mp3(mp3_path, lyrics_text)
    if ok:
        result["status"] = "updated"
        logging.info(f"🎤 Letra agregada: {filename}")
    else:
        result["status"] = "save_failed"
        result["reason"] = "Error guardando ID3"
    return result


def main() -> None:
    setup_logging()
    logging.info("🎼 Iniciando verificación de letras en MP3...")
    files = list_mp3_files(LYRICS_DIR)
    logging.info(f"📂 Archivos .mp3 detectados: {len(files)}")

    counters = {
        "processed": 0,
        "already_has_lyrics": 0,
        "updated": 0,
        "missing_tags": 0,
        "not_found": 0,
        "save_failed": 0,
    }

    for mp3_path in files:
        res = process_file(mp3_path)
        counters["processed"] += 1
        status = res.get("status")
        if status in counters:
            counters[status] += 1

    logging.info("\n📊 Resumen:")
    logging.info(f"   Total procesados: {counters['processed']}")
    logging.info(f"   Ya tenían letra: {counters['already_has_lyrics']}")
    logging.info(f"   Letras agregadas: {counters['updated']}")
    logging.info(f"   Faltan tags: {counters['missing_tags']}")
    logging.info(f"   No encontradas: {counters['not_found']}")
    logging.info(f"   Error guardando: {counters['save_failed']}")


if __name__ == "__main__":
    main()
