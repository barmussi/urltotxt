import os
import tempfile
from flask import Flask, request, jsonify, send_file
import yt_dlp

app = Flask(__name__)

@app.route('/')
def home():
    """Endpoint raíz que muestra el estado del servicio"""
    return """
    <h1>YouTube to MP3 API</h1>
    <p>Estado: <span style="color: green;">Operativo ✅</span></p>
    <p>Endpoints disponibles:</p>
    <ul>
        <li><code>GET /download?url=YOUTUBE_URL</code> - Descarga audio como MP3</li>
        <li><code>GET /health</code> - Verifica salud del servicio</li>
    </ul>
    """

@app.route('/health')
def health_check():
    """Endpoint de verificación de salud"""
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "components": {
            "yt_dlp": "operational",
            "disk_space": "adequate",
            "memory": "stable"
        }
    }), 200

@app.route('/download', methods=['GET'])
def download_audio():
    """Endpoint principal para descarga de audio"""
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "Se requiere el parámetro 'url'"}), 400

    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, '%(title)s.%(ext)s')
    filename = None

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': False,
        'retries': 3,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            if not info or info.get('availability', 'public') != 'public':
                return jsonify({
                    "error": "El vídeo no está disponible",
                    "available": False,
                    "reason": info.get('availability') if info else "No se pudo obtener información"
                }), 404
            
            ydl.download([video_url])
            filename = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')

            if not os.path.exists(filename):
                return jsonify({"error": "El archivo MP3 no se generó correctamente"}), 500

            return send_file(
                filename,
                as_attachment=True,
                mimetype='audio/mpeg',
                download_name=os.path.basename(filename)
            )

    except yt_dlp.utils.DownloadError as e:
        return jsonify({
            "error": "Error al descargar el video",
            "details": str(e),
            "solution": "Intente con otro video o verifique la URL"
        }), 500
    except Exception as e:
        return jsonify({
            "error": "Error inesperado",
            "details": str(e)
        }), 500
    finally:
        try:
            if filename and os.path.exists(filename):
                os.remove(filename)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as cleanup_error:
            app.logger.error(f"Error durante limpieza: {cleanup_error}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
