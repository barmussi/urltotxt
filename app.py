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
    # 'cookiefile': 'cookies.txt', # Se configura dinámicamente si se usa variable de entorno
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept-Language': 'en-US,en;q=0.9'
    }
}

# Configuración dinámica del archivo de cookies desde la variable de entorno (opcional)
COOKIES_CONTENT = os.environ.get('COOKIES_CONTENT')
if COOKIES_CONTENT:
    with open('cookies.txt', 'w') as f:
        f.write(COOKIES_CONTENT)
    YDL_OPTS['cookiefile'] = 'cookies.txt'
elif os.path.exists('cookies.txt'):
    YDL_OPTS['cookiefile'] = 'cookies.txt'
else:
    print("Advertencia: No se encontró el archivo cookies.txt ni la variable de entorno COOKIES_CONTENT.")

@app.route('/super', methods=['GET'])
def super_download():
    try:
        url = request.args['url']
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url)
            audio_data = BytesIO(ydl.pipe.read())
            audio_data.seek(0) # ¡Importante! Volver al inicio del buffer

            return send_file(
                audio_data,
                mimetype='audio/mpeg',
                as_attachment=True,
                download_name=f"{info['title'][:30]}.mp3"
            )
    except Exception as e:
        error_message = "¡Error al descargar el contenido!"
        solution_message = "Si el contenido está restringido, asegúrate de haber configurado correctamente el archivo cookies.txt o la variable de entorno COOKIES_CONTENT."
        return jsonify({
            "error": error_message,
            "solución": solution_message,
            "detalles": str(e)
        }), 500

@app.route('/health')
def health():
    return jsonify({"status": "🔥 Turbo Activo"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000) # Render espera la aplicación en el puerto 10000
