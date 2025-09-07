from pytubefix import YouTube
from pytubefix.cli import on_progress
import time

# Array de URLs de YouTube para descargar
urls = [
    "https://www.youtube.com/watch?v=G9T_8DEXFxU",
]

def download_video(url, video_number, total_videos):
    """Descarga un video individual de YouTube"""
    try:
        print(f"\n[{video_number}/{total_videos}] Procesando: {url}")
        
        yt = YouTube(url, on_progress_callback=on_progress)
        print(f"Título: {yt.title}")
        
        # Obtener la mejor resolución disponible
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