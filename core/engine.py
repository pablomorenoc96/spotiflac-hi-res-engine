import os
import sys
import re
import json
import shutil
import subprocess
import urllib.request
import urllib.parse
from core.auditor import inspect_audio, apply_vorbis_tags

ROOT_DIR = r"D:\MUSICA"
DEFAULT_STAGING = os.path.join(ROOT_DIR, "_staging")

def sanitize_filename(s):
    return re.sub(r'[<>:"/\\|?*]', '', str(s)).strip()

def fetch_deezer_metadata(query_or_id, is_album_id=False):
    """
    Retrieves album metadata, tracks, and 1000x1000 cover_xl from Deezer.
    """
    if is_album_id:
        url = f"https://api.deezer.com/album/{query_or_id}"
    else:
        q = urllib.parse.quote(str(query_or_id))
        url = f"https://api.deezer.com/search/album?q={q}"

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if not is_album_id:
                items = data.get("data", [])
                if not items:
                    return None
                alb_id = items[0]["id"]
                return fetch_deezer_metadata(alb_id, is_album_id=True)
            return data
    except Exception as e:
        print(f"[!] Deezer API Error: {e}")
        return None

def download_cover(cover_url, dest_path):
    """
    Downloads official HD cover art (1000x1000).
    """
    if os.path.exists(dest_path):
        return True
    try:
        req = urllib.request.Request(cover_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            with open(dest_path, "wb") as f:
                f.write(resp.read())
        return True
    except Exception as e:
        print(f"[!] Cover download error: {e}")
        return False

def download_single_track(artist, album, track_title, track_pos, track_total, year, genre, target_dir, staging_dir=DEFAULT_STAGING):
    """
    Downloads one track using atomic staging, Hi-Res prioritization, ffmpeg audit, and mutagen tagging.
    """
    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(staging_dir, exist_ok=True)

    clean_artist = sanitize_filename(artist)
    clean_title = sanitize_filename(track_title)
    final_filename = f"{track_pos:02d} - {clean_artist} - {clean_title}.flac"
    final_path = os.path.join(target_dir, final_filename)

    if os.path.exists(final_path):
        valid, label, bits, sr = inspect_audio(final_path)
        if valid:
            return True, label

    staging_file = os.path.join(staging_dir, f"{clean_artist}_{track_pos:02d}.flac")
    out_tmpl = os.path.join(staging_dir, f"{clean_artist}_{track_pos:02d}.%(ext)s")
    if os.path.exists(staging_file):
        os.remove(staging_file)

    queries = [
        f'ytsearch1:"{artist}" "{album}" "{clean_title}"',
        f'ytsearch1:{artist} - Topic "{clean_title}"',
        f'ytsearch1:"{artist}" "{clean_title}" (Official Audio)',
        f'ytsearch1:"{artist}" "{clean_title}"'
    ]

    for q in queries:
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "-f", "bestaudio[ext=flac]/bestaudio[acodec=flac]/bestaudio/best",
            "-x",
            "--audio-format", "flac",
            "--audio-quality", "0",
            "--postprocessor-args", "ffmpeg:-compression_level 8",
            "-o", out_tmpl,
            q
        ]
        subprocess.run(cmd, capture_output=True, text=True)
        if os.path.exists(staging_file) and os.path.getsize(staging_file) > 10000:
            valid, label, bits, sr = inspect_audio(staging_file)
            if valid:
                apply_vorbis_tags(staging_file, artist, album, clean_title, track_pos, track_total, year, genre)
                shutil.move(staging_file, final_path)
                return True, label
            else:
                if os.path.exists(staging_file):
                    os.remove(staging_file)

    return False, "FAILED"
