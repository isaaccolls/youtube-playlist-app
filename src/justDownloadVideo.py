from pytubefix import YouTube, Playlist
from pytubefix.cli import on_progress
import time
import os
from urllib.parse import parse_qs, urlparse

DOWNLOAD_PATH = "/home/isaac/Downloads/videos/podcast"

# Array de URLs de YouTube para descargar
urls = [
    # music
    # "https://www.youtube.com/playlist?list=PL_8z4vyyerkNOgsNi67YVJrfMxaMHiL2u",
    # "https://www.youtube.com/playlist?list=PL_8z4vyyerkNQ7feaSGqFpSw99_Iks-09",
    # "https://www.youtube.com/playlist?list=PL_8z4vyyerkNuVi_SfPch16lyqJFl6xn_",
    # "https://www.youtube.com/playlist?list=PL_8z4vyyerkPaPo2QUvvJSwNpxg-XC4CN"
    # podcast
    # 284 | ¿Quién es Alex Saab?
    "https://www.youtube.com/live/q3M9Af9NbbU",
    # 283 | Lo que se sabe del Hantavirus
    "https://www.youtube.com/live/mv-KLPgC1HY",
    # 282 | Llenamos el álbum del mundial
    "https://www.youtube.com/live/YsD9-8cI5RI",
    # 281 | Daniel lee sus DMs
    "https://www.youtube.com/live/1up-M2Y2QTw",
    # 280 | ¿Cómo va la transición en Venezuela?
    "https://www.youtube.com/live/--yfMGR3R3M",
    # 279 | Jugamos con la pantalla verde
    "https://www.youtube.com/live/6y7dPRH-UnQ",
    # 278 | ¿Qué son las fruti-novelas?
    "https://www.youtube.com/live/U1EoGhGSXMw",
    # 277 | ¿Cuál es el fenómeno de las rifas?
    "https://www.youtube.com/live/u8LIb_aEteY",
    # 276 | Venezuela campeón
    "https://www.youtube.com/live/R1iJXlWJexk",
    # 275 | ¿Cómo ha sido el Clásico Mundial de Béisbol?
    "https://www.youtube.com/live/jo7YWF9m9K4",
    # 274 | ¿Qué pasa en Irán?
    "https://www.youtube.com/live/TfRRd4ZZPW0",
    # 273 | ¿Qué está pasando en México?
    "https://www.youtube.com/live/shfDSLA8-Ag",
    # 272 | ¿Por qué se habla tanto de los Therians?
    "https://www.youtube.com/live/ZoijntOm6dk",
    # 271 | ¿Qué es ser latino?
    "https://www.youtube.com/live/SHgMn_0bj-k",
    # 270 | ¿Quiénes son el ICE?
    "https://www.youtube.com/live/yQXDdS_EXmE",
    # 269 | Grandes hazañas de la historia
    "https://www.youtube.com/live/g6R7IvuETfQ",
    # 268 | ¿En qué andábamos en el 2016?
    "https://www.youtube.com/live/8PiV8I_wp8c",
    # 267 | Mundo en llamas - vol. 2
    "https://www.youtube.com/live/ePPmTHedSd8",
    # 266 | Bigote Político - Más bigote, más político que nunca
    "https://www.youtube.com/live/Yhz9PuWtqIs",
    "https://www.youtube.com/live/plvky1G5jtM",
    # 265 | ¡Vision Board 2026!
    "https://www.youtube.com/live/oaXadMghFV4",
    # 264 | La cena navideña en El Cuartico
    "https://www.youtube.com/live/SCqpQZDbK7A",
]

def is_playlist_url(url):
    """Indica si la URL contiene un parámetro de playlist."""
    query_params = parse_qs(urlparse(url).query)
    return "list" in query_params

def get_video_urls(url):
    """Devuelve las URLs de video para una URL individual o una playlist."""
    if not is_playlist_url(url):
        return [url]

    print(f"📋 Detectada playlist: {url}")
    playlist = Playlist(url)
    video_urls = list(playlist.video_urls)
    print(f"✅ Playlist cargada con {len(video_urls)} video(s)")
    return video_urls

