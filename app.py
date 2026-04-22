import time
import os
import requests
import uuid
import threading
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

                # Download image
                res = requests.get(image_url)
                if res.status_code != 200:
                    raise Exception("Image download failed")

                image_bytes = res.content

                # ✅ FINAL WORKING CALL
                operation = client.models.generate_videos(
                    model="veo-3.1-generate-preview",
                    prompt=prompt,
                    image_bytes=image_bytes,
                    image_mime_type="image/jpeg"
                )

                # Wait
                while not operation.done:
                    time.sleep(10)
                    operation = client.operations.get(operation)

                video_obj = operation.response.generated_videos[0]

                file_data = client.files.download(file=video_obj.video)

                jobs[job_id]["status"] = "completed"
                jobs[job_id]["video"] = file_data

            except Exception as e:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"] = str(e)
                print("ERROR:", str(e))

        threading.Thread(target=process_video).start()

        return jsonify({
            "job_id": job_id,
            "message": "Video generation started"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/status/<job_id>")
def status(job_id):
    return jsonify(jobs.get(job_id, {"error": "Invalid job id"}))


@app.route("/download/<job_id>")
def download(job_id):
    job = jobs.get(job_id)

    if not job or job["status"] != "completed":
        return jsonify({"error": "Not ready"}), 400

    return send_file(
        BytesIO(job["video"]),
        mimetype="video/mp4",
        as_attachment=True,
        download_name="video.mp4"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
