import os
from functools import wraps
from typing import List, Optional

from flask import (
    Flask,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from transmission_rpc import Client, TransmissionError


app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET_KEY", "insecure-dev-key")


class TransmissionUnavailable(Exception):
    """Raised when Transmission is not reachable."""


# Transmission helpers

def get_transmission_client() -> Client:
    host = os.environ.get("TRANSMISSION_HOST", "localhost")
    port = int(os.environ.get("TRANSMISSION_PORT", "9091"))
    username = os.environ.get("TRANSMISSION_USERNAME")
    password = os.environ.get("TRANSMISSION_PASSWORD")
    download_dir = os.environ.get("TRANSMISSION_DOWNLOAD_DIR")

    client = Client(host=host, port=port, username=username, password=password)

    if download_dir:
        # Ensure the client is configured to use our preferred directory.
        session = client.get_session()
        if session.download_dir != download_dir:
            client.set_session(download_dir=download_dir)

    return client


def with_transmission(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        try:
            client = get_transmission_client()
        except TransmissionError as exc:  # pragma: no cover - environment check
            raise TransmissionUnavailable(
                "Unable to reach Transmission. Check host, port, and credentials."
            ) from exc
        return view_func(client, *args, **kwargs)

    return wrapper


VIDEO_EXTENSIONS = {".mp4", ".mkv"}
SUBTITLE_EXTENSIONS = {".srt", ".vtt"}


def video_mime_for(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".mkv":
        return "video/x-matroska"
    return "video/mp4"


def filter_video_files(files: List[dict]):
    return [
        (idx, f)
        for idx, f in enumerate(files)
        if os.path.splitext(f.get("name", ""))[1].lower() in VIDEO_EXTENSIONS
    ]


def find_subtitle_for(file_entry: dict, torrent_download_dir: str) -> Optional[str]:
    name = file_entry.get("name", "")
    base, _ = os.path.splitext(name)
    for ext in SUBTITLE_EXTENSIONS:
        candidate = os.path.join(torrent_download_dir, f"{base}{ext}")
        if os.path.exists(candidate):
            return candidate
    return None


def resolve_file_path(torrent, file_entry: dict):
    download_dir = torrent.download_dir or ""
    name = file_entry.get("name")
    if not name:
        return None
    return os.path.abspath(os.path.join(download_dir, name))


@app.route("/")
@with_transmission
def index(client: Client):
    error = None
    torrents = []
    try:
        torrents = client.get_torrents()
    except TransmissionError as exc:  # pragma: no cover - runtime connectivity
        error = str(exc)

    enriched = []
    for torrent in torrents:
        files = torrent.files()
        video_files = filter_video_files(files)
        enriched.append(
            {
                "id": torrent.id,
                "name": torrent.name,
                "status": torrent.status,
                "progress": round(torrent.progress, 2),
                "download_dir": torrent.download_dir,
                "video_files": [
                    {
                        "index": idx,
                        "name": f.get("name"),
                        "size": f.get("size"),
                        "completed": f.get("completed"),
                    }
                    for idx, f in video_files
                ],
            }
        )

    return render_template("index.html", torrents=enriched, error=error)


@app.route("/add-magnet", methods=["POST"])
@with_transmission
def add_magnet(client: Client):
    magnet = request.form.get("magnet")
    if not magnet:
        flash("Please provide a magnet link.", "error")
        return redirect(url_for("index"))
    client.add_torrent(magnet)
    flash("Magnet link added to Transmission.", "success")
    return redirect(url_for("index"))


@app.route("/add-file", methods=["POST"])
@with_transmission
def add_file(client: Client):
    torrent_file = request.files.get("torrent_file")
    if not torrent_file:
        flash("Please choose a .torrent file to upload.", "error")
        return redirect(url_for("index"))

    file_bytes = torrent_file.read()
    if not file_bytes:
        flash("Uploaded file is empty.", "error")
        return redirect(url_for("index"))

    client.add_torrent(file_bytes)
    flash("Torrent file added to Transmission.", "success")
    return redirect(url_for("index"))


@app.route("/watch/<int:torrent_id>/<int:file_index>")
@with_transmission
def watch(client: Client, torrent_id: int, file_index: int):
    torrent = client.get_torrent(torrent_id)
    files = torrent.files()
    if file_index >= len(files):
        flash("Requested file not found in torrent.", "error")
        return redirect(url_for("index"))

    file_entry = files[file_index]
    video_path = resolve_file_path(torrent, file_entry)
    if not video_path or not os.path.exists(video_path):
        flash("Video file is not available yet.", "error")
        return redirect(url_for("index"))

    subtitle_path = find_subtitle_for(file_entry, torrent.download_dir or "")
    subtitle_url = None
    if subtitle_path:
        subtitle_url = url_for("serve_subtitle", torrent_id=torrent_id, file_index=file_index)

    return render_template(
        "watch.html",
        torrent=torrent,
        file_index=file_index,
        file_entry=file_entry,
        subtitle_available=subtitle_url,
        stream_url=url_for("stream_file", torrent_id=torrent_id, file_index=file_index),
        stream_mime=video_mime_for(video_path),
    )


@app.route("/subtitle/<int:torrent_id>/<int:file_index>")
@with_transmission
def serve_subtitle(client: Client, torrent_id: int, file_index: int):
    torrent = client.get_torrent(torrent_id)
    files = torrent.files()
    if file_index >= len(files):
        abort(404)
    file_entry = files[file_index]
    subtitle_path = find_subtitle_for(file_entry, torrent.download_dir or "")
    if not subtitle_path:
        abort(404)
    mime = "text/vtt" if subtitle_path.endswith(".vtt") else "text/plain"
    return send_file(subtitle_path, mimetype=mime)


@app.route("/download/<int:torrent_id>/<int:file_index>")
@with_transmission
def download_file(client: Client, torrent_id: int, file_index: int):
    torrent = client.get_torrent(torrent_id)
    files = torrent.files()
    if file_index >= len(files):
        flash("Requested file not found in torrent.", "error")
        return redirect(url_for("index"))
    file_entry = files[file_index]
    file_path = resolve_file_path(torrent, file_entry)
    if not file_path or not os.path.exists(file_path):
        flash("File is not available yet.", "error")
        return redirect(url_for("index"))
    return send_file(file_path, as_attachment=True)


@app.route("/stream/<int:torrent_id>/<int:file_index>")
@with_transmission
def stream_file(client: Client, torrent_id: int, file_index: int):
    torrent = client.get_torrent(torrent_id)
    files = torrent.files()
    if file_index >= len(files):
        abort(404)

    file_entry = files[file_index]
    video_path = resolve_file_path(torrent, file_entry)
    if not video_path or not os.path.exists(video_path):
        abort(404)

    range_header = request.headers.get("Range", None)
    file_size = os.path.getsize(video_path)

    mime = video_mime_for(video_path)

    if range_header:
        # Handle byte ranges for streaming.
        range_value = range_header.strip().lower().replace("bytes=", "")
        start_str, end_str = range_value.split("-", 1)
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
        end = min(end, file_size - 1)

        length = end - start + 1
        with open(video_path, "rb") as f:
            f.seek(start)
            data = f.read(length)

        response = Response(data, 206, mimetype=mime)
        response.headers.add("Content-Range", f"bytes {start}-{end}/{file_size}")
        response.headers.add("Accept-Ranges", "bytes")
        response.headers.add("Content-Length", str(length))
        return response

    return send_file(video_path, mimetype=mime)


@app.errorhandler(TransmissionUnavailable)
def handle_transmission_error(exc):
    return render_template("index.html", torrents=[], error=str(exc)), 503


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
