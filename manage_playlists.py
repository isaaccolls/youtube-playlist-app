#!/usr/bin/env python3
"""Administrador interactivo de playlists M3U."""

import sys
import subprocess
import termios
import tty
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Config ---

DATA_DIR = Path(__file__).parent / "data" / "mp3"

GENRE_KEYS = {
    'a': 'classical',
    'b': 'bailoteo',
    'h': 'bachata',
    'c': 'cumbia',
    'd': 'bolero',
    'e': 'electro',
    'i': 'gaita',
    'j': 'jazz',
    'f': 'lofi',
    'l': 'llanera',
    'p': 'lollipop',
    'm': 'merengue',
    'r': 'rap',
    'g': 'reggae',
    'k': 'rock',
    's': 'salsa',
    'v': 'vallenato',
    'o': 'bossanova',
}

FFPROBE_WORKERS = 8

# --- ANSI ---

RESET  = '\033[0m'
BOLD   = '\033[1m'
DIM    = '\033[2m'
GREEN  = '\033[32m'
YELLOW = '\033[33m'
CYAN   = '\033[36m'
RED    = '\033[31m'

# --- M3U helpers ---

def playlist_path(name: str) -> Path:
    return DATA_DIR / f"{name}.m3u"


def parse_m3u(path: Path) -> list[tuple[str, int, str]]:
    """Return list of (filename, duration, title) from an m3u file."""
    if not path.exists():
        return []
    entries: list[tuple[str, int, str]] = []
    extinf: tuple[int, str] | None = None
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#EXTINF:'):
                rest = line[8:]
                dur_str, _, title = rest.partition(',')
                try:
                    extinf = (int(dur_str), title)
                except ValueError:
                    extinf = (0, rest)
            elif line and not line.startswith('#'):
                dur, title = extinf if extinf else (0, song_title(line))
                entries.append((line, dur, title))
                extinf = None
    return entries


def write_m3u(path: Path, entries: list[tuple[str, int, str]]) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for filename, duration, title in entries:
            f.write(f'#EXTINF:{duration},{title}\n{filename}\n')


def song_title(filename: str) -> str:
    """'Artist - Album - Title.mp3' → 'Artist - Title'."""
    name = Path(filename).stem
    parts = name.split(' - ', 2)
    return f"{parts[0]} - {parts[2]}" if len(parts) >= 3 else name


def get_duration(filepath: Path) -> int:
    try:
        r = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', str(filepath)],
            capture_output=True, text=True, timeout=10,
        )
        return int(float(r.stdout.strip()))
    except Exception:
        return 0

# --- Phase 1: Sync all.m3u ---

