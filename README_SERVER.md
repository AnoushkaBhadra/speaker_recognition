# Speaker Recognition - Flask Server

## Quick Start

1. Install dependencies:
   ```bash
   pip install flask flask-cors librosa numpy soundfile werkzeug pydub resemblyzer
   ```

2. Run server:
   ```bash
   python server.py
   ```

3. Server runs at: `http://localhost:5000`

## API Endpoints

The server exposes the following endpoints (default base URL: `http://localhost:5000`):

- **Health:** `GET /` — Health check; returns server status, number of enrolled users and available endpoints.

- **Enroll:** `POST /enroll` — Enroll a new speaker. Use `multipart/form-data` with these fields:
  - `username` (string) — lowercased identifier for the speaker.
  - `clip_number` (int) — which clip this is (1 to 4 by default).
  - `audio` (file) — audio file (supported: `wav`, `mp3`, `ogg`, `webm`, `m4a`).
  - Response: JSON indicating whether the clip was saved and whether enrollment is complete. The server requires multiple clips (by default 4) and will compute and save a single averaged embedding once all clips are received.

  Example:
  ```bash
  curl -X POST "http://localhost:5000/enroll" \
    -F "username=anoushka" \
    -F "clip_number=1" \
    -F "audio=@/path/to/clip_1.wav"
  ```

- **Predict:** `POST /predict` — Predict speaker from an audio clip.
  - Request: `multipart/form-data` with field `audio` (file).
  - Response: JSON with keys: `prediction` (username or `Unknown`), `confidence` (similarity score), `threshold`, and `all_similarities` (per-user scores).

  Example:
  ```bash
  curl -X POST "http://localhost:5000/predict" \
    -F "audio=@/path/to/test_clip.wav"
  ```

- **List enrolled users:** `GET /enrolled-users` — Returns a JSON list of enrolled users and metadata (enrollment date, clips count).

- **Delete user:** `DELETE /delete-user/<username>` — Delete an enrolled user and remove saved embedding and enrollment clips.

Notes & configuration:

- **Allowed file types:** `wav`, `mp3`, `ogg`, `webm`, `m4a`.
- **Max file size:** 10 MB (server rejects larger uploads with HTTP 413).
- **Clips required for enrollment:** 4 (variable `REQUIRED_CLIPS` in `server.py`).
- **Similarity threshold:** Default is 0.75 (`SIMILARITY_THRESHOLD` in `server.py`). Matches require similarity >= threshold.

If you change configuration values in `server.py` (e.g., `REQUIRED_CLIPS`, `SIMILARITY_THRESHOLD`, or `MAX_FILE_SIZE`), update this README accordingly.

## Testing

Run test script to verify server works:
```bash
python tests/test_upload.py
```

## Directory Structure

```
project/
├── server.py              # Main Flask server
├── uploads/              # Received audio files
├── temp/                 # Temporary processing
├── logs/                 # Server logs
├── tests/                # Test scripts
└── requirements.txt      # Dependencies
```
