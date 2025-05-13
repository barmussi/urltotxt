import subprocess, os, tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

@app.route("/download", methods=["POST"])
def descargar_audio():
    data = request.json
    url = data.get("youtube_url")
    if not url:
        return jsonify({"error": "Falta 'youtube_url'"}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "audio.%(ext)s")

        command = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--user-agent", "Mozilla/5.0",
            "--no-check-certificate",
            "-o", output_path,
            url
        ]

        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            return jsonify({"error": "Fallo yt-dlp", "details": str(e)}), 500

        # Buscar el archivo mp3 generado
        for file in os.listdir(tmpdir):
            if file.endswith(".mp3"):
                return send_file(os.path.join(tmpdir, file), as_attachment=True, download_name="audio.mp3")

        return jsonify({"error": "No se generó ningún archivo mp3"}), 500

@app.route("/")
def home():
    return "API YouTube a MP3 activa"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "yt-dlp downloader"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
