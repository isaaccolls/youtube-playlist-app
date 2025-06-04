#!/bin/bash

MP3_DIR="/home/isaac/Projects/youtube-playlist-app/data/mp3"
UPLOAD_URL="http://192.168.7.140/upload.json"

for file in "$MP3_DIR"/*.mp3; do
  if [[ -f "$file" ]]; then
    echo "🚀 Upload: $file"
    curl -F "files[]=@${file}" "$UPLOAD_URL"
    echo "✅ Uploaded: $file"
  fi
done
