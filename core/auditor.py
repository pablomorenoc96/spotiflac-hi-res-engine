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
        del f
        import gc
        gc.collect()
        return True
    except Exception as e:
        print(f"[!] Warning applying tags to {filepath}: {e}")
        return False


def audit_library_integrity(root_dir=r"D:\MUSICA", check_audio_samples=False, progress_callback=None):
    """
    Escaneo y auditoría exhaustiva de toda la biblioteca en disco:
    - Identifica álbumes completos con pistas válidas.
    - Detecta álbumes incompletos (solo portada cover.jpg, letras .lrc o 0 archivos de audio).
    - Detecta huecos en secuencias de pistas (álbumes parcialmente descargados).
    - Opcionalmente realiza pruebas acústicas por muestreo con ffmpeg (0 errores).
    """
    import re
    from datetime import datetime

    ignored_folders = {
        "_staging", "_quarantine", "_backups", "_catalogos",
        "$recycle.bin", "system volume information", "_foobar_backup_final_rc3",
        "_foobar_backup_pre_rc3"
    }
    audio_extensions = {'.flac', '.mp3', '.m4a', '.ogg', '.wav', '.opus'}

    complete_albums = 0
    incomplete_albums = []
    partial_albums = []
    corrupted_tracks = []
    total_artists = 0
    genres_found = set()

    for genre in sorted(os.listdir(root_dir)):
        genre_path = os.path.join(root_dir, genre)
        if not os.path.isdir(genre_path) or genre.lower() in ignored_folders or genre.startswith(('.', '_')):
            continue

        genres_found.add(genre)

        try:
            artists_list = sorted(os.listdir(genre_path))
        except Exception:
            continue

        for artist in artists_list:
            artist_path = os.path.join(genre_path, artist)
            if not os.path.isdir(artist_path) or artist.startswith('.'):
                continue

            total_artists += 1

            for root, dirs, files in os.walk(artist_path):
                folder_name = os.path.basename(root)
                m = re.match(r"^\[(\d{4})\]\s*(.*)", folder_name)
                if not m:
                    continue

                year_found = m.group(1)
                alb_title = m.group(2).strip()

                # Verificar archivos de audio
                audio_files = []
                flac_files = []
                for sub_r, _, sub_f in os.walk(root):
                    for f in sub_f:
                        ext = os.path.splitext(f.lower())[1]
                        if ext in audio_extensions:
                            audio_files.append(os.path.join(sub_r, f))
                            if ext == '.flac':
                                flac_files.append(os.path.join(sub_r, f))

                if not audio_files:
                    # Determinar motivo específico
                    all_sub_files = [f for _, _, sf in os.walk(root) for f in sf]
                    if not all_sub_files:
                        reason = "CARPETA_VACIA"
                    elif any('cover' in f.lower() or 'folder' in f.lower() for f in all_sub_files):
                        reason = "SOLO_PORTADA"
                    else:
                        reason = "SIN_AUDIO_SOLO_METADATOS"

                    incomplete_albums.append({
                        "genre": genre,
                        "artist": artist,
                        "year": year_found,
                        "title": alb_title,
                        "path": root,
                        "reason": reason,
                        "files": all_sub_files[:5]
                    })
                    continue

                # Si tiene archivos de audio, verificar si tiene huecos en la secuencia
                track_nums = []
                for af in audio_files:
                    fn = os.path.basename(af)
                    tm = re.match(r"^(\d+)", fn)
                    if tm:
                        track_nums.append(int(tm.group(1)))

                if track_nums:
                    full_range = set(range(1, max(track_nums) + 1))
                    gaps = sorted(list(full_range - set(track_nums)))
                    if gaps:
                        partial_albums.append({
                            "genre": genre,
                            "artist": artist,
                            "year": year_found,
                            "title": alb_title,
                            "path": root,
                            "present_tracks": len(track_nums),
                            "missing_tracks": gaps
                        })

                # Detectar archivos truncados por tamaño anormal o temporales abortados
                for sub_r, _, sub_f in os.walk(root):
                    for f in sub_f:
                        fp = os.path.join(sub_r, f)
                        ext = os.path.splitext(f.lower())[1]
                        if ext in {'.part', '.ytdl', '.tmp'} or f.endswith('.temp'):
                            corrupted_tracks.append({
                                "path": fp,
                                "error": f"ARCHIVO_TEMPORAL_INTERRUMPIDO ({f})"
                            })
                        elif ext in audio_extensions:
                            try:
                                if os.path.getsize(fp) < 100000:
                                    corrupted_tracks.append({
                                        "path": fp,
                                        "error": f"PISTA_TRUNCADA ({os.path.getsize(fp)} bytes)"
                                    })
                            except Exception:
                                pass

                # Muestreo acústico opcional con ffmpeg
                if check_audio_samples and flac_files:
                    sample_flac = flac_files[0]
                    valid, label, _, _ = inspect_audio(sample_flac)
                    if not valid:
                        corrupted_tracks.append({
                            "path": sample_flac,
                            "error": label
                        })

                complete_albums += 1

    result = {
        "timestamp": datetime.now().isoformat(),
        "total_genres": len(genres_found),
        "total_artists": total_artists,
        "total_albums": complete_albums + len(incomplete_albums),
        "complete_albums_count": complete_albums,
        "incomplete_albums": incomplete_albums,
        "partial_albums": partial_albums,
        "corrupted_tracks": corrupted_tracks
    }

    return result


