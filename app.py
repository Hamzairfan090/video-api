import time
import base64
import os
from flask import Flask, request, jsonify, send_file
from google import genai
from io import BytesIO
from PIL import Image

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

        # base64 → image
        image_bytes = base64.b64decode(image_base64)
        image = Image.open(BytesIO(image_bytes))

        # generate video
        operation = client.models.generate_videos(
            model="veo-3.1-generate-preview",
            prompt=prompt,
            image=image,
        )

        # wait
        while not operation.done:
            time.sleep(10)
            operation = client.operations.get(operation)

        video = operation.response.generated_videos[0]
        file_data = client.files.download(file=video.video)

        return send_file(
            BytesIO(file_data),
            mimetype="video/mp4",
            as_attachment=True,
            download_name="video.mp4"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
