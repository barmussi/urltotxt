from flask import Flask, request, jsonify, send_file
import subprocess
import os
import tempfile

app = Flask(__name__)

@app.route("/download", methods=["POST"])
def download_audio():
    data = request.get_json()
    url = data.get("youtube_url")

    if not url:
        return jsonify({"error": "Falta el parámetro 'youtube_url'"}), 400

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "audio.mp3")
            command = [
                "yt-dlp",
                "--extract-audio",
                "--audio-format", "mp3",
                "-o", output_path,
                url
            ]
            subprocess.run(command, check=True)

            return send_file(
                output_path,
                as_attachment=True,
                download_name="audio.mp3",
                mimetype="audio/mpeg"
            )

    except subprocess.CalledProcessError as e:
        return jsonify({"error": "Error al procesar el video", "details": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "yt-dlp downloader"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
