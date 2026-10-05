import argparse
import os
from http.cookiejar import MozillaCookieJar

from ytmusicapi import YTMusic

from constants import playlistIdForMusic

COOKIES_FILE = "cookies.txt"

# Items por petición de borrado: lotes pequeños para que un fallo a mitad de
# camino no deje la playlist en un estado difícil de retomar.
BATCH_SIZE = 50


def build_ytmusic(cookies_file):
    """YTMusic autenticado a partir de un cookies.txt en formato Netscape."""
    jar = MozillaCookieJar(cookies_file)
    jar.load(ignore_discard=True, ignore_expires=True)
    cookies = {c.name: c.value for c in jar if c.domain.endswith("youtube.com")}

    if "__Secure-3PAPISID" not in cookies:
        raise RuntimeError(
            f"'{cookies_file}' no contiene la cookie __Secure-3PAPISID "
            "(¿se exportó con la sesión de YouTube iniciada?)")

    # ytmusicapi detecta la autenticación de navegador por la presencia de
    # SAPISIDHASH en 'authorization'; el valor real lo recalcula en cada
    # petición a partir de la cookie __Secure-3PAPISID.
    headers = {
        "cookie": "; ".join(f"{name}={value}" for name, value in cookies.items()),
        "authorization": "SAPISIDHASH placeholder",
        "x-goog-authuser": "0",
        "origin": "https://music.youtube.com",
    }
    return YTMusic(auth=headers)


def main():
    parser = argparse.ArgumentParser(
        description="Borra TODOS los items de la playlist playlistIdForMusic "
                    "(constants.py). No toca los mp3 ni playlist.json locales."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="solo muestra lo que se borraría, sin borrar nada")
    parser.add_argument("--yes", action="store_true",
                        help="no pedir confirmación antes de borrar")
    args = parser.parse_args()

    if not os.path.exists(COOKIES_FILE):
        print(f"🚫 Error: El archivo de cookies '{COOKIES_FILE}' no existe.")
        return

    playlist_id = str(playlistIdForMusic)

    try:
        ytmusic = build_ytmusic(COOKIES_FILE)
        print(f"👉 Checking playlist {playlist_id}")
        playlist = ytmusic.get_playlist(playlist_id, limit=None)
    except Exception as e:
        print(f"🚫 error getting playlist info: {e}")
        return

    tracks = playlist.get('tracks', [])
    print(f"👉 playlist «{playlist.get('title', '')}»: {len(tracks)} items")

    if not tracks:
        print("✅ La playlist ya está vacía.")
        return

    # setVideoId identifica al item dentro de la playlist y solo viene cuando
    # la sesión es la del dueño; sin él no hay forma de borrar el item.
    removable = [t for t in tracks if t.get('setVideoId') and t.get('videoId')]
    not_removable = [t for t in tracks if t not in removable]
    for track in not_removable:
        print(f"⚠️  no se puede borrar (sin setVideoId/videoId): {track.get('title')}")

    if not removable:
        print("🚫 Ningún item se puede borrar. ¿La sesión de cookies.txt es la "
              "dueña de la playlist?")
        return

    if args.dry_run:
        for track in removable:
            artists = ', '.join(a['name'] for a in track.get('artists') or [])
            print(f"   🗑️  {artists} - {track.get('title')}")
        print(f"\n(dry-run) se borrarían {len(removable)} items; no se borró nada.")
        return

    if not args.yes:
        answer = input(f"\n⚠️  Se van a borrar {len(removable)} items de la playlist "
                       f"«{playlist.get('title', '')}». Escribe 'borrar' para continuar: ")
        if answer.strip().lower() != 'borrar':
            print("⏭️  Cancelado, no se borró nada.")
            return

    removed = 0
    for start in range(0, len(removable), BATCH_SIZE):
        batch = removable[start:start + BATCH_SIZE]
        try:
            status = ytmusic.remove_playlist_items(playlist_id, batch)
        except Exception as e:
            print(f"🚫 error borrando items {start + 1}-{start + len(batch)}: {e}")
            break
        if status != 'STATUS_SUCCEEDED':
            print(f"🚫 respuesta inesperada borrando items "
                  f"{start + 1}-{start + len(batch)}: {status}")
            break
        removed += len(batch)
        print(f"🗑️  {removed}/{len(removable)} items borrados")

    if removed == len(removable) and not not_removable:
        print("✅ Playlist vacía.")
    else:
        print(f"⚠️  Se borraron {removed} de {len(tracks)} items; "
              "vuelve a ejecutar el script para reintentar el resto.")


if __name__ == "__main__":
    main()
