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

## One-command setup
- **Ubuntu 24.04**: installs Transmission, sets RPC to 0.0.0.0:9091 with basic auth, creates `.env.local`, and starts the app
  ```bash
  git clone <your-fork-url> torrent-hub && cd torrent-hub && bash scripts/ubuntu-one-click.sh
  ```
  Override credentials/paths by exporting `TRANSMISSION_USERNAME`, `TRANSMISSION_PASSWORD`, `TRANSMISSION_DOWNLOAD_DIR`, or `APP_SECRET_KEY` before running.

- **Windows 10/11 (PowerShell)**: installs Transmission via winget, sets up Python env + `.env.local`, then starts the app (Transmission remote access must be enabled in Preferences → Remote)
  ```powershell
  git clone <your-fork-url> torrent-hub; cd torrent-hub; powershell -ExecutionPolicy Bypass -File scripts\windows-one-click.ps1
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

## Setting up a Transmission server
The app expects a running Transmission daemon with RPC enabled.

### Ubuntu 24.04
1. Install and enable the daemon:
   ```bash
   sudo apt update
   sudo apt install transmission-daemon
   ```
2. Stop the service before editing settings:
   ```bash
   sudo systemctl stop transmission-daemon
   ```
3. Edit `/etc/transmission-daemon/settings.json` and set:
   - `"rpc-enabled": true`
   - `"rpc-bind-address": "0.0.0.0"` (or keep `127.0.0.1` if the app runs on the same machine)
   - `"rpc-port": 9091` (default)
   - `"rpc-username"` and `"rpc-password"` to secure access
   - `"download-dir"` to the folder the web app should serve from
   - Optionally disable the whitelist or add the web server IP in `"rpc-whitelist"`
4. Start the service again:
   ```bash
   sudo systemctl start transmission-daemon
   ```
5. Verify RPC is reachable:
   ```bash
   curl http://<server-ip>:9091/transmission/rpc
   ```

### Windows
1. Download and install Transmission from [https://transmissionbt.com/download](https://transmissionbt.com/download).
2. Open **Edit → Preferences → Remote** and enable **Allow remote access**.
3. Keep the RPC port at `9091` (or note the custom port) and set a **Username/Password**.
4. Set the **Download to** directory to the folder you want the web app to stream from.
5. Allow Transmission through Windows Firewall and ensure the app can reach the host on the configured port.
6. Confirm RPC is reachable by visiting `http://127.0.0.1:9091/transmission/rpc` (or replace with your host/IP).

## Linking Transmission to the web app
- Set `TRANSMISSION_HOST` to the IP/hostname where Transmission runs. If the daemon is on the same machine, use `localhost`.
- Set `TRANSMISSION_PORT` to match the RPC port (default `9091`).
- Provide `TRANSMISSION_USERNAME` and `TRANSMISSION_PASSWORD` if RPC auth is enabled.
- Point `TRANSMISSION_DOWNLOAD_DIR` at the same download directory configured in Transmission to allow streaming and downloads.
- Ensure the web server can reach the RPC port (9091) over the network or through firewall rules.

## Notes
- Streaming uses the detected file path reported by Transmission. Ensure `TRANSMISSION_DOWNLOAD_DIR` matches your daemon configuration.
- Subtitles are served when a `.srt` or `.vtt` with the same base filename exists alongside the video file.
