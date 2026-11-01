import os
import sys
import subprocess
from mutagen.flac import FLAC

def inspect_audio(filepath):
    """
    Decodes the full audio stream via ffmpeg to ensure 0 decoding errors.
    Probes bit depth and sample rate via ffprobe.
    Returns (is_valid: bool, quality_label: str, bits: int, sample_rate: int)
    """
    if not os.path.exists(filepath) or os.path.getsize(filepath) < 10000:
        return False, "CORRUPTED_OR_EMPTY", 0, 0

    chk = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", filepath, "-f", "null", "-"],
        capture_output=True,
        text=True
    )
    if chk.stderr:
        return False, f"DECODE_ERROR: {chk.stderr.strip()[:100]}", 0, 0

    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=sample_rate,bits_per_raw_sample",
            "-of", "default=noprint_wrappers=1:nokey=1",
            filepath
        ],
        capture_output=True,
        text=True
    )
    lines = probe.stdout.strip().split()
    sample_rate = int(lines[0]) if len(lines) > 0 and lines[0].isdigit() else 44100
    bits = int(lines[1]) if len(lines) > 1 and lines[1].isdigit() else 16

    if bits == 24:
        label = f"⭐ Hi-Res 24-bit / {sample_rate/1000:.1f} kHz"
    else:
        label = f"💿 Lossless 16-bit / {sample_rate/1000:.1f} kHz"

    return True, label, bits, sample_rate


def apply_vorbis_tags(filepath, artist, album, title, track_pos, track_total, year, genre):
    """
    Injects standardized Vorbis Comments using mutagen.flac.
    """
    try:
        f = FLAC(filepath)
        f["artist"] = [str(artist)]
        f["albumartist"] = [str(artist)]
        f["album"] = [str(album)]
        f["title"] = [str(title)]
        f["tracknumber"] = [str(track_pos)]
        if track_total:
            f["tracktotal"] = [str(track_total)]
        if year:
            f["date"] = [str(year)]
        if genre:
            f["genre"] = [str(genre)]
        f.save()
        return True
    except Exception as e:
        print(f"[!] Warning applying tags to {filepath}: {e}")
        return False
