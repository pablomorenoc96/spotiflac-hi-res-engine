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

def safe_move(src, dst, max_retries=5, delay=0.3):
    """
    Safely moves a file on Windows, handling collisions and lock errors.
    """
    import gc
    import time
    gc.collect()
    for attempt in range(max_retries):
        try:
            if os.path.exists(dst):
                try:
                    os.remove(dst)
                except Exception:
                    pass
            os.replace(src, dst)
            return True
        except (PermissionError, OSError):
            time.sleep(delay)
            gc.collect()
    try:
        shutil.copy2(src, dst)
        try:
            os.remove(src)
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"[!] Error safe_move: {e}")
        return False

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

def download_single_track(artist, album, track_title, track_pos, track_total, year, genre, target_dir, staging_dir=DEFAULT_STAGING, track_artist=None):
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
        try:
            os.remove(staging_file)
        except Exception:
            pass

    # Normalización de textos para consultas robustas
    norm_artist = re.sub(r'\s+', ' ', artist).strip()
    norm_title = re.sub(r'\s+', ' ', track_title).strip()
    norm_album = re.sub(r'\s+', ' ', album).strip()
    base_title = re.sub(r'[\(\[].*?[\)\]]', '', norm_title).strip()
    search_artist = norm_artist.replace("+", " ")

    queries = []
    if track_artist and track_artist.lower() != artist.lower():
        norm_t_artist = re.sub(r'\s+', ' ', track_artist).strip().replace("+", " ")
        queries.append(f'ytsearch1:"{norm_t_artist}" "{norm_title}"')
        queries.append(f"ytsearch1:{norm_t_artist} {norm_title}")
        if base_title and base_title != norm_title:
            queries.append(f"ytsearch1:{norm_t_artist} {base_title}")

    queries.extend([
        f'ytsearch1:"{norm_artist}" "{norm_album}" "{norm_title}"',
        f'ytsearch1:"{norm_artist}" "{norm_title}"',
        f"ytsearch1:{search_artist} {norm_title} (Official Audio)",
        f'ytsearch1:{search_artist} - Topic "{norm_title}"',
        f"ytsearch1:{search_artist} {norm_album} {norm_title}",
        f"ytsearch1:{search_artist} {norm_title}"
    ])

    if base_title and base_title != norm_title:
        queries.append(f"ytsearch1:{search_artist} {base_title}")

    downloaded = False
    stream_codec = "flac"
    stream_abr = None
    stream_asr = 48000
    stream_ext = "webm"

    for q in queries:
        cmd = [
            "yt-dlp",
            "--no-simulate",
            "--no-playlist",
            "-f", "bestaudio[ext=flac]/bestaudio[acodec=flac]/bestaudio/best",
            "-x",
            "--audio-format", "flac",
            "--audio-quality", "0",
            "--postprocessor-args", "ffmpeg:-sample_fmt s16 -compression_level 8",
            "--print", "STREAM_INFO:%(acodec)s|%(abr)s|%(asr)s|%(ext)s",
            "-o", out_tmpl,
            q
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if os.path.exists(staging_file) and os.path.getsize(staging_file) > 10000:
            downloaded = True
            m = re.search(r'STREAM_INFO:([^|\r\n]+)\|([^|\r\n]+)\|([^|\r\n]+)\|([^\r\n]+)', res.stdout)
            if m:
                stream_codec, stream_abr, stream_asr, stream_ext = m.groups()
            break
        time.sleep(0.5)

    if downloaded:
        is_native_lossless = stream_codec.lower() in ("flac", "alac", "wav") or stream_ext.lower() == "flac"
        
        # Si el stream original era lossy (Opus / AAC), asegurar que sea 16-bit FLAC
        if not is_native_lossless:
            probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=bits_per_raw_sample", "-of", "default=noprint_wrappers=1:nokey=1", staging_file]
            pr = subprocess.run(probe_cmd, capture_output=True, text=True)
            bits_raw = pr.stdout.strip()
            if bits_raw.isdigit() and int(bits_raw) > 16:
                temp_16 = staging_file + ".16.flac"
                recode_cmd = [
                    "ffmpeg", "-y", "-v", "error",
                    "-i", staging_file,
                    "-c:a", "flac",
                    "-sample_fmt", "s16",
                    "-compression_level", "8",
                    temp_16
                ]
                subprocess.run(recode_cmd, capture_output=True, text=True)
                if os.path.exists(temp_16) and os.path.getsize(temp_16) > 10000:
                    safe_move(temp_16, staging_file)

        valid, label, bits, sr = inspect_audio(staging_file, is_native_lossless=is_native_lossless, stream_codec=stream_codec, stream_abr=stream_abr)
        if valid:
            tag_artist = track_artist if track_artist else artist
            apply_vorbis_tags(staging_file, tag_artist, album, clean_title, track_pos, track_total, year, genre, source_codec=stream_codec, audio_fidelity=label)
            safe_move(staging_file, final_path)
            time.sleep(1.0)
            return True, label
        else:
            if os.path.exists(staging_file):
                try:
                    os.remove(staging_file)
                except Exception:
                    pass

    return False, "FAILED"
