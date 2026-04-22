import time
import os
import requests
import threading
import uuid
from flask import Flask, request, jsonify, send_file
from google import genai
from io import BytesIO

app = Flask(__name__)

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# store jobs
jobs = {}

@app.route("/")
def home():
    return "API is running"

# 🔥 BACKGROUND FUNCTION
def process_video(job_id, prompt, image_url):
    try:
        jobs[job_id]["status"] = "processing"

        # 1. download image
        img_response = requests.get(image_url)
        image_bytes = img_response.content

        # 2. upload image
        uploaded_file = client.files.upload(
            file=BytesIO(image_bytes),
            config={"mime_type": "image/jpeg"}
        )

        # 3. generate video
        operation = client.models.generate_videos(
            model="veo-3.1-generate-preview",
            prompt=prompt,
            image=uploaded_file.name
        )

        # 4. wait
        while not operation.done:
            time.sleep(10)
            operation = client.operations.get(operation)

        video = operation.response.generated_videos[0]

        # 5. download
        file_data = client.files.download(file=video.video)

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["video"] = file_data

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


# 🔥 START JOB
@app.route("/generate-video", methods=["POST"])
def generate_video():
    data = request.get_json()

    prompt = data.get("prompt")
    image_url = data.get("image_url")

    if not prompt or not image_url:
        return jsonify({"error": "Missing data"}), 400

    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": "queued",
        "video": None
    }

    # run in background
    thread = threading.Thread(target=process_video, args=(job_id, prompt, image_url))
    thread.start()

    # 🔥 instant response
    return jsonify({
        "message": "Video generation started",
        "job_id": job_id
    })


# 🔥 CHECK STATUS
@app.route("/status/<job_id>", methods=["GET"])
def check_status(job_id):
    job = jobs.get(job_id)

    if not job:
        return jsonify({"error": "Invalid job id"}), 404

    return jsonify({
        "status": job["status"]
    })


# 🔥 DOWNLOAD VIDEO
@app.route("/download/<job_id>", methods=["GET"])
def download_video(job_id):
    job = jobs.get(job_id)

    if not job or job["status"] != "completed":
        return jsonify({"error": "Video not ready"}), 400

    return send_file(
        BytesIO(job["video"]),
        mimetype="video/mp4",
        as_attachment=True,
        download_name="video.mp4"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