def sync_all() -> None:
    all_path = playlist_path('all')
    mp3_files = sorted(f.name for f in DATA_DIR.glob('*.mp3'))
    mp3_set = set(mp3_files)

    existing = parse_m3u(all_path)
    existing_map = {e[0]: (e[1], e[2]) for e in existing}

    stale   = {f for f in existing_map if f not in mp3_set}
    missing = [f for f in mp3_files if f not in existing_map]

    if not missing and not stale:
        print(f"  {GREEN}all.m3u ya sincronizado{RESET} ({len(mp3_files)} canciones)")
        return

    entries: dict[str, tuple[int, str]] = {f: v for f, v in existing_map.items() if f not in stale}

    if stale:
        print(f"  Eliminando {len(stale)} entradas obsoletas")

    if missing:
        print(f"  Agregando {len(missing)} canciones (obteniendo duraciones en paralelo)...")

        def fetch(fname: str) -> tuple[str, int, str]:
            return fname, get_duration(DATA_DIR / fname), song_title(fname)

        done = 0
        with ThreadPoolExecutor(max_workers=FFPROBE_WORKERS) as pool:
            for future in as_completed(pool.submit(fetch, f) for f in missing):
                fname, dur, title = future.result()
                entries[fname] = (dur, title)
                done += 1
                if done % 200 == 0 or done == len(missing):
                    pct = done * 100 // len(missing)
                    bar = '█' * (pct // 5) + '░' * (20 - pct // 5)
                    print(f"  [{bar}] {done}/{len(missing)} ({pct}%)   ", end='\r', flush=True)
        print()

    sorted_entries = [(f, entries[f][0], entries[f][1]) for f in sorted(entries)]
    write_m3u(all_path, sorted_entries)
    print(f"  {GREEN}all.m3u actualizado:{RESET} {len(sorted_entries)} canciones")

# --- Phase 2: Interactive classification ---

def get_char() -> str:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


class Player:
    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None

    def play(self, filepath: Path) -> None:
        self.stop()
        self._proc = subprocess.Popen(
            ['mpv', '--no-video', '--really-quiet', str(filepath)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None


def classify_songs() -> None:
    all_mp3s = sorted(f.name for f in DATA_DIR.glob('*.mp3'))

    # Load all genre playlists
    genre_entries: dict[str, list] = {}
    genre_sets:    dict[str, set]  = {}
    for name in GENRE_KEYS.values():
        rows = parse_m3u(playlist_path(name))
        genre_entries[name] = list(rows)
        genre_sets[name]    = {e[0] for e in rows}

    categorized   = set().union(*genre_sets.values())
    uncategorized = [f for f in all_mp3s if f not in categorized]

    if not uncategorized:
        print(f"  {GREEN}Todas las canciones ya están categorizadas.{RESET}")
        return

    total = len(uncategorized)
    print(f"\n  {YELLOW}{total}{RESET} canciones sin categorizar\n")

    key_help = '  '.join(f"{CYAN}[{k}]{RESET}={v}" for k, v in sorted(GENRE_KEYS.items()))
    print(f"  Géneros: {key_help}")
    print(f"  {DIM}[Enter/Espacio] avanzar  [q] guardar y salir{RESET}\n")
    print(f"  {DIM}Selecciona uno o varios géneros y presiona Enter para confirmar.{RESET}\n")
    print('─' * 60)

    player = Player()
    saved  = False

    def save_all() -> None:
        for name, entries in genre_entries.items():
            write_m3u(playlist_path(name), entries)

    def render_selection(selection: set[str]) -> None:
        if selection:
            sel_str = ', '.join(f"{GREEN}{g}{RESET}" for g in sorted(selection))
            print(f"  → {sel_str}          ", end='\r', flush=True)
        else:
            print(f"  {DIM}(sin género seleccionado)    {RESET}", end='\r', flush=True)

    try:
        for idx, filename in enumerate(uncategorized, 1):
            title    = song_title(filename)
            selection: set[str] = set()

            print(f"\n{BOLD}[{idx}/{total}]{RESET}  {title}")
            print(f"  {DIM}{filename}{RESET}")

            player.play(DATA_DIR / filename)
            render_selection(selection)

            while True:
                ch = get_char()

                if ch in ('\r', '\n', ' '):
                    print()
                    if selection:
                        for genre in sorted(selection):
                            if filename not in genre_sets[genre]:
                                dur = get_duration(DATA_DIR / filename)
                                genre_entries[genre].append((filename, dur, title))
                                genre_sets[genre].add(filename)
                        added_str = ', '.join(sorted(selection))
                        print(f"  {GREEN}Agregado a:{RESET} {added_str}")
                    else:
                        print(f"  {DIM}Saltada{RESET}")
                    break

                elif ch == 'q':
                    print(f"\n\n  Guardando y saliendo...")
                    player.stop()
                    save_all()
                    saved = True
                    print(f"  {GREEN}Playlists guardadas.{RESET}")
                    return

                elif ch == '\x03':  # Ctrl+C
                    raise KeyboardInterrupt

                elif ch in GENRE_KEYS:
                    genre = GENRE_KEYS[ch]
                    if genre in selection:
                        selection.discard(genre)
                    else:
                        selection.add(genre)
                    render_selection(selection)

    except KeyboardInterrupt:
        print(f"\n\n  Interrumpido.")
    finally:
        player.stop()
        if not saved:
            save_all()
            print(f"  {GREEN}Playlists guardadas.{RESET}")

    print(f"\n  {GREEN}Clasificación completada.{RESET}")

# --- Main ---

def main() -> None:
    if not DATA_DIR.exists():
        print(f"{RED}Error:{RESET} No se encontró el directorio {DATA_DIR}")
        sys.exit(1)

    if not sys.stdin.isatty():
        print(f"{RED}Error:{RESET} Este script requiere un terminal interactivo.")
        sys.exit(1)

    print(f"\n{BOLD}=== Administrador de Playlists M3U ==={RESET}")
    print(f"  Directorio: {DATA_DIR}\n")

    print(f"{BOLD}Fase 1:{RESET} Sincronizando all.m3u...")
    sync_all()

    print(f"\n{BOLD}Fase 2:{RESET} Clasificación interactiva")
    classify_songs()
    print()


if __name__ == '__main__':
    main()