def save_audit_report(audit_result, report_path=os.path.join(r"D:\MUSICA", "_ALBUMES_INCOMPLETOS_DETECTADOS.txt")):
    """
    Escribe un informe exhaustivo y legible para el usuario con todos los álbumes
    que requieren descarga o reparación de pistas.
    """
    inc = audit_result.get("incomplete_albums", [])
    part = audit_result.get("partial_albums", [])

    lines = []
    lines.append("=" * 80)
    lines.append("   SPOTIFLAC HI-RES ENGINE - INFORME DE AUDITORÍA DE BIBLIOTECA")
    lines.append(f"   Fecha de análisis: {audit_result.get('timestamp')}")
    lines.append(f"   Artistas indexados: {audit_result.get('total_artists')}")
    lines.append(f"   Álbumes completos con audio: {audit_result.get('complete_albums_count')}")
    lines.append(f"   Álbumes incompletos (0 audio / solo portada): {len(inc)}")
    lines.append(f"   Álbumes con pistas faltantes en secuencia: {len(part)}")
    lines.append("=" * 80)
    lines.append("")
    lines.append("INSTRUCCIONES DE REPARACIÓN:")
    lines.append("Para descargar automáticamente las canciones faltantes de estos álbumes:")
    lines.append("  1. Haz doble clic en: REPARAR_INCOMPLETOS.bat")
    lines.append("  2. O ejecuta en terminal: python actualizar_biblioteca.py --reparar-incompletos")
    lines.append("  3. O desde la aplicación visual: Tab 'Auditoría' -> Botón 'Reparar Álbumes'")
    lines.append("")

    if inc:
        lines.append("-" * 80)
        lines.append(f"1. ÁLBUMES SIN PISTAS DE AUDIO ({len(inc)} detectados):")
        lines.append("-" * 80)
        for i, a in enumerate(inc, 1):
            lines.append(f"[{i:04d}] [{a.get('genre', 'General')}] {a.get('artist', 'Artista')} - [{a.get('year', '????')}] {a.get('title', 'Álbum')}")
            lines.append(f"       Motivo: {a.get('reason', 'INCOMPLETO')} | Archivos presentes: {a.get('files', [])}")
            lines.append(f"       Ruta: {a.get('path', '')}")
            lines.append("")

    if part:
        lines.append("-" * 80)
        lines.append(f"2. ÁLBUMES CON SECUENCIA INCOMPLETA ({len(part)} detectados):")
        lines.append("-" * 80)
        for i, p in enumerate(part, 1):
            lines.append(f"[{i:03d}] [{p['genre']}] {p['artist']} - [{p['year']}] {p['title']}")
            lines.append(f"       Pistas presentes: {p['present_tracks']} | Pistas faltantes: {p['missing_tracks']}")
            lines.append(f"       Ruta: {p['path']}")
            lines.append("")

    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return True
    except Exception as e:
        print(f"[!] Error guardando reporte de auditoría: {e}")
        return False

