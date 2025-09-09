from pytubefix import YouTube
from pytubefix.cli import on_progress
import time
import os

# Array de URLs de YouTube para descargar
urls = [
    "https://www.youtube.com/watch?v=B5fEVQ60RyQ",
    "https://www.youtube.com/watch?v=jzVGnBb23rU",
    "https://www.youtube.com/watch?v=027o0EshENI&list=PLqaxRcHTgYrNYFs0O9LUrf4vJBHnP1y1s&index=1",
    "https://www.youtube.com/watch?v=hGcvP1agDNc&list=PLqaxRcHTgYrNYFs0O9LUrf4vJBHnP1y1s&index=2",
    "https://www.youtube.com/watch?v=d-LhID_V6LA&list=PLqaxRcHTgYrNYFs0O9LUrf4vJBHnP1y1s&index=3",
    "https://www.youtube.com/watch?v=hp0TWVGvPyM&list=PLqaxRcHTgYrNYFs0O9LUrf4vJBHnP1y1s&index=4",
    "https://www.youtube.com/watch?v=RBv91u7Msig&list=PLqaxRcHTgYrNYFs0O9LUrf4vJBHnP1y1s&index=5",
    "https://www.youtube.com/watch?v=gHVnA6p3zS0&list=PLqaxRcHTgYrNYFs0O9LUrf4vJBHnP1y1s&index=6",
    "https://www.youtube.com/watch?v=aVODOlxWwbM&list=PLqaxRcHTgYrNYFs0O9LUrf4vJBHnP1y1s&index=7",
    "https://www.youtube.com/watch?v=JarupwcMcmM&list=PLqaxRcHTgYrNYFs0O9LUrf4vJBHnP1y1s&index=8"
]

def download_video(url, video_number, total_videos):
    """Descarga un video individual de YouTube con autenticación por cookies"""
    try:
        print(f"\n[{video_number}/{total_videos}] Procesando: {url}")
        
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
                video_filename = video_stream.download(filename_prefix="video_")
                # Descargar audio
                audio_filename = audio_stream.download(filename_prefix="audio_")
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
            ys.download()
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
    
    total_videos = len(urls)
    successful_downloads = 0
    failed_downloads = 0
    
    print(f"🎬 Iniciando descarga de {total_videos} video(s)...")
    print("=" * 50)
    
    start_time = time.time()
    
    for i, url in enumerate(urls, 1):
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