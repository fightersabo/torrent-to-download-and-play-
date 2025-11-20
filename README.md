# Torrent Hub

A modern web UI for downloading and streaming video torrents using a Transmission daemon. Add torrents via magnet links or `.torrent` files, then stream or download MKV/MP4 files with optional subtitle support.

## Features
- Add torrents by magnet link or uploaded `.torrent` file.
- Lists active torrents with progress and detected video files.
- Direct download links and in-browser streaming with HTTP range support.
- Subtitle tracks auto-detected (`.srt`/`.vtt`) and loaded in the player when available.
- Configurable Transmission connection via environment variables.

## Requirements
- Python 3.10+
- A reachable Transmission RPC endpoint

Install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the app
Set environment variables to point to your Transmission server:
```bash
export TRANSMISSION_HOST=localhost
export TRANSMISSION_PORT=9091
export TRANSMISSION_USERNAME=your_user # optional
export TRANSMISSION_PASSWORD=your_password # optional
export TRANSMISSION_DOWNLOAD_DIR=/path/for/downloads # optional
export APP_SECRET_KEY=change-me
```

Start the Flask server:
```bash
python app.py
```
Visit `http://localhost:5000` to add torrents and stream/download videos.

## Notes
- Streaming uses the detected file path reported by Transmission. Ensure `TRANSMISSION_DOWNLOAD_DIR` matches your daemon configuration.
- Subtitles are served when a `.srt` or `.vtt` with the same base filename exists alongside the video file.
