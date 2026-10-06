import argparse
import json
import os
import re
import time
import unicodedata

from constants import playlistIdForMusic, pathForMusic
from cleanPlaylist import COOKIES_FILE, build_ytmusic

# Resultados de búsqueda a revisar por consulta.
SEARCH_LIMIT = 20

# Errores seguidos al agregar tras los que se aborta (sesión caducada, rate
# limit, etc.) en vez de seguir martillando la API con el resto de la lista.
MAX_CONSECUTIVE_ERRORS = 5


FEAT_PATTERN = re.compile(r'\s*[\(\[](?:feat|ft)\.?\s+([^\)\]]+)[\)\]]', re.IGNORECASE)


def normalize(value):
    """Minúsculas, sin acentos ni puntuación y con espacios colapsados.

    YouTube Music escribe 'Carín León' o 'Sr. Santos' donde el json (o el tag
    ID3) dice 'Carin Leon' o 'SR SANTOS'; esas diferencias leves no deben
    impedir la coincidencia de título, artista ni álbum.
    """
    if not isinstance(value, str):
        return ''
    decomposed = unicodedata.normalize('NFKD', value.casefold())
    without_accents = ''.join(c for c in decomposed if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^\w\s]', ' ', without_accents).split())


def split_artists(artist):
    # Los canales autogenerados de YouTube añaden ' - Topic' al artista.
    cleaned = re.sub(r'\s+-\s+topic\b', '', artist or '', flags=re.IGNORECASE)
    parts = re.split(r',|&|\band\b|\by\b', cleaned, flags=re.IGNORECASE)
    return {normalize(part) for part in parts if normalize(part)}


def song_key(title, artist):
    """(título sin '(feat. X)', conjunto de artistas incluyendo los feat).

    La misma canción aparece como 'My Love' de 'Route 94 & Jess Glynne' en la
    playlist y como 'My Love (feat. Jess Glynne)' de 'Route 94' en la
    búsqueda; además el orden de los artistas no siempre coincide.
    """
    artists = split_artists(artist)
    for featured in FEAT_PATTERN.findall(title or ''):
        artists |= split_artists(featured)
    return normalize(FEAT_PATTERN.sub('', title or '')), frozenset(artists)


def get_artist_string(artists):
    # Mismo formato que DownloadMp3.get_artist_string, con el que se generó el json
    if not artists:
        return ''
    if len(artists) > 1:
        return ', '.join(artist['name'] for artist in artists[:-1]) + ' & ' + artists[-1]['name']
    return artists[0]['name']


def find_in_album(ytmusic, item, key, album):
    """Busca el álbum del item y, dentro de él, la canción. Devuelve el track o None."""
    query = f"{item.get('artist', '')} {item.get('album', '')}".strip()
    for result in ytmusic.search(query, filter='albums', limit=SEARCH_LIMIT):
        if normalize(result.get('title')) != album or not result.get('browseId'):
            continue
        for track in ytmusic.get_album(result['browseId']).get('tracks', []):
            if not track.get('videoId'):
                continue
            if song_key(track.get('title'), get_artist_string(track.get('artists'))) == key:
                return track
    return None


def find_match(ytmusic, item):
    """Busca la canción en YouTube Music.

    Devuelve (resultado, 'exacta' | 'parcial') o (None, None). 'exacta' es
    título + artista + álbum; 'parcial' es título + artista con otro álbum
    (la misma canción publicada en un single, recopilatorio o reedición).
    Se agotan las formas de dar con el álbum antes de aceptar una parcial.
    """
    key = song_key(item.get('title', ''), item.get('artist', ''))
    album = normalize(item.get('album', ''))

    queries = [f"{item.get('artist', '')} {item.get('title', '')} {item.get('album', '')}".strip()]
    without_album = f"{item.get('artist', '')} {item.get('title', '')}".strip()
    if without_album != queries[0]:
        queries.append(without_album)

    partial = None
    for query in queries:
        for result in ytmusic.search(query, filter='songs', limit=SEARCH_LIMIT):
            if not result.get('videoId'):
                continue
            if song_key(result.get('title'), get_artist_string(result.get('artists'))) != key:
                continue
            result_album = (result.get('album') or {}).get('name', '')
            if normalize(result_album) == album:
                return result, 'exacta'
            if partial is None:
                partial = result

    # La búsqueda de canciones suele devolver solo una edición de cada tema;
    # si no fue la del álbum pedido, se va a buscar el álbum directamente.
    if album:
        track = find_in_album(ytmusic, item, key, album)
        if track is not None:
            return track, 'exacta'

    if partial is not None:
        return partial, 'parcial'
    return None, None


