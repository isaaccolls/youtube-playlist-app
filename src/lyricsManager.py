import argparse
import os
import re
import threading
import time
import logging
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from urllib.parse import quote

import requests
from mutagen.id3 import ID3, USLT, ID3NoHeaderError
from mutagen.mp3 import MP3

from constants import pathForMusic

LYRICS_DIR = pathForMusic
REQUEST_TIMEOUT_SECONDS = 8
SLEEP_BETWEEN_REQUESTS_SECONDS = 0.5
# Canciones procesadas a la vez. El tiempo se va en esperar a la API de letras,
# así que los hilos rinden aunque sea Python; cada hilo sigue respetando la
# pausa entre sus propias peticiones para no saturar un servicio público.
DEFAULT_WORKERS = 8

LRCLIB_URL = "https://lrclib.net/api"
# lrclib pide identificar la aplicación que hace las peticiones.
USER_AGENT = "youtube-playlist-app lyricsManager"
LRCLIB_ATTEMPTS = 3
# Las marcas de tiempo de una letra sincronizada valen para una grabación
# concreta: si la duración no coincide con la del mp3 es otra versión (en vivo,
# remaster, edición con intro distinta) y la letra iría desfasada.
SYNCED_DURATION_TOLERANCE_SECONDS = 2
# Fallos de conexión seguidos tras los que se deja de consultar lyrics.ovh en
# esta ejecución: cuando el servicio está caído cada intento agota el timeout.
LYRICS_OVH_MAX_FAILURES = 3

FEAT_PATTERN = re.compile(r'\s*[\(\[](?:feat|ft)\.?\s+[^\)\]]+[\)\]]', re.IGNORECASE)
LRC_TIMESTAMP_PATTERN = re.compile(r'\[\d+:\d+(?:[.:]\d+)?\]\s?')

_thread_local = threading.local()
_lyrics_ovh_lock = threading.Lock()
_lyrics_ovh_failures = 0


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


def get_session() -> requests.Session:
    """Una sesión por hilo, para reutilizar la conexión entre peticiones."""
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        session.headers["User-Agent"] = USER_AGENT
        _thread_local.session = session
    return session


def normalize_title(title: str) -> str:
    """Título sin '(feat. X)', acentos, puntuación ni mayúsculas, para comparar."""
    text = FEAT_PATTERN.sub('', title or '').casefold()
    text = ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^\w\s]', ' ', text).split())


def synced_to_plain(synced_lyrics: str) -> str:
    """Quita las marcas de tiempo de una letra en formato LRC."""
    lines = [LRC_TIMESTAMP_PATTERN.sub('', line).strip() for line in synced_lyrics.splitlines()]
    return '\n'.join(lines).strip()


def _clean(text) -> Optional[str]:
    return text.strip() if isinstance(text, str) and text.strip() else None


def _lrclib_request(endpoint: str, params: dict):
    # Un fallo pasajero (timeout, 429, 5xx) se reintenta: si no, la canción
    # quedaría como "no encontrada" hasta la siguiente ejecución.
    for attempt in range(1, LRCLIB_ATTEMPTS + 1):
        try:
            resp = get_session().get(f"{LRCLIB_URL}/{endpoint}", params=params,
                                     timeout=REQUEST_TIMEOUT_SECONDS)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code != 429 and resp.status_code < 500:
                return None
        except Exception:
            pass
        if attempt < LRCLIB_ATTEMPTS:
            time.sleep(attempt)
    return None


def fetch_lyrics_lrclib(artist: str, title: str, album: Optional[str],
                        duration: Optional[int]) -> dict:
    """Devuelve {'plain': str | None, 'synced': str | None} desde lrclib.net.

    Primero pide la grabación exacta (artista, título, álbum y duración). Si
    no existe, busca por artista y título y se queda con la candidata de
    duración más parecida; la sincronizada solo se acepta si la duración
    coincide con la del mp3.
    """
    found = {"plain": None, "synced": None}

    if album and duration:
        exact = _lrclib_request("get", {
            "artist_name": artist, "track_name": title,
            "album_name": album, "duration": duration,
        })
        if isinstance(exact, dict):
            found["plain"] = _clean(exact.get("plainLyrics"))
            found["synced"] = _clean(exact.get("syncedLyrics"))
            if found["plain"] and found["synced"]:
                return found

    candidates = _lrclib_request("search", {"artist_name": artist, "track_name": title})
    if not isinstance(candidates, list):
        return found

    wanted = normalize_title(title)
    candidates = [c for c in candidates
                  if isinstance(c, dict) and normalize_title(c.get("trackName") or '') == wanted]

    def distance(candidate: dict) -> float:
        if not duration or not candidate.get("duration"):
            return float("inf")
        return abs(candidate["duration"] - duration)

    for candidate in sorted(candidates, key=distance):
        if not found["synced"] and distance(candidate) <= SYNCED_DURATION_TOLERANCE_SECONDS:
            found["synced"] = _clean(candidate.get("syncedLyrics"))
        if not found["plain"]:
            found["plain"] = _clean(candidate.get("plainLyrics"))
        if found["plain"] and found["synced"]:
            break
    return found


def fetch_lyrics_lyrics_ovh(artist: str, title: str) -> Optional[str]:
    # Public, no-key API. May fail for some songs.
    global _lyrics_ovh_failures
    if _lyrics_ovh_failures >= LYRICS_OVH_MAX_FAILURES:
        return None
    url = f"https://api.lyrics.ovh/v1/{quote(artist, safe='')}/{quote(title, safe='')}"
    try:
        resp = get_session().get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException:
        with _lyrics_ovh_lock:
            _lyrics_ovh_failures += 1
            if _lyrics_ovh_failures == LYRICS_OVH_MAX_FAILURES:
                logging.warning("⚠️  lyrics.ovh no responde; no se consultará más en esta ejecución.")
        return None
    with _lyrics_ovh_lock:
        _lyrics_ovh_failures = 0
    try:
        if resp.status_code != 200:
            return None
        return _clean(resp.json().get("lyrics"))
    except Exception:
        return None


