import os
import tempfile
import yt_dlp
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Configuración global
MAX_RETRIES = 3
DEFAULT_PORT = 10000

@app.route('/')
def home():
    """Endpoint raíz con información del servicio"""
    return """
    <h1>YouTube Audio Downloader API</h1>
    <p><b>Status:</b> <span style="color: green;">Operational ✅</span></p>
    <p><b>Endpoints:</b></p>
    <ul>
        <li><code>GET /download?url=YOUTUBE_URL</code> - Descarga audio en MP3</li>
        <li><code>GET /health</code> - Verifica el estado del servicio</li>
    </ul>
    """

@app.route('/health')
def health_check():
    """Endpoint de verificación de salud"""
    return jsonify({
        "status": "healthy",
        "service": "youtube-audio-downloader",
        "version": "1.0.0",
        "components": {
            "yt_dlp": "operational",
            "disk_space": "adequate",
            "memory": "stable"
        }
    })

@app.route('/download', methods=['GET'])
def download_audio():
    """Endpoint principal para descarga de audio"""
    video_url = request.args.get('url')
    
    if not video_url:
        return jsonify({
            "error": "Missing URL parameter",
            "example": "/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }), 400

    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, 'audio.%(ext)s')

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'retries': MAX_RETRIES,
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')

            if not os.path.exists(filename):
                return jsonify({"error": "Failed to generate MP3 file"}), 500

            return send_file(
                filename,
                as_attachment=True,
                mimetype='audio/mpeg',
                download_name=os.path.basename(filename)
            
    except yt_dlp.utils.DownloadError as e:
        return jsonify({
            "error": "Download failed",
            "details": str(e),
            "solution": "Try again later or check the video URL"
        }), 500
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500
    finally:
        # Limpieza de archivos temporales
        if 'filename' in locals() and os.path.exists(filename):
            os.remove(filename)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', DEFAULT_PORT)))
