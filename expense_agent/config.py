import os
from dotenv import load_dotenv

load_dotenv()

THRESHOLD_AMOUNT = 100.0

project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

if project_id and project_id != "your-project-id":
    MODEL_NAME = f"projects/{project_id}/locations/{location}/publishers/google/models/gemini-3.1-flash-lite"
else:
    MODEL_NAME = "gemini-3.1-flash-lite"