def fetch_lyrics(artist: str, title: str, album: Optional[str],
                 duration: Optional[int] = None, need_plain: bool = True) -> dict:
    """Devuelve {'plain', 'synced', 'provider'}; plain/synced son None si no se encontraron."""
    found = fetch_lyrics_lrclib(artist, title, album, duration)
    provider = "lrclib" if found["plain"] or found["synced"] else None
    if not found["plain"] and found["synced"]:
        found["plain"] = synced_to_plain(found["synced"])
    # lyrics.ovh solo tiene letra plana: se usa de respaldo si aún hace falta
    if need_plain and not found["plain"]:
        found["plain"] = fetch_lyrics_lyrics_ovh(artist, title)
        if found["plain"]:
            provider = provider or "lyrics.ovh"
    return {**found, "provider": provider}


def lrc_path_for(mp3_path: str) -> str:
    return os.path.splitext(mp3_path)[0] + ".lrc"


def has_lrc_file(mp3_path: str) -> bool:
    path = lrc_path_for(mp3_path)
    return os.path.isfile(path) and os.path.getsize(path) > 0


def get_duration_seconds(mp3_path: str) -> Optional[int]:
    try:
        return round(MP3(mp3_path).info.length)
    except Exception:
        return None


def save_lrc_file(mp3_path: str, synced_lyrics: str) -> bool:
    """Guarda la letra sincronizada como '<nombre del mp3>.lrc' junto al mp3."""
    try:
        with open(lrc_path_for(mp3_path), "w", encoding="utf-8") as f:
            f.write(synced_lyrics.strip() + "\n")
        return True
    except OSError as e:
        logging.error(f"🚫 Error guardando .lrc de {os.path.basename(mp3_path)}: {e}")
        return False


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
        "lrc_written": False,
    }

    tags = get_id3_tags(mp3_path)
    has_plain = has_lyrics(tags)
    has_lrc = has_lrc_file(mp3_path)

    if has_plain and has_lrc:
        result["status"] = "already_has_lyrics"
        logging.info(f"✅ Ya contiene letra y .lrc: {filename}")
        return result

    title, artist, album = extract_title_artist_album(tags)
    if not title or not artist:
        result["status"] = "missing_tags"
        result["reason"] = "Faltan etiquetas ID3 requeridas (title/artist)"
        logging.warning(f"⚠️  Faltan etiquetas en {filename} (title/artist requeridos). Se omite.")
        return result

    logging.info(f"🔎 Buscando letra para: '{title}' - {artist}{f' | {album}' if album else ''}")
    found = fetch_lyrics(artist, title, album, get_duration_seconds(mp3_path),
                         need_plain=not has_plain)
    result["provider"] = found["provider"]
    time.sleep(SLEEP_BETWEEN_REQUESTS_SECONDS)

    # La letra incrustada que ya exista no se sobrescribe; solo se completa lo que falta
    plain_saved = False
    if not has_plain and found["plain"]:
        if not save_lyrics_to_mp3(mp3_path, found["plain"]):
            result["status"] = "save_failed"
            result["reason"] = "Error guardando ID3"
            return result
        plain_saved = True

    if not has_lrc and found["synced"]:
        result["lrc_written"] = save_lrc_file(mp3_path, found["synced"])

    if plain_saved or result["lrc_written"]:
        result["status"] = "updated"
        saved = " + ".join(part for part, done in (("letra", plain_saved), (".lrc", result["lrc_written"])) if done)
        logging.info(f"🎤 Guardado ({saved}): {filename}")
    elif has_plain:
        result["status"] = "already_has_lyrics"
        logging.info(f"✅ Ya contiene letra (sin versión sincronizada disponible): {filename}")
    else:
        result["status"] = "not_found"
        result["reason"] = "Letra no encontrada"
        logging.info(f"❌ Letra no encontrada: {filename}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Busca en lrclib.net la letra de los mp3 que aún no la tienen: "
                    "la incrusta en el mp3 y deja la sincronizada en un .lrc al lado.")
    parser.add_argument(
        "--workers", type=int, default=DEFAULT_WORKERS,
        help=f"Cantidad de canciones a procesar en paralelo (default: {DEFAULT_WORKERS}).")
    args = parser.parse_args()

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
        "lrc_written": 0,
    }

    # Cada mp3 lo toca un único hilo, así que no hay escrituras concurrentes
    # sobre un mismo archivo; los contadores se actualizan solo en este hilo.
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for res in pool.map(process_file, files):
            counters["processed"] += 1
            status = res.get("status")
            if status in counters:
                counters[status] += 1
            if res.get("lrc_written"):
                counters["lrc_written"] += 1

    logging.info("\n📊 Resumen:")
    logging.info(f"   Total procesados: {counters['processed']}")
    logging.info(f"   Ya tenían letra: {counters['already_has_lyrics']}")
    logging.info(f"   Actualizados: {counters['updated']}")
    logging.info(f"   Archivos .lrc creados: {counters['lrc_written']}")
    logging.info(f"   Faltan tags: {counters['missing_tags']}")
    logging.info(f"   No encontradas: {counters['not_found']}")
    logging.info(f"   Error guardando: {counters['save_failed']}")


if __name__ == "__main__":
    main()
