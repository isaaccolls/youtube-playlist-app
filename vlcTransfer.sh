#!/bin/bash

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

MP3_DIR="/home/isaac/Projects/youtube-playlist-app/data/mp3"
TEMP_DIR="/home/isaac/Projects/youtube-playlist-app/data/temporal"
UPLOAD_URL="http://192.168.7.247:53497/upload.json"

# Contar archivos mp3 detectados
TOTAL_FILES=$(find "$MP3_DIR" -maxdepth 1 -type f -name '*.mp3' | wc -l)
echo "🎵 Archivos mp3 detectados para copiar: $TOTAL_FILES"

COPIED=0
CURRENT=1

find "$MP3_DIR" -maxdepth 1 -type f -name '*.mp3' -print0 | while IFS= read -r -d '' file; do
  echo "🔢 Copiando canción $CURRENT de $TOTAL_FILES"
  echo "exitosamente copiados: $COPIED de $TOTAL_FILES"
  if [[ -r "$file" ]]; then
    temp_file=$(mktemp "$TEMP_DIR/upload_XXXXXX.mp3")
    cp "$file" "$temp_file"
    echo "🚀 Upload: $temp_file (original: $(basename "$file"))"
    echo -n "HEX: "
    echo -n "$temp_file" | xxd
    ls -l "$temp_file"
    if [[ -r "$temp_file" ]]; then
      RETRY=1
      while true; do
        LC_ALL=en_US.UTF-8 curl -F "files[]=@${temp_file}" -- "$UPLOAD_URL"
        CURL_EXIT=$?
        if [[ $CURL_EXIT -eq 0 ]]; then
          echo "✅ Uploaded: $file"
          ((COPIED++))
          break
        else
          echo "❌ Error al subir: $file (curl exit code: $CURL_EXIT) - Reintento #$RETRY"
          sleep 2
          ((RETRY++))
        fi
      done
      rm -f "$temp_file"
    else
      echo "❌ Archivo temporal no legible: $temp_file"
      rm -f "$temp_file"
    fi
  else
    echo "❌ No se puede leer el archivo: $file"
  fi
  echo "----------------------------------------"
  ((CURRENT++))
done

# Mostrar resumen al finalizar
echo "🎉 Archivos copiados exitosamente: $COPIED de $TOTAL_FILES"