def download_video(url, video_number, total_videos):
    """Descarga un video individual de YouTube con autenticación por cookies"""
    try:
        print(f"\n[{video_number}/{total_videos}] Procesando: {url}")
        os.makedirs(DOWNLOAD_PATH, exist_ok=True)
        
        # Configurar cookies si el archivo existe
        cookies_path = "cookies.txt"
        if os.path.exists(cookies_path):
            print("🍪 Usando cookies para autenticación...")
            yt = YouTube(url, on_progress_callback=on_progress, use_oauth=False, allow_oauth_cache=True)
            # Cargar cookies
            yt.cookies = cookies_path
        else:
            print("⚠️  Archivo de cookies no encontrado, descargando sin autenticación...")
            yt = YouTube(url, on_progress_callback=on_progress)
        
        print(f"Título: {yt.title}")
        
        # Estrategia 1: Intentar streams progresivos (con audio) en orden de preferencia
        print("🔍 Buscando streams progresivos (con audio)...")
        
        # Primero intentar 1080p progresivo
        ys = yt.streams.filter(progressive=True, res="1080p", file_extension="mp4").first()
        
        # Si no hay 1080p progresivo, intentar 720p progresivo
        if not ys:
            print("⚠️  1080p progresivo no disponible, intentando 720p progresivo...")
            ys = yt.streams.filter(progressive=True, res="720p", file_extension="mp4").first()
        
        # Si no hay 720p progresivo, intentar 480p progresivo
        if not ys:
            print("⚠️  720p progresivo no disponible, intentando 480p progresivo...")
            ys = yt.streams.filter(progressive=True, res="480p", file_extension="mp4").first()
        
        # Si no hay streams progresivos, usar el mejor stream progresivo disponible
        if not ys:
            print("⚠️  Resoluciones específicas no disponibles, buscando mejor stream progresivo...")
            ys = yt.streams.filter(progressive=True, file_extension="mp4").order_by('resolution').desc().first()
        
        # Estrategia 2: Si no hay streams progresivos, combinar video y audio por separado
        if not ys:
            print("🔄 No hay streams progresivos, intentando combinar video y audio por separado...")
            
            # Buscar el mejor stream de video (sin audio)
            video_stream = None
            for res in ["1080p", "720p", "480p", "360p"]:
                video_stream = yt.streams.filter(adaptive=True, res=res, file_extension="mp4", only_video=True).first()
                if video_stream:
                    print(f"📹 Video encontrado en {res}")
                    break
            
            # Buscar el mejor stream de audio
            audio_stream = yt.streams.filter(adaptive=True, file_extension="mp4", only_audio=True).order_by('abr').desc().first()
            if audio_stream:
                print(f"🎵 Audio encontrado: {audio_stream.abr}")
            
            if video_stream and audio_stream:
                print(f"📥 Descargando video en {video_stream.resolution} y audio por separado...")
                # Descargar video
                video_filename = video_stream.download(output_path=DOWNLOAD_PATH, filename_prefix="video_")
                # Descargar audio
                audio_filename = audio_stream.download(output_path=DOWNLOAD_PATH, filename_prefix="audio_")
                print(f"✅ Descarga completada: {yt.title}")
                print("ℹ️  Nota: Los archivos de video y audio están separados. Usa ffmpeg para combinarlos si es necesario.")
                return True
            else:
                print("❌ No se pudieron encontrar streams de video y audio por separado")
                print("❌ No se puede descargar este video con audio garantizado")
                return False
        
        # Solo descargar si tenemos un stream con audio garantizado
        if ys:
            print(f"📥 Descargando en resolución: {ys.resolution}")
            ys.download(output_path=DOWNLOAD_PATH)
            print(f"✅ Descarga completada: {yt.title}")
            return True
        else:
            print(f"❌ No se encontraron streams con audio para: {yt.title}")
            return False
            
    except Exception as e:
        print(f"❌ Error al descargar {url}: {str(e)}")
        return False

def main():
    """Función principal que procesa todas las URLs secuencialmente"""
    if not urls:
        print("❌ No hay URLs para procesar. Agrega URLs al array 'urls'.")
        return

    os.makedirs(DOWNLOAD_PATH, exist_ok=True)

    download_urls = []
    for url in urls:
        try:
            download_urls.extend(get_video_urls(url))
        except Exception as e:
            print(f"❌ Error al cargar la playlist o URL {url}: {str(e)}")
    
    total_videos = len(download_urls)
    if total_videos == 0:
        print("❌ No se encontraron videos para descargar.")
        return

    successful_downloads = 0
    failed_downloads = 0
    
    print(f"🎬 Iniciando descarga de {total_videos} video(s)...")
    print("=" * 50)
    
    start_time = time.time()
    
    for i, url in enumerate(download_urls, 1):
        if download_video(url, i, total_videos):
            successful_downloads += 1
        else:
            failed_downloads += 1
        
        # Pequeña pausa entre descargas para evitar problemas de rate limiting
        if i < total_videos:
            print("⏳ Esperando 2 segundos antes de la siguiente descarga...")
            time.sleep(2)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE DESCARGAS:")
    print(f"✅ Exitosas: {successful_downloads}")
    print(f"❌ Fallidas: {failed_downloads}")
    print(f"⏱️  Tiempo total: {total_time:.2f} segundos")
    print("=" * 50)

if __name__ == "__main__":
    main()