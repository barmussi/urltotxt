import os
import mimetypes
import time
import browser_cookie3
from flask import Flask, request, send_file, jsonify
import yt_dlp

app = Flask(__name__)

# Configuración básica
TEMP_FOLDER = "temp"
os.makedirs(TEMP_FOLDER, exist_ok=True)

# =============================================
# 🔧 CONFIGURACIÓN DE yt-dlp CON COOKIES AUTOMÁTICAS
# =============================================
def get_ytdl_options(output_path, max_retries=3):
    """
    Configura yt-dlp para usar cookies del navegador o archivo cookies.txt.
    """
    # Opciones base
    ydl_opts = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': output_path,
        'quiet': False,
        'no_warnings': False,
        'ignoreerrors': False,
        'retries': max_retries,
        'socket_timeout': 30,
        'referer': 'https://www.youtube.com',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    # 🔄 Intentar cargar cookies automáticamente (Chrome, Firefox, Edge)
    try:
        cookies = browser_cookie3.load(domain_name='youtube.com')
        if cookies:
            ydl_opts['cookies'] = {c.name: c.value for c in cookies}
            print("✅ Cookies del navegador cargadas automáticamente")
    except Exception as e:
        print(f"⚠ No se pudieron cargar cookies del navegador: {e}")
        # Si falla, intentar con cookies.txt
        if os.path.exists('cookies.txt'):
            ydl_opts['cookiefile'] = 'cookies.txt'
            print("✅ Usando cookies.txt como respaldo")

    return ydl_opts

# =============================================
# 📥 FUNCIÓN PRINCIPAL DE DESCARGA
# =============================================
def download_audio(video_url, output_dir=TEMP_FOLDER, max_retries=3):
    """
    Descarga audio desde YouTube usando yt-dlp con manejo de errores.
    """
    output_path = os.path.join(output_dir, "%(title)s.%(ext)s")
    ydl_opts = get_ytdl_options(output_path, max_retries)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 🔍 Verificar disponibilidad antes de descargar
            info = ydl.extract_info(video_url, download=False)
            
            if info.get('availability') != 'public':
                raise Exception("❌ El vídeo no está disponible (privado/eliminado/restringido)")
            
            # ⏬ Descargar el audio
            ydl.download([video_url])
            
            # 📌 Obtener el nombre real del archivo generado
            filename = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')
            return filename

    except yt_dlp.utils.DownloadError as e:
        raise Exception(f"Error al descargar: {str(e)}")
    except Exception as e:
        raise Exception(f"Error inesperado: {str(e)}")

# =============================================
# 🌐 ENDPOINTS FLASK
# =============================================
@app.route("/download", methods=["GET"])
def handle_download():
    """Endpoint para descargar audio desde YouTube."""
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "Se requiere el parámetro 'url'"}), 400

    try:
        # ⏳ Descargar el audio
        file_path = download_audio(video_url)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "El archivo no se generó correctamente"}), 500

        # 📊 Obtener metadatos del archivo
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        size_in_mb = round(file_size / (1024 * 1024), 2)

        # 🎯 Respuesta con datos + descarga
        return jsonify({
            "status": "success",
            "data": {
                "filename": file_name,
                "size": f"{size_in_mb} MB",
                "format": "MP3",
                "bitrate": "128kbps (estimado)"
            }
        }), send_file(
            file_path,
            as_attachment=True,
            mimetype="audio/mpeg",
            download_name=file_name
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    return "🎧 YouTube MP3 Downloader API 🎶"

@app.route("/health")
def health_check():
    return jsonify({"status": "active", "version": "1.0"})

# =============================================
# 🚀 INICIAR SERVIDOR
# =============================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
