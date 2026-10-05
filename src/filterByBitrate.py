import argparse
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

from constants import pathForMusic
from checkFiles import sanitize_filename, build_filename


def get_bitrate_kbps(path):
    """Bitrate del stream de audio en kb/s (como lo muestra ffprobe), o None."""
    # Se usa el bitrate del stream y no el del contenedor (format=bit_rate):
    # este último incluye la carátula embebida y los tags ID3, por lo que un
    # mp3 de 192 kb/s aparece como 192.3, 192.6, etc.
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=bit_rate",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return int(result.stdout.strip()) // 1000
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Genera un json con las canciones de playlist.json cuyo "
                    "bitrate (según ffprobe) coincide con el indicado."
    )
    parser.add_argument("--bitrate", type=int, default=192,
                        help="bitrate a buscar en kb/s (por defecto 192)")
    parser.add_argument("--output",
                        help="ruta del json de salida "
                             "(por defecto data/mp3/playlist-<bitrate>kbps.json)")
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 4,
                        help="procesos ffprobe en paralelo")
    args = parser.parse_args()

    path_playlist = os.path.join(pathForMusic, 'playlist.json')
    path_output = args.output or os.path.join(
        pathForMusic, f'playlist-{args.bitrate}kbps.json')

    if not os.path.exists(path_playlist):
        print(f"🚫 No existe el archivo {path_playlist}")
        return

    with open(path_playlist, 'r') as f:
        playlist_json = json.load(f)

    def probe(item):
        sanitized_file_name = build_filename(
            sanitize_filename(item.get('artist', '')),
            sanitize_filename(item.get('album', '')),
            sanitize_filename(item.get('title', '')),
        )
        mp3_file_name = f"{sanitized_file_name}.mp3"
        mp3_file_path = os.path.join(pathForMusic, mp3_file_name)
        if not os.path.exists(mp3_file_path):
            return mp3_file_name, 'missing'
        return mp3_file_name, get_bitrate_kbps(mp3_file_path)

    print(f"🔎 Buscando canciones a {args.bitrate} kb/s "
          f"entre {len(playlist_json)} entradas...\n")

    matches = []
    missing = 0
    unreadable = 0
    # pool.map conserva el orden de playlist.json en el json resultante
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for item, (mp3_file_name, bitrate) in zip(playlist_json, pool.map(probe, playlist_json)):
            if bitrate == 'missing':
                print(f"❌ {mp3_file_name} NO existe.")
                missing += 1
            elif bitrate is None:
                print(f"⚠️  {mp3_file_name}: ffprobe no pudo leer el bitrate.")
                unreadable += 1
            elif bitrate == args.bitrate:
                matches.append(item)

    with open(path_output, 'w') as f:
        json.dump(matches, f, indent=2)

    print(f"\n✅ {len(matches)} de {len(playlist_json)} canciones a "
          f"{args.bitrate} kb/s → {path_output}")
    if missing or unreadable:
        print(f"   ({missing} sin archivo, {unreadable} ilegibles: no se incluyeron)")


if __name__ == "__main__":
    main()
