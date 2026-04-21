import time
import os
import base64
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
        image_base64 = data.get("image")

        if not prompt or not image_base64:
            return jsonify({"error": "Missing prompt or image"}), 400

        # ✅ Remove base64 prefix if present
        if "base64," in image_base64:
            image_base64 = image_base64.split("base64,")[1]

        # ✅ Convert base64 → bytes
        image_bytes = base64.b64decode(image_base64)

        # 🎬 Generate video (NO wrapper!)
        operation = client.models.generate_videos(
            model="veo-3.1-generate-preview",
            prompt=prompt,
            image=image_bytes,
        )

        # ⏳ Wait for completion
        while not operation.done:
            print("Waiting for video...")
            time.sleep(10)
            operation = client.operations.get(operation)

        video = operation.response.generated_videos[0]

        # 📥 Download video
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
