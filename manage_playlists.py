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
    't': 'tambor',
    'v': 'vallenato',
    'o': 'bossanova',
    'x': 'mariachi',
}

FFPROBE_WORKERS = 8
COUNT_COLUMNS = 3       # columnas del resumen de canciones por playlist
MAX_ISSUES_SHOWN = 20   # problemas listados por playlist antes de resumir

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


def playlist_names() -> list[str]:
    """'all' primero; luego los géneros y cualquier otro .m3u presente en disco."""
    names = set(GENRE_KEYS.values()) | {p.stem for p in DATA_DIR.glob('*.m3u')}
    names.discard('all')
    return ['all', *sorted(names)]


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


def song_title_with_album(filename: str) -> str:
    """'Artist - Album - Title.mp3' → 'Artist - Album - Title' (para mostrar en pantalla)."""
    name = Path(filename).stem
    parts = name.split(' - ', 2)
    return f"{parts[0]} - {parts[1]} - {parts[2]}" if len(parts) >= 3 else name


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


def probe_durations(filenames: list[str]) -> dict[str, int]:
    """Duración de cada mp3 según ffprobe (0 si no pudo leerlo), en paralelo y con barra de progreso."""
    durations: dict[str, int] = {}
    if not filenames:
        return durations

    def fetch(fname: str) -> tuple[str, int]:
        return fname, get_duration(DATA_DIR / fname)

    total = len(filenames)
    with ThreadPoolExecutor(max_workers=FFPROBE_WORKERS) as pool:
        for future in as_completed(pool.submit(fetch, f) for f in filenames):
            fname, dur = future.result()
            durations[fname] = dur
            done = len(durations)
            if done % 200 == 0 or done == total:
                pct = done * 100 // total
                bar = '█' * (pct // 5) + '░' * (20 - pct // 5)
                print(f"  [{bar}] {done}/{total} ({pct}%)   ", end='\r', flush=True)
    print()
    return durations

# --- Startup: Song counts ---

def show_counts() -> None:
    names = playlist_names()
    width = max(len(n) for n in names)
    cells = []
    for name in names:
        try:
            count = str(len(parse_m3u(playlist_path(name))))
        except OSError:
            count = '?'
        cells.append(f"{CYAN}{name:<{width}}{RESET} {count:>5}")
    for i in range(0, len(cells), COUNT_COLUMNS):
        print('  ' + '    '.join(cells[i:i + COUNT_COLUMNS]))

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

        for fname, dur in probe_durations(missing).items():
            entries[fname] = (dur, song_title(fname))

    sorted_entries = [(f, entries[f][0], entries[f][1]) for f in sorted(entries)]
    write_m3u(all_path, sorted_entries)
    print(f"  {GREEN}all.m3u actualizado:{RESET} {len(sorted_entries)} canciones")

# --- Phase 1b: Verify playlist integrity ---

# Caracteres reservados en URI/MRL: algunos reproductores (notablemente VLC
# iOS) resuelven las rutas de un m3u como Media Resource Locators en vez de
# rutas de texto planas. Un '#' sin escapar se interpreta como delimitador
# de fragmento y un '%' como inicio de un escape porcentual — ambos cortan
# o corrompen la resolución de esa entrada en adelante, y a diferencia de
# VLC desktop (que se recupera), VLC iOS aborta el resto del import.
RISKY_CHARS = '#%?'


# (línea, es_error, mensaje); línea 0 = problema del archivo completo
Issue = tuple[int, bool, str]


def check_m3u(path: Path, disk: dict[str, int], durations: dict[str, int] | None = None) -> list[Issue]:
    """Valida un m3u línea a línea contra el formato que escribe write_m3u().

    Lee los bytes crudos en vez de usar parse_m3u(), que es tolerante a
    propósito (ignora lo que no entiende y reemplaza bytes inválidos) y por
    lo tanto oculta justo los daños que aquí se quieren detectar.

    `disk` mapea nombre de mp3 → tamaño en bytes. `durations` mapea nombre de
    mp3 → duración real según ffprobe (0 si no pudo leerlo); si se pasa, se
    comprueba además que cada mp3 sea legible y que su #EXTINF no haya
    quedado desfasado (p. ej. tras reemplazar el mp3 por otra descarga).
    """
    issues: list[Issue] = []

    def error(num: int, msg: str) -> None:
        issues.append((num, True, msg))

    def warn(num: int, msg: str) -> None:
        issues.append((num, False, msg))

    try:
        raw = path.read_bytes()
    except OSError as e:
        error(0, f"no se pudo leer el archivo: {e.strerror}")
        return issues

    if raw.startswith(b'\xef\xbb\xbf'):
        warn(0, "BOM UTF-8 al inicio del archivo")
        raw = raw[3:]
    if b'\r' in raw:
        warn(0, "saltos de línea CRLF (se esperan LF)")
    if raw and not raw.endswith(b'\n'):
        warn(0, "falta el salto de línea final")

    lines = raw.split(b'\n')
    if lines[-1] == b'':
        lines.pop()
    if not lines:
        error(0, "archivo vacío, falta la cabecera #EXTM3U")
    elif lines[0].strip() != b'#EXTM3U':
        error(1, "falta la cabecera #EXTM3U")

    # #EXTINF a la espera de su archivo:
    # (línea, título o None si es inválido, duración o None si es inválida o <= 0)
    pending: tuple[int, str | None, int | None] | None = None
    seen: dict[str, int] = {}

    for num, raw_line in enumerate(lines, 1):
        try:
            text = raw_line.decode('utf-8')
        except UnicodeDecodeError:
            error(num, "codificación UTF-8 inválida")
            text = raw_line.decode('utf-8', errors='replace')
        line = text.strip()

        if num == 1 and line == '#EXTM3U':
            continue
        if not line:
            warn(num, "línea en blanco")
            continue
        if line != text.rstrip('\r'):
            warn(num, "espacios al inicio o al final de la línea")

        if line.startswith('#EXTINF:'):
            if pending is not None:
                error(pending[0], "#EXTINF sin archivo a continuación")
            dur_str, sep, title = line[8:].partition(',')
            extinf_dur: int | None = None
            if not sep:
                error(num, f"#EXTINF malformado (se espera '#EXTINF:<segundos>,<título>'): {line}")
            else:
                try:
                    if int(dur_str) <= 0:
                        warn(num, f"duración {dur_str} en #EXTINF (¿ffprobe no pudo leer el mp3?)")
                    else:
                        extinf_dur = int(dur_str)
                except ValueError:
                    error(num, f"#EXTINF con duración no numérica: {line}")
                if not title:
                    error(num, "#EXTINF con título vacío")
            pending = (num, title or None, extinf_dur)

        elif line.startswith('#'):
            # write_m3u() la descartaría al guardar
            warn(num, f"línea de comentario/directiva no reconocida: {line}")

        else:
            if pending is None:
                error(num, f"entrada sin #EXTINF previo: {line}")
            if line in seen:
                error(num, f"entrada duplicada (ya está en la línea {seen[line]}): {line}")
            else:
                seen[line] = num
            if '/' in line:
                error(num, f"entrada con ruta, se espera sólo el nombre del archivo: {line}")
            elif line not in disk:
                error(num, f"el archivo no existe en disco: {line}")
            elif disk[line] == 0:
                error(num, f"el archivo mp3 está vacío (0 bytes): {line}")
            elif durations is not None and durations.get(line, 0) <= 0:
                error(num, f"ffprobe no pudo leer el mp3 (¿archivo corrupto?): {line}")
            elif pending is not None:
                if pending[1] not in (None, song_title(line)):
                    # Típico de un par #EXTINF/archivo desalineado tras una edición manual
                    warn(pending[0], f"el título del #EXTINF no corresponde al archivo «{line}»: {pending[1]}")
                if durations is not None and pending[2] not in (None, durations[line]):
                    # Típico de un mp3 reemplazado (o truncado) después de haber sido agregado
                    warn(pending[0], f"duración {pending[2]} en #EXTINF, pero ffprobe reporta "
                                     f"{durations[line]} para «{line}»")
            pending = None

    if pending is not None:
        error(pending[0], "#EXTINF sin archivo a continuación")

    return issues


def verify_playlists() -> bool:
    """Verifica la integridad de todas las playlists y reporta lo que encuentre,
    además de los archivos con caracteres riesgosos para un import de m3u como URI.

    Devuelve False si alguna playlist tiene errores (los avisos no cuentan).

    sync_all() sólo reconcilia all.m3u; si un mp3 se renombra o se
    reemplaza después de haber sido clasificado, la entrada queda huérfana
    en su playlist de género (invisible para os.path.exists) y reproductores
    estrictos (p. ej. VLC iOS) pueden abortar la carga del resto de la
    playlist al toparse con ella en vez de saltarla.
    """
    disk = {f.name: f.stat().st_size for f in DATA_DIR.glob('*.mp3')}
    print(f"  Leyendo {len(disk)} mp3 con ffprobe...")
    durations = probe_durations(sorted(f for f, size in disk.items() if size > 0))
    names = playlist_names()
    total_errors = total_warnings = affected = 0

    for name in names:
        path = playlist_path(name)
        if not path.exists():
            issues: list[Issue] = [(0, False, "la playlist no existe en disco")]
        else:
            issues = check_m3u(path, disk, durations)
            if name != 'all' and name not in GENRE_KEYS.values():
                issues.append((0, False, "playlist sin tecla en GENRE_KEYS (el script no la administra)"))
        if not issues:
            continue

        # Errores primero, para que el recorte de MAX_ISSUES_SHOWN nunca los oculte tras avisos
        issues.sort(key=lambda issue: (not issue[1], issue[0]))
        errors = sum(1 for _, is_error, _ in issues if is_error)
        warnings = len(issues) - errors
        total_errors += errors
        total_warnings += warnings
        affected += 1

        print(f"  {RED if errors else YELLOW}{name}.m3u{RESET}: {errors} error(es), {warnings} aviso(s)")
        for num, is_error, msg in issues[:MAX_ISSUES_SHOWN]:
            tag = f"{RED}error{RESET}" if is_error else f"{YELLOW}aviso{RESET}"
            where = f"línea {num}" if num else "archivo"
            print(f"    {tag} {DIM}{where}:{RESET} {msg}")
        if len(issues) > MAX_ISSUES_SHOWN:
            print(f"    {DIM}… y {len(issues) - MAX_ISSUES_SHOWN} más{RESET}")

    if total_errors:
        print(f"  {RED}{total_errors} error(es){RESET} y {total_warnings} aviso(s) "
              f"en {affected} de {len(names)} playlists")
        print(f"  {DIM}Corrige las entradas indicadas (o el mp3 renombrado/eliminado) y vuelve a correr este script.{RESET}")
    elif total_warnings:
        print(f"  {GREEN}Playlists sin errores{RESET} ({len(names)} verificadas), "
              f"{YELLOW}{total_warnings} aviso(s){RESET} en {affected}")
    else:
        print(f"  {GREEN}Playlists OK{RESET} ({len(names)} verificadas, sin errores ni avisos)")

    risky = sorted(f for f in disk if any(c in f for c in RISKY_CHARS))
    if risky:
        print(f"  {RED}{len(risky)} archivo(s) con carácter riesgoso para import de m3u{RESET} ({RISKY_CHARS}):")
        for f in risky:
            print(f"    {YELLOW}{f}{RESET}")
        print(f"  {DIM}Renombra el archivo (quitando {RISKY_CHARS}) y vuelve a correr este script para propagar el cambio.{RESET}")
    else:
        print(f"  {GREEN}Sin caracteres riesgosos ({RISKY_CHARS}) en nombres de archivo{RESET}")

    return total_errors == 0

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

            print(f"\n{BOLD}[{idx}/{total}]{RESET}  {song_title_with_album(filename)}")
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

    print(f"{BOLD}Canciones por playlist:{RESET}")
    show_counts()

    print(f"\n{BOLD}Fase 1:{RESET} Sincronizando all.m3u...")
    sync_all()

    print(f"\n{BOLD}Fase 1b:{RESET} Verificando integridad de playlists...")
    if not verify_playlists():
        # La fase 2 reescribe las playlists de género al guardar; se pide
        # confirmación para que el reporte no pase desapercibido antes de eso.
        print(f"\n  {RED}Se detectaron errores de integridad.{RESET} "
              f"{DIM}[Enter/Espacio] continuar de todos modos  [q] salir{RESET}")
        while (ch := get_char()) not in ('\r', '\n', ' '):
            if ch in ('q', '\x03'):
                sys.exit(1)

    print(f"\n{BOLD}Fase 2:{RESET} Clasificación interactiva")
    classify_songs()
    print()


if __name__ == '__main__':
    main()
