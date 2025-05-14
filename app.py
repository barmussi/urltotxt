import os
from flask import Flask, request, send_file, jsonify
from io import BytesIO
import yt_dlp

app = Flask(__name__)

# Configuración Turbo++ con cookies de emergencia
YDL_OPTS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
    }],
    'outtmpl': '-',
    'quiet': True,
    'cookiefile': 'cookies.txt',  # Archivo de cookies opcional
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept-Language': 'en-US,en;q=0.9'
    }
}

@app.route('/super', methods=['GET'])
def super_download():
    try:
        url = request.args['url']
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url)
            return send_file(
                BytesIO(ydl.pipe.read()),
                mimetype='audio/mpeg',
                as_attachment=True,
                download_name=f"{info['title'][:30]}.mp3"
            )
    except Exception as e:
        return jsonify({
            "error": "¡Contenido restringido!",
            "solución": "Usa cookies.txt",
            "detalles": str(e)
        }), 500

@app.route('/health')
def health():
    return jsonify({"status": "🔥 Turbo Activo"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))
