import time
import os
import requests
import uuid
import tempfile
import threading
from flask import Flask, request, jsonify, send_file
from google import genai
from io import BytesIO

app = Flask(__name__)

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# In-memory job store
jobs = {}


@app.route("/")
def home():
    return "Veo API is running 🚀"


# =========================
# START VIDEO GENERATION
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

        def process_video():
            try:
                jobs[job_id]["status"] = "processing"

                # 🔹 STEP 1: Download image
                response = requests.get(image_url)
                if response.status_code != 200:
                    raise Exception("Image download failed")

                image_bytes = response.content

                # 🔹 STEP 2: Save temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                    tmp.write(image_bytes)
                    tmp_path = tmp.name

                # 🔹 STEP 3: Upload to Gemini
                uploaded_file = client.files.upload(file=tmp_path)

                if not uploaded_file or not uploaded_file.name:
                    raise Exception("File upload failed")

                print("Uploaded file:", uploaded_file.name)

                # 🔹 STEP 4: Generate video (FIX APPLIED HERE ✅)
                operation = client.models.generate_videos(
                    model="veo-3.1-generate-preview",
                    prompt=prompt,
                    image={
                        "file": uploaded_file.name   # ✅ IMPORTANT FIX
                    }
                )

                # 🔹 STEP 5: Wait for completion
                while not operation.done:
                    print("Processing...")
                    time.sleep(10)
                    operation = client.operations.get(operation)

                if not operation.response.generated_videos:
                    raise Exception("No video generated")

                video_obj = operation.response.generated_videos[0]

                # 🔹 STEP 6: Download video
                file_data = client.files.download(file=video_obj.video)

                jobs[job_id]["status"] = "completed"
                jobs[job_id]["video"] = file_data

            except Exception as e:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"] = str(e)
                print("ERROR:", str(e))

        # Run in background
        threading.Thread(target=process_video).start()

        return jsonify({
            "job_id": job_id,
            "message": "Video generation started"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# STATUS API
# =========================
@app.route("/status/<job_id>", methods=["GET"])
def status(job_id):
    job = jobs.get(job_id)

    if not job:
        return jsonify({"error": "Invalid job id"}), 404

    return jsonify(job)


# =========================
# DOWNLOAD API
# =========================
@app.route("/download/<job_id>", methods=["GET"])
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
