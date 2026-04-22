import time
import os
from flask import Flask, request, jsonify
from google import genai

app = Flask(__name__)

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

@app.route("/")
def home():
    return "Veo 3.1 API Running"


# =========================
# GENERATE VIDEO
# =========================
@app.route("/generate-video", methods=["POST"])
def generate_video():
    try:
        data = request.get_json()

        instances = data.get("instances")
        parameters = data.get("parameters")

        if not instances:
            return jsonify({"error": "Missing instances"}), 400

        # =========================
        # CALL VEO MODEL
        # =========================
        operation = client.models.generate_videos(
            model="veo-3.1-generate-preview",
            instances=instances,
            parameters=parameters
        )

        # =========================
        # WAIT FOR RESULT
        # =========================
        while not operation.done:
            time.sleep(10)
            operation = client.operations.get(operation)

        video = operation.response.generated_videos[0]

        return jsonify({
            "status": "success",
            "video_uri": video.video
        })

    except Exception as e:
        return jsonify({
            "status": "failed",
            "error": str(e)
        }), 500


# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
