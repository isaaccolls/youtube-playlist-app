#!/bin/bash

MP3_DIR="/home/isaac/Projects/youtube-playlist-app/data/mp3"
UPLOAD_URL="http://192.168.7.140/upload.json"

for file in "$MP3_DIR"/*.mp3; do
  if [[ -f "$file" && -r "$file" ]]; then
    echo "🚀 Upload: $file"
    LC_ALL=C curl -F "files[]=@${file}" -- "$UPLOAD_URL"
    echo "✅ Uploaded: $file"
  else
    echo "❌ No se puede leer el archivo: $file"
  fi
  echo "----------------------------------------"
done
