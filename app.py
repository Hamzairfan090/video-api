import time
import os
import requests
from flask import Flask, request, jsonify, send_file
from google import genai
from io import BytesIO

app = Flask(__name__)

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

@app.route("/")
def home():
    return "API is running"

@app.route("/generate-video", methods=["POST"])
def generate_video():
    try:
        data = request.json

        prompt = data.get("prompt")
        image_url = data.get("image_url")

        if not prompt or not image_url:
            return jsonify({"error": "Missing prompt or image_url"}), 400

        # 🔥 1. Download image from URL
        img_response = requests.get(image_url)
        if img_response.status_code != 200:
            return jsonify({"error": "Failed to download image"}), 400

        image_bytes = img_response.content

        # 🎬 2. Generate video using Veo
        operation = client.models.generate_videos(
            model="veo-3.1-generate-preview",
            prompt=prompt,
            image=image_bytes,
        )

        # ⏳ 3. Wait for completion
        while not operation.done:
            print("Waiting for video...")
            time.sleep(10)
            operation = client.operations.get(operation)

        video = operation.response.generated_videos[0]

        # 📥 4. Download video
        file_data = client.files.download(file=video.video)

        return send_file(
            BytesIO(file_data),
            mimetype="video/mp4",
            as_attachment=True,
            download_name="video.mp4"
        )

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
