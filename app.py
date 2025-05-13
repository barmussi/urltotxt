import os
import tempfile
from flask import Flask, request, jsonify, send_file
import yt_dlp

app = Flask(__name__)

@app.route('/download', methods=['GET'])
def download_audio():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "Se requiere el parámetro 'url'"}), 400

    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, '%(title)s.%(ext)s')
    filename = None  # Inicializamos la variable

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
        'ignoreerrors': False,  # Cambiado a False para manejar errores explícitamente
        'retries': 3,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # Verificación más robusta de disponibilidad
            if not info or info.get('availability', 'public') != 'public':
                return jsonify({
                    "error": "El vídeo no está disponible",
                    "reason": info.get('availability') if info else "No se pudo obtener información"
                }), 404
            
            # Descargar el audio
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
        # Limpieza segura
        try:
            if filename and os.path.exists(filename):
                os.remove(filename)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as cleanup_error:
            print(f"Error durante limpieza: {cleanup_error}")

@app.route('/')
def home():
    return "YouTube a MP3 API - Versión Estable ✅"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
