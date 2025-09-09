from pytubefix import YouTube
from pytubefix.cli import on_progress
import time

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
    """Descarga un video individual de YouTube"""
    try:
        print(f"\n[{video_number}/{total_videos}] Procesando: {url}")
        
        yt = YouTube(url, on_progress_callback=on_progress)
        print(f"Título: {yt.title}")
        
        # Intentar obtener 1080p específicamente
        ys = yt.streams.filter(res="1080p", file_extension="mp4").first()
        
        # Si no hay 1080p, intentar 720p
        if not ys:
            print("⚠️  1080p no disponible, intentando 720p...")
            ys = yt.streams.filter(res="720p", file_extension="mp4").first()
        
        # Si no hay 720p, intentar con la mejor resolución disponible
        if not ys:
            print("⚠️  720p no disponible, buscando la mejor resolución...")
            ys = yt.streams.get_highest_resolution()
        
        if ys:
            print(f"Descargando en resolución: {ys.resolution}")
            ys.download()
            print(f"✅ Descarga completada: {yt.title}")
            return True
        else:
            print(f"❌ No se encontraron streams disponibles para: {yt.title}")
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