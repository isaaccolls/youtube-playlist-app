import os
import json
import re

from constants import pathForMusic


def sanitize_filename(name):
    return re.sub(r'[\/\\\:\*\?\"\<\>\|]', '_', name)


def main():
    # Carga el archivo playlist.json
    path_playlist = os.path.join(pathForMusic, 'playlist.json')
    path_file = pathForMusic

    if not os.path.exists(path_playlist):
        print(f"🚫 No existe el archivo {path_playlist}")
        return

    with open(path_playlist, 'r') as f:
        playlist_json = json.load(f)

    # Recolecta todos los archivos mp3 en la carpeta
    mp3_files = set(f for f in os.listdir(path_file)
                    if f.lower().endswith('.mp3'))

    # Para llevar registro de los archivos esperados
    expected_mp3_files = set()

    print("🔎 Verificando canciones del playlist.json...\n")
    for item in playlist_json:
        title = item.get('title', '')
        artist = item.get('artist', '')
        album = item.get('album', '')

        sanitized_title = sanitize_filename(title)
        sanitized_artist = sanitize_filename(artist)
        sanitized_album = sanitize_filename(album)
        album_part_for_file_name = f" - {sanitized_album}" if sanitized_album else ''
        sanitized_file_name = f"{sanitized_artist}{album_part_for_file_name} - {sanitized_title}"
        mp3_file_name = f"{sanitized_file_name}.mp3"
        expected_mp3_files.add(mp3_file_name)

        mp3_file_path = os.path.join(path_file, mp3_file_name)
        if mp3_file_name in mp3_files:
            print(f"✅ {mp3_file_name} existe.")
        else:
            print(f"❌ {mp3_file_name} NO existe.")

    print("\n🔎 Buscando archivos mp3 huérfanos (no registrados en playlist.json)...\n")
    orphan_files = mp3_files - expected_mp3_files
    if orphan_files:
        for orphan in orphan_files:
            print(f"⚠️  {orphan} no está registrado en playlist.json")
    else:
        print("✅ No hay archivos mp3 huérfanos.")


if __name__ == "__main__":
    main()
