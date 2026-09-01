import argparse
import json
import os

import eyed3

from constants import pathForMusic, pathForMusicManual
from checkFiles import sanitize_filename, build_filename


class SkipFile(Exception):
    """Señal para omitir el archivo actual durante la edición interactiva."""


def prompt_field(label, current, required=True):
    hint = f" [{current}]" if current else ""
    while True:
        raw = input(f"   {label}{hint}: ").strip()
        if raw.lower() == 'skip':
            raise SkipFile()
        if raw == '':
            value = current
        elif raw == '-':
            value = ''
        else:
            value = raw
        if value or not required:
            return value
        print("   ⚠️ este campo es obligatorio (o escribe 'skip' para omitir el archivo).")


def normalize_cover_images(tag):
    """Fuerza cualquier imagen embebida a picture_type 3 (front cover),
    igual que DownloadMp3.download_audio al guardar el thumbnail descargado."""
    changed = 0
    for image in list(tag.images):
        if image.picture_type != 3:
            tag.images.set(3, image.image_data, image.mime_type, description=image.description)
            changed += 1
    return changed


def is_duplicate(title, artist, album, playlist_json):
    def normalize(value):
        return value.strip().lower() if isinstance(value, str) else ''
    return any(
        normalize(existing['title']) == normalize(title) and
        normalize(existing['artist']) == normalize(artist) and
        normalize(existing['album']) == normalize(album)
        for existing in playlist_json
    )


def process_file(filename, path_manual, path_music, playlist_json, dry_run):
    src_path = os.path.join(path_manual, filename)

    audiofile = eyed3.load(src_path)
    if audiofile is None:
        print(f"🚫 {filename}: no se pudo leer como mp3 válido, se omite.")
        return None

    if audiofile.tag is None:
        audiofile.initTag()

    current_title = audiofile.tag.title or ''
    current_artist = audiofile.tag.artist or ''
    current_album = audiofile.tag.album or ''

    print(f"\n📀 {filename}")
    print(f"   Título actual:  {current_title or '(vacío)'}")
    print(f"   Artista actual: {current_artist or '(vacío)'}")
    print(f"   Álbum actual:   {current_album or '(vacío)'}")
    print("   (Enter = mantener, '-' = dejar vacío, 'skip' = omitir este archivo)")

    try:
        title = prompt_field("Título", current_title)
        artist = prompt_field("Artista", current_artist)
        album = prompt_field("Álbum (opcional)", current_album, required=False)
    except SkipFile:
        print(f"⏭️  {filename} omitido por el usuario.")
        return None

    if is_duplicate(title, artist, album, playlist_json):
        print(f"✅ '{title}' de '{artist}' ya está en playlist.json, se omite.")
        return None

    sanitized_title = sanitize_filename(title)
    sanitized_artist = sanitize_filename(artist)
    sanitized_album = sanitize_filename(album)
    sanitized_file_name = build_filename(sanitized_artist, sanitized_album, sanitized_title)
    mp3_file_name = f"{sanitized_file_name}.mp3"
    dest_path = os.path.join(path_music, mp3_file_name)

    if os.path.exists(dest_path):
        print(f"🚫 {mp3_file_name} ya existe en {path_music}, se omite {filename} para no sobrescribir.")
        return None

    images_to_fix = sum(1 for image in audiofile.tag.images if image.picture_type != 3)

    if dry_run:
        cover_note = f", {images_to_fix} imagen(es) a normalizar a tipo 3" if images_to_fix else ""
        print(f"🔎 [dry-run] {filename} -> {mp3_file_name} "
              f"(título='{title}', artista='{artist}', álbum='{album}'{cover_note})")
        return None

    audiofile.tag.title = title
    audiofile.tag.artist = artist
    audiofile.tag.album = album
    if images_to_fix:
        normalize_cover_images(audiofile.tag)
        print(f"   🖼️  {images_to_fix} imagen(es) normalizada(s) a tipo 3 (front cover).")
    audiofile.tag.save()

    os.replace(src_path, dest_path)
    print(f"✅ {filename} -> {mp3_file_name}")

    return {'title': title, 'artist': artist, 'album': album}


def main():
    parser = argparse.ArgumentParser(
        description="Normaliza tags ID3 y nombre de archivo de mp3s descargados "
                     "manualmente en data/mp3-manual/, y los integra a data/mp3/.")
    parser.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Solo muestra qué se haría, sin mover archivos ni escribir tags/playlist.json.")
    args = parser.parse_args()

    path_manual = pathForMusicManual
    path_music = pathForMusic
    path_playlist = os.path.join(path_music, 'playlist.json')

    if not os.path.exists(path_manual):
        print(f"🚫 No existe el directorio {path_manual}")
        return

    if not os.path.exists(path_playlist):
        print(f"🚫 No existe el archivo {path_playlist}")
        return

    with open(path_playlist, 'r') as f:
        playlist_json = json.load(f)

    mp3_files = sorted(
        f for f in os.listdir(path_manual) if f.lower().endswith('.mp3'))

    if not mp3_files:
        print(f"✅ No hay archivos mp3 en {path_manual}")
        return

    print(f"👉 {len(mp3_files)} archivo(s) mp3 encontrados en {path_manual}")
    if args.dry_run:
        print("🔎 Modo dry-run: no se moverá ningún archivo ni se escribirá playlist.json.")

    imported = 0
    skipped = 0

    try:
        for filename in mp3_files:
            item = process_file(filename, path_manual, path_music, playlist_json, args.dry_run)
            if item is None:
                skipped += 1
                continue
            imported += 1
            if not args.dry_run:
                playlist_json.append(item)
                with open(path_playlist, 'w') as f:
                    json.dump(playlist_json, f, indent=2)
    except KeyboardInterrupt:
        print("\n🚫 Interrumpido por el usuario.")

    print(f"\n📊 Resumen: {imported} importado(s), {skipped} omitido(s).")


if __name__ == "__main__":
    main()
