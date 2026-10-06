#!/bin/bash
# Sincroniza la biblioteca con VLC en el iPhone (montado por gvfs vía AFC):
# borra del dispositivo los .mp3, .m3u y .lrc existentes y copia los de data/mp3.

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

SRC_DIR="/home/isaac/Projects/youtube-playlist-app/data/mp3"
DEST_DIR="/run/user/1000/gvfs/afc:host=00008101-000E382C2644001E,port=3/org.videolan.vlc-ios"

MAX_RETRIES=3

# Solo el primer nivel de cada carpeta; el resto del contenido de VLC no se toca.
list_media() {
  find "$1" -maxdepth 1 -type f -name "$2" -print0 | sort -z
}

count_media() {
  list_media "$1" "$2" | tr -cd '\0' | wc -c
}

# --- Comprobaciones previas: nada se borra si algo no está en orden ---

if [[ ! -d "$SRC_DIR" ]]; then
  echo "🚫 No existe el directorio de origen: $SRC_DIR"
  exit 1
fi

if [[ ! -d "$DEST_DIR" || ! -w "$DEST_DIR" ]]; then
  echo "🚫 No se puede acceder al destino: $DEST_DIR"
  echo "   ¿Está el iPhone conectado, desbloqueado y montado?"
  exit 1
fi

SRC_MP3=$(count_media "$SRC_DIR" '*.mp3')
SRC_LRC=$(count_media "$SRC_DIR" '*.lrc')
SRC_M3U=$(count_media "$SRC_DIR" '*.m3u')
TOTAL_FILES=$((SRC_MP3 + SRC_LRC + SRC_M3U))

if [[ $SRC_MP3 -eq 0 ]]; then
  echo "🚫 No hay archivos mp3 en $SRC_DIR; no se borra nada del dispositivo."
  exit 1
fi

echo "🎵 Archivos a copiar: $TOTAL_FILES ($SRC_MP3 mp3, $SRC_LRC lrc, $SRC_M3U m3u)"

# --- Fase 1: borrar del dispositivo ---

DEST_TOTAL=$(( $(count_media "$DEST_DIR" '*.mp3') + $(count_media "$DEST_DIR" '*.lrc') + $(count_media "$DEST_DIR" '*.m3u') ))
echo "🗑️  Borrando $DEST_TOTAL archivos (.mp3, .m3u, .lrc) del dispositivo..."

DELETED=0
DELETE_FAILED=0
for pattern in '*.mp3' '*.m3u' '*.lrc'; do
  while IFS= read -r -d '' file; do
    if rm -f -- "$file" && [[ ! -e "$file" ]]; then
      ((DELETED++))
    else
      echo "❌ No se pudo borrar: $(basename "$file")"
      ((DELETE_FAILED++))
    fi
  done < <(list_media "$DEST_DIR" "$pattern")
done
echo "🗑️  Borrados: $DELETED de $DEST_TOTAL"

if [[ $DELETE_FAILED -gt 0 ]]; then
  echo "🚫 Quedaron $DELETE_FAILED archivos sin borrar; se cancela la copia."
  exit 1
fi

# --- Fase 2: copiar al dispositivo ---

COPIED=0
FAILED=0
CURRENT=0

copy_file() {
  local file="$1"
  local name dest size attempt
  name=$(basename "$file")
  dest="$DEST_DIR/$name"
  size=$(stat -c %s -- "$file")

  for ((attempt = 1; attempt <= MAX_RETRIES; attempt++)); do
    # Sin -p: AFC no admite conservar permisos ni fechas
    if cp -- "$file" "$dest" && [[ "$(stat -c %s -- "$dest" 2>/dev/null)" == "$size" ]]; then
      return 0
    fi
    echo "❌ Error al copiar: $name - Reintento #$attempt"
    rm -f -- "$dest"
    sleep 2
  done
  return 1
}

# Las playlists van al final: así nunca apuntan a canciones que aún no se copiaron.
for pattern in '*.mp3' '*.lrc' '*.m3u'; do
  while IFS= read -r -d '' file; do
    ((CURRENT++))
    echo "🔢 [$CURRENT/$TOTAL_FILES] $(basename "$file")"
    if copy_file "$file"; then
      ((COPIED++))
    else
      echo "🚫 No se pudo copiar: $(basename "$file")"
      ((FAILED++))
    fi
  done < <(list_media "$SRC_DIR" "$pattern")
done

# --- Resumen ---

echo "----------------------------------------"
echo "🎉 Archivos copiados exitosamente: $COPIED de $TOTAL_FILES"
if [[ $FAILED -gt 0 ]]; then
  echo "⚠️  Fallaron $FAILED archivos; vuelve a ejecutar el script para reintentar."
  exit 1
fi
