import os
import uuid
import time
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
    return "Veo API running 🚀"


@app.route("/generate-video", methods=["POST"])
def generate_video():
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

            # download image
            img = requests.get(image_url)
            if img.status_code != 200:
                raise Exception("Image download failed")

            path = f"/tmp/{job_id}.jpg"
            with open(path, "wb") as f:
                f.write(img.content)

            # upload file
            uploaded_file = client.files.upload(file=path)

            # ✅ FINAL WORKING CALL
            operation = client.models.generate_videos(
                model="veo-3.1-generate-preview",
                prompt=prompt,
                image=uploaded_file   # 🔥 ONLY THIS WORKS IN YOUR SDK
            )

            while not operation.done:
                time.sleep(5)
                operation = client.operations.get(operation)

            video = operation.response.generated_videos[0]
            file_data = client.files.download(file=video.video)

            jobs[job_id]["status"] = "completed"
            jobs[job_id]["video"] = file_data

        except Exception as e:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)
            print("ERROR:", str(e))

    threading.Thread(target=process).start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id):
    return jsonify(jobs.get(job_id, {"error": "invalid job"}))


@app.route("/download/<job_id>")
def download(job_id):
    job = jobs.get(job_id)

    if not job or job["status"] != "completed":
        return jsonify({"error": "not ready"}), 400

    return send_file(
        BytesIO(job["video"]),
        mimetype="video/mp4",
        as_attachment=True,
        download_name="video.mp4"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
