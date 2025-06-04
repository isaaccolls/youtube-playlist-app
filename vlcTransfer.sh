#!/bin/bash

MP3_DIR="/home/isaac/Projects/youtube-playlist-app/data/mp3"
UPLOAD_URL="http://192.168.7.140/upload.json"

# Contar archivos mp3 detectados
TOTAL_FILES=$(find "$MP3_DIR" -maxdepth 1 -type f -name '*.mp3' | wc -l)
echo "🎵 Archivos mp3 detectados para copiar: $TOTAL_FILES"

COPIED=0

find "$MP3_DIR" -maxdepth 1 -type f -name '*.mp3' -print0 | while IFS= read -r -d '' file; do
  if [[ -r "$file" ]]; then
    echo "🚀 Upload: $file"
    LC_ALL=C curl -F "files[]=@${file}" -- "$UPLOAD_URL"
    CURL_EXIT=$?
    if [[ $CURL_EXIT -eq 0 ]]; then
      echo "✅ Uploaded: $file"
      ((COPIED++))
    else
      echo "❌ Error al subir: $file (curl exit code: $CURL_EXIT)"
    fi
  else
    echo "❌ No se puede leer el archivo: $file"
  fi
  echo "----------------------------------------"
done

# Mostrar resumen al finalizar
echo "🎉 Archivos copiados exitosamente: $COPIED de $TOTAL_FILES"
