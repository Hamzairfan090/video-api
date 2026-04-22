import os
import uuid
import time
import base64
import threading
import requests
from flask import Flask, request, jsonify, send_file
from google import genai
from io import BytesIO

app = Flask(__name__)

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

jobs = {}


@app.route("/")
def home():
    return "Veo API Running 🚀"


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

                # =========================
                # STEP 1: Download image
                # =========================
                img = requests.get(image_url)
                if img.status_code != 200:
                    raise Exception("Image download failed")

                image_bytes = img.content

                # =========================
                # STEP 2: Convert to Base64
                # =========================
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")

                # =========================
                # STEP 3: Generate Video (FIXED)
                # =========================
                operation = client.models.generate_videos(
                    model="veo-3.1-generate-preview",
                    prompt=prompt,
                    image={
                        "bytesBase64Encoded": image_base64,
                        "mimeType": "image/jpeg"
                    }
                )

                # =========================
                # STEP 4: Wait for completion
                # =========================
                while not operation.done:
                    time.sleep(5)
                    operation = client.operations.get(operation)

                video_obj = operation.response.generated_videos[0]

                # =========================
                # STEP 5: Download video
                # =========================
                file_data = client.files.download(file=video_obj.video)

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
# STATUS API
# =========================
@app.route("/status/<job_id>")
def status(job_id):
    return jsonify(jobs.get(job_id, {"error": "Invalid job id"}))


# =========================
# DOWNLOAD API
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


# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
