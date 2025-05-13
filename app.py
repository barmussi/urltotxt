import os
import tempfile
from flask import Flask, request, jsonify, send_file
import yt_dlp

app = Flask(__name__)

@app.route('/download', methods=['GET'])
def download_audio():
    # Obtener la URL del vídeo desde los parámetros de la consulta
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "Se requiere el parámetro 'url'"}), 400

    # Crear una carpeta temporal para guardar el archivo
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, '%(title)s.%(ext)s')

    # Configuración de yt-dlp (sin cookies)
    ydl_opts = {
        'format': 'bestaudio/best',  # Mejor calidad de audio disponible
        'outtmpl': output_path,      # Ruta de salida
        'postprocessors': [{         # Convertir a MP3
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',  # Calidad de audio (192 kbps)
        }],
        'quiet': True,               # Silenciar logs innecesarios
        'no_warnings': True,        # Ignorar advertencias
        'ignoreerrors': True,       # Continuar si hay errores
        'retries': 3,               # Reintentar en caso de fallo
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extraer información del vídeo (sin descargar aún)
            info = ydl.extract_info(video_url, download=False)
            
            # Verificar si el vídeo está disponible
            if not info or info.get('availability') != 'public':
                return jsonify({"error": "El vídeo no está disponible o es privado"}), 404
            
            # Descargar el audio y convertirlo a MP3
            ydl.download([video_url])

            # Obtener el nombre del archivo generado
            filename = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')

            # Verificar si el archivo existe
            if not os.path.exists(filename):
                return jsonify({"error": "No se pudo generar el archivo MP3"}), 500

            # Enviar el archivo como respuesta
            return send_file(
                filename,
                as_attachment=True,
                mimetype='audio/mpeg',
                download_name=os.path.basename(filename)
            )

    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": f"Error al descargar: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Error inesperado: {str(e)}"}), 500
    finally:
        # Limpiar archivos temporales
        if os.path.exists(filename):
            os.remove(filename)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

@app.route('/')
def home():
    return "API de YouTube a MP3 (sin cookies) ✅"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
