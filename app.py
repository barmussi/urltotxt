import os
import tempfile
import yt_dlp
from flask import Flask, request, send_file, jsonify
from flask_caching import Cache

app = Flask(__name__)
cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})
cache.init_app(app)

# Configuración express para yt-dlp
YDL_OPTS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '128',  # Calidad balanceada
    }],
    'outtmpl': '%(id)s.%(ext)s',  # Nombre corto para rapidez
    'quiet': True,
    'no_warnings': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.5'
    }
}

@app.route('/fast', methods=['GET'])
@cache.cached(timeout=300, query_string=True)
def fast_download():
    url = request.args.get('url')
    
    if not url:
        return jsonify({"error": "URL parameter required"}), 400
    
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = f"{info['id']}.mp3"
            
            return send_file(
                filename,
                as_attachment=True,
                mimetype='audio/mpeg',
                download_name=f"{info['title'][:30]}.mp3"  # Nombre corto
            )
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        # Limpieza express
        if 'filename' in locals():
            try: os.remove(filename)
            except: pass

@app.route('/health')
def health():
    return jsonify({"status": "hyper", "version": "flash-1.0"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))
