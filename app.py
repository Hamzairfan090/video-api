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
        prompt = None
        image_bytes = None

        # 🔥 1. Handle JSON (image_url)
        if request.content_type and "application/json" in request.content_type:
            data = request.get_json()

            prompt = data.get("prompt")
            image_url = data.get("image_url")

            if not prompt or not image_url:
                return jsonify({"error": "Missing prompt or image_url"}), 400

            # Download image
            img_response = requests.get(image_url)
            if img_response.status_code != 200:
                return jsonify({"error": "Failed to download image"}), 400

            image_bytes = img_response.content

        # 🔥 2. Handle Form-Data (direct file upload)
        elif request.content_type and "multipart/form-data" in request.content_type:
            prompt = request.form.get("prompt")
            image = request.files.get("image")

            if not prompt or not image:
                return jsonify({"error": "Missing prompt or image file"}), 400

            image_bytes = image.read()

        else:
            return jsonify({"error": "Unsupported content type"}), 400

        print("PROMPT:", prompt)
        print("Image size:", len(image_bytes))

        # 🎬 3. Generate video
        operation = client.models.generate_videos(
            model="veo-3.1-generate-preview",
            prompt=prompt,
            image=image_bytes,
        )

        # ⏳ 4. Wait for completion
        while not operation.done:
            print("Waiting for video...")
            time.sleep(10)
            operation = client.operations.get(operation)

        video = operation.response.generated_videos[0]

        # 📥 5. Download video
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
