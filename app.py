import os
import sys
import json
import uuid
import shutil
import subprocess
import threading
import mimetypes
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
from urllib.parse import urlparse

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Use venv python to call yt_dlp module
YTDLP_CMD = [sys.executable, "-m", "yt_dlp"]

# Common yt-dlp flags (ffmpeg path for merging streams)
COMMON_FLAGS = [
    "--ffmpeg-location", "/opt/homebrew/bin/ffmpeg",
    "--no-warnings",
    "--no-playlist",
]

def detect_platform(url):
    domain = urlparse(url).netloc.lower()
    if "youtube" in domain or "youtu.be" in domain:
        return "youtube"
    elif "instagram" in domain:
        return "instagram"
    elif "facebook" in domain or "fb.com" in domain or "fb.watch" in domain:
        return "facebook"
    elif "tiktok" in domain:
        return "tiktok"
    elif "twitter" in domain or "x.com" in domain:
        return "twitter"
    return "other"

def clean_error(stderr):
    """Return a short, user-friendly error from yt-dlp stderr."""
    if not stderr:
        return "Could not fetch video info."
    for line in reversed(stderr.strip().splitlines()):
        line = line.strip()
        if line.startswith("ERROR:"):
            return line.replace("ERROR:", "").strip()
    return stderr.strip().splitlines()[-1] if stderr.strip() else "Unknown error"

def get_video_info(url):
    """Fetch video metadata using yt-dlp."""
    try:
        result = subprocess.run(
            YTDLP_CMD + COMMON_FLAGS + ["--dump-json", url],
            capture_output=True, text=True, timeout=45
        )
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                try:
                    data = json.loads(line)
                    return {
                        "title": data.get("title", "Unknown Title"),
                        "thumbnail": data.get("thumbnail", ""),
                        "duration": data.get("duration_string") or str(data.get("duration", "")),
                        "uploader": data.get("uploader") or data.get("channel", "Unknown"),
                        "platform": detect_platform(url),
                    }
                except Exception:
                    continue
        err = clean_error(result.stderr)
        return {"error": err}
    except Exception as e:
        return {"error": str(e)}

# ── Job tracking ──────────────────────────────────────────────────────────────
job_status = {}   # job_id -> {status, file, ext, title, error}

def run_download(job_id, url, mode, quality, out_dir):
    """Run yt-dlp download in a background thread."""
    try:
        job_status[job_id] = {"status": "downloading", "file": None, "error": None}

        if mode == "audio":
            out_tmpl = str(out_dir / "output.%(ext)s")
            cmd = YTDLP_CMD + COMMON_FLAGS + [
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "--ffmpeg-location", "/opt/homebrew/bin/ffmpeg",
                "-o", out_tmpl,
                url,
            ]
        else:
            height = quality if quality else "1080"
            out_tmpl = str(out_dir / "output.%(ext)s")
            fmt = (
                f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]"
                f"/bestvideo[height<={height}]+bestaudio"
                f"/best[height<={height}]"
                f"/best"
            )
            cmd = YTDLP_CMD + COMMON_FLAGS + [
                "-f", fmt,
                "--merge-output-format", "mp4",
                "--ffmpeg-location", "/opt/homebrew/bin/ffmpeg",
                "-o", out_tmpl,
                url,
            ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            job_status[job_id] = {
                "status": "error",
                "error": clean_error(result.stderr),
                "file": None,
            }
            return

        # Find file — look for output.mp4 / output.mp3 / output.* etc.
        VALID_EXTS = {".mp4", ".mp3", ".webm", ".mkv", ".m4a", ".ogg", ".opus"}
        chosen = None

        # First try exact matches for output.EXT
        for ext in VALID_EXTS:
            candidate = out_dir / f"output{ext}"
            if candidate.exists() and candidate.stat().st_size > 0:
                chosen = candidate
                break

        # Fallback: any valid-ext file bigger than 0 bytes
        if not chosen:
            candidates = [
                f for f in out_dir.iterdir()
                if f.is_file() and f.suffix.lower() in VALID_EXTS and f.stat().st_size > 0
            ]
            if candidates:
                chosen = max(candidates, key=lambda f: f.stat().st_size)

        if chosen:
            job_status[job_id] = {
                "status": "done",
                "file": chosen.name,        # e.g. "output.mp4"
                "ext": chosen.suffix,       # e.g. ".mp4"
                "error": None,
            }
        else:
            job_status[job_id] = {
                "status": "error",
                "error": "Download finished but output file not found.",
                "file": None,
            }

    except subprocess.TimeoutExpired:
        job_status[job_id] = {"status": "error", "error": "Download timed out (10 min limit).", "file": None}
    except Exception as e:
        job_status[job_id] = {"status": "error", "error": str(e), "file": None}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
def api_info():
    data = request.get_json()
    url = (data or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    return jsonify(get_video_info(url))


@app.route("/api/download", methods=["POST"])
def api_download():
    data = request.get_json()
    url     = (data or {}).get("url", "").strip()
    mode    = (data or {}).get("mode", "video")
    quality = (data or {}).get("quality", "1080")
    title   = (data or {}).get("title", "download")

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    job_id  = str(uuid.uuid4())
    out_dir = DOWNLOAD_DIR / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Store the human title for use when serving the file
    job_status[job_id] = {"status": "queued", "file": None, "error": None, "title": title}

    thread = threading.Thread(
        target=run_download,
        args=(job_id, url, mode, quality, out_dir),
        daemon=True
    )
    thread.start()
    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def api_status(job_id):
    return jsonify(job_status.get(job_id, {"status": "not_found"}))


@app.route("/api/file/<job_id>")
def api_file(job_id):
    info = job_status.get(job_id)
    if not info or info.get("status") != "done":
        return jsonify({"error": "File not ready"}), 404

    filename  = info.get("file")          # "output.mp4" or "output.mp3"
    ext       = info.get("ext", ".mp4")   # ".mp4" or ".mp3"
    raw_title = info.get("title", "download")

    file_path = DOWNLOAD_DIR / job_id / filename
    if not file_path.exists():
        return jsonify({"error": "File missing on server"}), 404

    # Build download filename from the video title — keep full unicode (browsers support it)
    safe_title = raw_title.strip()
    # Only remove characters that are truly invalid in filenames
    for ch in '\\/:*?"<>|\n\r\t':
        safe_title = safe_title.replace(ch, "_")
    safe_title = safe_title.strip(". ")   # no leading/trailing dots or spaces
    if not safe_title:
        safe_title = "download"
    download_name = f"{safe_title[:120]}{ext}"  # e.g. "My Video Title.mp4"

    mime = mimetypes.guess_type(download_name)[0] or "application/octet-stream"

    @after_this_request
    def cleanup(response):
        def _delete():
            try:
                shutil.rmtree(DOWNLOAD_DIR / job_id, ignore_errors=True)
                job_status.pop(job_id, None)
            except Exception:
                pass
        threading.Timer(15, _delete).start()
        return response

    return send_file(
        str(file_path),
        mimetype=mime,
        as_attachment=True,
        download_name=download_name,
    )


if __name__ == "__main__":
    print("🚀 MediaSnap is running at http://localhost:8080")
    app.run(debug=False, host="0.0.0.0", port=8080)
