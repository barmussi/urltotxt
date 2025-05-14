import os
import yt_dlp
from flask import Flask, request, send_file, jsonify
from io import BytesIO

app = Flask(__name__)

# Configuración express turbo
YDL_OPTS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
    }],
    'outtmpl': '-',  # Stream directo a memoria
    'quiet': True,
    'no_warnings': True,
    'http_chunk_size': 1048576,  # Buffer grande para velocidad
}

@app.route('/turbo', methods=['GET'])
def turbo_download():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "¡URL requerida! Ej: /turbo?url=VIDEO_URL"}), 400
    
    try:
        ydl = yt_dlp.YoutubeDL(YDL_OPTS)
        info = ydl.extract_info(url, download=True)
        audio_data = ydl.pipe.result
        
        return send_file(
            BytesIO(audio_data),
            as_attachment=True,
            mimetype='audio/mpeg',
            download_name=f"{info['title'][:25]}.mp3"
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health():
    return jsonify({"status": "🚀 Hyper Active", "version": "Turbo-2.0"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))
