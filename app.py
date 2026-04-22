import time
import os
import requests
import uuid
import base64
import threading
from flask import Flask, request, jsonify, send_file
from google import genai
from io import BytesIO

app = Flask(__name__)

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

jobs = {}

@app.route("/")
def home():
    return "Veo API Running"


# =========================
# GENERATE VIDEO
# =========================
@app.route("/generate-video", methods=["POST"])
def generate_video():
    try:
        data = request.get_json()

        prompt = data.get("prompt")
        image_url = data.get("image_url")

        if not prompt or not image_url:
            return jsonify({"error": "Missing prompt or image_url"}), 400

        job_id = str(uuid.uuid4())

        jobs[job_id] = {
            "status": "queued",
            "error": None,
            "video": None
        }

        def process():
            try:
                jobs[job_id]["status"] = "processing"

                # 1. download image
                img = requests.get(image_url, timeout=30)
                if img.status_code != 200:
                    raise Exception("Image download failed")

                image_bytes = img.content

                # 2. FIXED BASE64 (IMPORTANT)
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")

                # 3. EXACT REQUIRED FORMAT (THIS FIXES YOUR ERROR)
                image_input = {
                    "image": {
                        "bytesBase64Encoded": image_base64,
                        "mimeType": "image/jpeg"
                    }
                }

                # 4. generate video
                operation = client.models.generate_videos(
                    model="veo-3.1-generate-preview",
                    prompt=prompt,
                    image=image_input["image"]   # IMPORTANT
                )

                # 5. wait
                while not operation.done:
                    time.sleep(10)
                    operation = client.operations.get(operation)

                video = operation.response.generated_videos[0]

                # 6. download video
                file_data = client.files.download(file=video.video)

                jobs[job_id]["status"] = "completed"
                jobs[job_id]["video"] = file_data

            except Exception as e:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"] = str(e)
                print("ERROR:", str(e))

        threading.Thread(target=process).start()

        return jsonify({
            "job_id": job_id,
            "message": "Video generation started"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# STATUS
# =========================
@app.route("/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Invalid job id"}), 404
    return jsonify(job)


# =========================
# DOWNLOAD
# =========================
@app.route("/download/<job_id>")
def download(job_id):
    job = jobs.get(job_id)

    if not job:
        return jsonify({"error": "Invalid job id"}), 404

    if job["status"] != "completed":
        return jsonify({
            "error": "Video not ready",
            "status": job["status"]
        }), 400

    return send_file(
        BytesIO(job["video"]),
        mimetype="video/mp4",
        as_attachment=True,
        download_name="video.mp4"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
