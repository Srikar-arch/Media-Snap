# ⚡ MediaSnap — Video & Music Downloader

Download YouTube, Instagram, Facebook videos in **4K** or extract music at **192kbps MP3** — right from your browser.

## Features
- 🎬 **Video downloads** — 4K, 1080p, 720p, 480p, 360p (MP4)
- 🎵 **Audio extraction** — 192kbps MP3 with embedded cover art
- 📱 Supports YouTube, Instagram, Facebook, TikTok, Twitter/X and 1000+ sites
- 🔒 Files are auto-deleted after download — no storage buildup
- ✨ No sign-up, no watermarks, completely free

## Quick Start

```bash
# 1. Install dependencies
pip3 install flask yt-dlp --user

# 2. Run the server
python3 app.py

# 3. Open in browser
open http://localhost:8080
```

Or use the one-click start script:
```bash
./start.sh
```

## How to Use
1. Copy a YouTube / Instagram / Facebook video URL
2. Paste into the input field and click **Analyse**
3. Choose **Video (MP4)** or **Audio (MP3)** and select quality
4. Click **Download Now** — file saves directly to your device

## Project Structure
```
New project/
├── app.py                # Flask backend (routes + yt-dlp integration)
├── requirements.txt      # Python dependencies
├── start.sh              # One-click start script
├── templates/
│   └── index.html        # Main page (Jinja2 template)
├── static/
│   ├── css/style.css     # Full dark-mode glassmorphism design
│   └── js/app.js         # Frontend logic
└── downloads/            # Temporary download directory (auto-cleaned)
```

## Tech Stack
- **Backend**: Python 3 + Flask
- **Downloader**: yt-dlp (supports 1000+ sites)
- **Frontend**: Vanilla HTML + CSS + JS (no frameworks)
