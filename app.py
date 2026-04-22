import os
import time
import uuid
import requests
from flask import Flask, request, jsonify
from google import genai

app = Flask(__name__)

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

jobs = {}

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

        job_id = str(uuid.uuid4())

        jobs[job_id] = {
            "status": "queued",
            "video": None,
            "error": None
        }

        def process():
            try:
                jobs[job_id]["status"] = "processing"

                # 🔥 DIRECT PASS n8n payload → Veo API
                operation = client.models.generate_videos(
                    model="veo-3.1-generate-preview",
                    instances=data["instances"],
                    parameters=data["parameters"]
                )

                # wait
                while not operation.done:
                    time.sleep(10)
                    operation = client.operations.get(operation)

                video = operation.response.generated_videos[0]

                # download video
                file_data = client.files.download(file=video.video)

                jobs[job_id]["status"] = "completed"
                jobs[job_id]["video"] = file_data

            except Exception as e:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"] = str(e)
                print("ERROR:", str(e))

        import threading
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
    return jsonify(jobs.get(job_id, {"error": "invalid job"}))


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
