import os
from flask import Flask, request, send_file, jsonify
import yt_dlp
import mimetypes

app = Flask(__name__)

@app.route("/download", methods=["GET"])
def download_audio():
    # Obtén la URL del video de YouTube desde los parámetros de la consulta
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "Falta el parámetro 'url'"}), 400

    # Define el archivo de salida
    output_file = "audio.%(ext)s"

    # Descargar el audio con yt-dlp
    try:
        descargar_audio(video_url, output_file)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Si el archivo se ha descargado correctamente, obtener la información del archivo
    file_path = output_file % {'ext': 'mp3'}  # El archivo final será "audio.mp3"
    
    if not os.path.exists(file_path):
        return jsonify({"error": "El archivo no se generó correctamente"}), 500

    file_name = os.path.basename(file_path)
    file_extension = file_name.split('.')[-1]
    mime_type, _ = mimetypes.guess_type(file_path)
    file_size = os.path.getsize(file_path)

    # Convertir el tamaño a una forma legible
    size_in_kb = round(file_size / 1024, 2)

    # Devolver la información del archivo junto con el archivo
    return jsonify({
        "data": {
            "File Name": file_name,
            "File Extension": file_extension,
            "Mime Type": mime_type,
            "File Size": f"{size_in_kb} kB"
        }
    }), send_file(file_path, as_attachment=True, download_name=file_name)

def descargar_audio(video_url, output_file):
    ydl_opts = {
        'format': 'bestaudio/best',
        'extract_audio': True,
        'audio_format': 'mp3',
        'outtmpl': output_file
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])


@app.route("/")
def home():
    return "✅ API YouTube a MP3 activa"

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "yt-dlp downloader"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
