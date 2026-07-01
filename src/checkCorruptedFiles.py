import argparse
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from constants import pathForMusic
from checkFiles import sanitize_filename, build_filename

# Duración real vs. declarada: si faltan más de esto (en % y en segundos a la
# vez) lo tratamos como una descarga/conversión truncada, no como un redondeo
# normal del encoder (el delay/padding típico de LAME son ~0.05s).
TRUNCATION_REL_THRESHOLD = 0.05
TRUNCATION_ABS_THRESHOLD = 2.0

FFMPEG_ERR_DETECT = "+crccheck+bitstream+buffer+careful+compliant+aggressive"


def get_declared_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def get_actual_duration(path):
    """Decodifica el mp3 completo y devuelve (segundos_reales, error)."""
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-xerror",
         "-err_detect", FFMPEG_ERR_DETECT,
         "-i", path, "-f", "null", "-",
         "-progress", "pipe:1", "-nostats"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None, result.stderr.strip() or "ffmpeg no pudo decodificar el archivo"

    last_out_time_ms = 0
    for line in result.stdout.splitlines():
        if line.startswith("out_time_ms="):
            try:
                last_out_time_ms = int(line.split("=", 1)[1])
            except ValueError:
                pass
    return last_out_time_ms / 1_000_000.0, None


def check_corruption(filename, path_file):
    """Devuelve un motivo de corrupción (str) o None si el archivo está bien."""
    path = os.path.join(path_file, filename)

    declared = get_declared_duration(path)
    actual, error = get_actual_duration(path)

    if error:
        return f"error de decodificación ({error})"
    if actual is None or actual <= 0:
        return "duración decodificada es 0 (archivo vacío o ilegible)"
    if declared is not None and declared > 0:
        missing = declared - actual
        if missing > TRUNCATION_ABS_THRESHOLD and missing / declared > TRUNCATION_REL_THRESHOLD:
            return f"archivo truncado (declarado {declared:.1f}s, decodificado {actual:.1f}s)"

    return None


def filename_for_item(item):
    title = sanitize_filename(item.get("title", ""))
    artist = sanitize_filename(item.get("artist", ""))
    album = sanitize_filename(item.get("album", ""))
    return f"{build_filename(artist, album, title)}.mp3"


def build_filename_index(playlist_json):
    """Mapea nombre_de_archivo.mp3 -> item de playlist.json."""
    return {filename_for_item(item): item for item in playlist_json}


def main():
    parser = argparse.ArgumentParser(
        description="Detecta mp3 corruptos (truncados/ilegibles) en data/mp3/.")
    parser.add_argument(
        "--delete", action="store_true", default=False,
        help="Borra los mp3 corruptos y su entrada en playlist.json. "
             "Por defecto solo se listan.")
    parser.add_argument(
        "--workers", type=int, default=8,
        help="Cantidad de archivos a analizar en paralelo (default: 8).")
    args = parser.parse_args()

    path_playlist = os.path.join(pathForMusic, "playlist.json")
    path_file = pathForMusic

    if not os.path.exists(path_playlist):
        print(f"🚫 No existe el archivo {path_playlist}")
        return

    with open(path_playlist, "r") as f:
        playlist_json = json.load(f)

    filename_index = build_filename_index(playlist_json)

    mp3_files = sorted(f for f in os.listdir(path_file) if f.lower().endswith(".mp3"))
    print(f"🔎 Analizando {len(mp3_files)} archivos mp3 en busca de corrupción real "
          f"(truncados / ilegibles)...\n")

    corrupted = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(check_corruption, filename, path_file): filename
            for filename in mp3_files
        }
        done = 0
        total = len(futures)
        for future in as_completed(futures):
            filename = futures[future]
            done += 1
            reason = future.result()
            if reason:
                corrupted[filename] = reason
                print(f"❌ [{done}/{total}] {filename} -> {reason}")
            elif done % 200 == 0:
                print(f"…procesados {done}/{total}")

    if not corrupted:
        print("\n✅ No se encontraron archivos mp3 corruptos.")
        return

    print(f"\n🚨 {len(corrupted)} archivo(s) corrupto(s) detectado(s):\n")
    for filename, reason in corrupted.items():
        in_playlist = "sí" if filename in filename_index else "no (huérfano)"
        print(f" - {filename}\n   motivo: {reason}\n   en playlist.json: {in_playlist}")

    if not args.delete:
        print("\nℹ️  Modo listado (--delete no especificado): no se borró nada.")
        return

    print("\n🗑️  Borrando archivos corruptos y sus entradas en playlist.json...")
    remaining_playlist = [
        item for item in playlist_json
        if filename_for_item(item) not in corrupted
    ]
    removed_from_playlist = len(playlist_json) - len(remaining_playlist)

    for filename in corrupted:
        file_path = os.path.join(path_file, filename)
        try:
            os.remove(file_path)
            print(f"   🗑️  borrado {filename}")
        except OSError as exc:
            print(f"   ⚠️  no se pudo borrar {filename}: {exc}")

    with open(path_playlist, "w") as f:
        json.dump(remaining_playlist, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Listo. {removed_from_playlist} entrada(s) eliminada(s) de playlist.json, "
          f"{len(corrupted)} archivo(s) físico(s) borrado(s).")


if __name__ == "__main__":
    main()
