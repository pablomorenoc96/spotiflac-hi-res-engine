import os
import sys
import subprocess
from mutagen.flac import FLAC

def inspect_audio(filepath, is_native_lossless=None, stream_codec=None, stream_abr=None):
    """
    Decodes the full audio stream via ffmpeg to ensure 0 decoding errors.
    Probes real acoustic bit depth, sample rate, and audio source fidelity.
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

    # Leer metadatos de Vorbis para identificar fidelidad y codec de origen
    saved_codec = None
    saved_fidelity = None
    try:
        f = FLAC(filepath)
        saved_codec = f.get("source_codec", [None])[0] or f.get("SOURCE_CODEC", [None])[0]
        saved_fidelity = f.get("audio_fidelity", [None])[0] or f.get("AUDIO_FIDELITY", [None])[0]
    except Exception:
        pass

    codec_effective = stream_codec or saved_codec
    codec_low = (codec_effective or "").lower()

    if is_native_lossless is None:
        if codec_low in ("flac", "alac", "wav"):
            is_native_lossless = True
        elif codec_low in ("opus", "aac", "mp4a", "vorbis", "mp3"):
            is_native_lossless = False

    if is_native_lossless:
        if bits > 16 or sample_rate > 48000:
            label = f"⭐ Hi-Res Master {bits}-bit / {sample_rate/1000:.1f} kHz (Lossless Nativo)"
        else:
            label = f"💿 Lossless CD {bits}-bit / {sample_rate/1000:.1f} kHz (Lossless Nativo)"
    elif "opus" in codec_low:
        abr_str = f"{round(float(stream_abr))}k" if stream_abr and stream_abr != "None" else "160k"
        label = f"🎧 Opus {abr_str} @ {sample_rate/1000:.1f} kHz (Audio Oficial → FLAC 16-bit)"
    elif "aac" in codec_low or "mp4a" in codec_low:
        abr_str = f"{round(float(stream_abr))}k" if stream_abr and stream_abr != "None" else "128k"
        label = f"🎧 AAC {abr_str} @ {sample_rate/1000:.1f} kHz (Audio Oficial → FLAC 16-bit)"
    elif saved_fidelity:
        label = saved_fidelity
    elif bits > 16:
        # Detectar posible transcodificación hinchada por Lavf
        label = f"🎧 Streaming HQ Transcoded ({bits}-bit / {sample_rate/1000:.1f} kHz)"
    else:
        label = f"💿 Lossless {bits}-bit / {sample_rate/1000:.1f} kHz"

    return True, label, bits, sample_rate


def apply_vorbis_tags(filepath, artist, album, title, track_pos, track_total, year, genre, source_codec=None, audio_fidelity=None):
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
        if source_codec:
            f["SOURCE_CODEC"] = [str(source_codec).upper()]
        if audio_fidelity:
            f["AUDIO_FIDELITY"] = [str(audio_fidelity)]
        f.save()
        return True
    except Exception as e:
        print(f"[!] Warning applying tags to {filepath}: {e}")
        return False