def main():
    default_input = os.path.join(pathForMusic, 'playlist-192kbps.json')
    parser = argparse.ArgumentParser(
        description="Recorre un json de canciones, busca cada una en YouTube "
                    "Music y la agrega a la playlist playlistIdForMusic (constants.py)."
    )
    parser.add_argument("--input", default=default_input,
                        help=f"json a recorrer (por defecto {default_input})")
    parser.add_argument("--dry-run", action="store_true",
                        help="solo busca y muestra las coincidencias, sin agregar nada")
    parser.add_argument("--strict", action="store_true",
                        help="exigir que también coincida el álbum (descarta las parciales)")
    parser.add_argument("--limit", type=int,
                        help="procesar solo los primeros N items del json")
    parser.add_argument("--sleep", type=float, default=1.0,
                        help="segundos de espera entre canciones (por defecto 1)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"🚫 No existe el archivo {args.input}")
        return
    if not os.path.exists(COOKIES_FILE):
        print(f"🚫 Error: El archivo de cookies '{COOKIES_FILE}' no existe.")
        return

    with open(args.input, 'r') as f:
        items = json.load(f)
    if args.limit:
        items = items[:args.limit]

    playlist_id = str(playlistIdForMusic)
    path_not_found = os.path.splitext(args.input)[0] + '-not-found.json'

    try:
        ytmusic = build_ytmusic(COOKIES_FILE)
        print(f"👉 Checking playlist {playlist_id}")
        playlist = ytmusic.get_playlist(playlist_id, limit=None)
    except Exception as e:
        print(f"🚫 error getting playlist info: {e}")
        return

    # Lo que ya está en la playlist no se vuelve a agregar: permite relanzar
    # el script tras un corte sin duplicar canciones.
    in_playlist = {t['videoId'] for t in playlist.get('tracks', []) if t.get('videoId')}
    print(f"👉 playlist «{playlist.get('title', '')}»: {len(in_playlist)} items")
    print(f"👉 {len(items)} canciones por procesar"
          f"{' (dry-run)' if args.dry_run else ''} 🔥\n")

    added = 0
    already = 0
    partial_matches = 0
    not_found = []
    consecutive_errors = 0

    for index, item in enumerate(items, start=1):
        label = f"[{index}/{len(items)}] {item.get('artist', '')} - {item.get('title', '')}"

        try:
            match, kind = find_match(ytmusic, item)
        except Exception as e:
            print(f"🚫 {label}: error buscando: {e}")
            not_found.append(item)
            time.sleep(args.sleep)
            continue

        if match is None or (args.strict and kind != 'exacta'):
            print(f"❌ {label}: sin coincidencia")
            not_found.append(item)
            time.sleep(args.sleep)
            continue

        video_id = match['videoId']
        detail = ''
        if kind == 'parcial':
            partial_matches += 1
            detail = f" (álbum distinto: «{(match.get('album') or {}).get('name', '')}»)"

        if video_id in in_playlist:
            print(f"✅ {label}: ya está en la playlist{detail}")
            already += 1
            time.sleep(args.sleep)
            continue

        if args.dry_run:
            print(f"👉 {label}: se agregaría {video_id}{detail}")
            in_playlist.add(video_id)
            added += 1
            time.sleep(args.sleep)
            continue

        try:
            response = ytmusic.add_playlist_items(playlist_id, [video_id])
            status = response.get('status', '') if isinstance(response, dict) else str(response)
        except Exception as e:
            status = f"error: {e}"

        if 'SUCCEEDED' in status:
            print(f"➕ {label}: agregada{detail}")
            in_playlist.add(video_id)
            added += 1
            consecutive_errors = 0
        else:
            print(f"🚫 {label}: no se pudo agregar ({status or response})")
            not_found.append(item)
            consecutive_errors += 1
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                print(f"\n🚫 {MAX_CONSECUTIVE_ERRORS} errores seguidos al agregar; se aborta. "
                      "Revisa cookies.txt y vuelve a ejecutar: lo ya agregado se omite.")
                break
        time.sleep(args.sleep)

    with open(path_not_found, 'w') as f:
        json.dump(not_found, f, indent=2)

    verb = "se agregarían" if args.dry_run else "agregadas"
    print(f"\n✅ {added} {verb}, {already} ya estaban, {len(not_found)} sin agregar "
          f"({partial_matches} coincidencias con álbum distinto)")
    if not_found:
        print(f"   pendientes → {path_not_found}")


if __name__ == "__main__":
    main()
