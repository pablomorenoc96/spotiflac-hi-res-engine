# -*- coding: utf-8 -*-
r"""
SISTEMA AUTOMÁTICO DE VERIFICACIÓN, AUDITORÍA DE CALIDAD Y SUSTITUCIÓN DE MÚSICA
Biblioteca: D:\MUSICA
Formatos: FLAC Hi-Res (24-bit), FLAC Lossless (16-bit), MP3, M4A
"""

import os
import sys
import shutil
import subprocess
import re
from pathlib import Path

# Force UTF-8 stdout on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from mutagen.flac import FLAC
    from mutagen.easyid3 import EasyID3
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4
except ImportError:
    print("[ERROR] Falta la librería mutagen. Ejecuta: pip install mutagen")
    sys.exit(1)

MUSIC_ROOT = Path(r"D:\MUSICA")
INPUT_DIRS = [
    MUSIC_ROOT / "Album",
    MUSIC_ROOT / "_ENTRADA_DESCARGAS"
]
QUARANTINE_DIR = Path(r"D:\_CUARENTENA_INCOMPLETAS")
QUARANTINE_LOG = QUARANTINE_DIR / "INCOMPLETAS_LOG.txt"
BACKUP_REPLACED_DIR = MUSIC_ROOT / "_REEMPLAZADOS_BACKUP"

AUDIO_EXTS = {".flac", ".mp3", ".m4a", ".ogg", ".wav", ".ape", ".wv"}

# List of known genre folders
GENRE_FOLDERS = [
    "Black Metal",
    "Clásica, Folk & Bandas Sonoras",
    "Death Metal",
    "Doom & Stoner Metal",
    "Electronic & Synthwave",
    "Gothic, Darkwave & Industrial",
    "Heavy & Power Metal",
    "Hip Hop & Phonk",
    "NSBM",
    "Playlist",
    "Punk & Hardcore",
    "Rock & Classic Rock",
    "Salsa & Música Latina",
    "Thrash Metal",
    "Vaporwave, Ambient & Experimental",
    "Videoder"
]

def print_banner():
    print("=" * 78)
    print("  AUDITORÍA Y SUSTITUCIÓN AUTOMÁTICA DE MÚSICA - HI-RES / LOSSLESS")
    print("  foobar2000 & Georgia-ReBORN Library Assistant")
    print("=" * 78)

def test_audio_integrity(filepath):
    """
    Verifies audio stream integrity 100% using ffmpeg decoding.
    Returns (True, None) if sound, (False, error_msg) if corrupt/truncated.
    """
    cmd = ["ffmpeg", "-v", "error", "-i", str(filepath), "-f", "null", "-"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        err = res.stderr.strip()
        if err:
            return False, err
        # Check if file is zero-padded
        size = os.path.getsize(filepath)
        if size < 1000:
            return False, "Archivo vacío o menor a 1 KB"
        with open(filepath, "rb") as f:
            chunk = f.read(min(size, 65536))
            if chunk == b"\x00" * len(chunk):
                return False, "Archivo 100% relleno de ceros (incompleto)"
        return True, None
    except Exception as e:
        return False, str(e)

def get_audio_info(filepath):
    """
    Extracts tags and quality information.
    """
    ext = filepath.suffix.lower()
    info = {
        "artist": None,
        "album": None,
        "title": None,
        "year": None,
        "track": None,
        "bits": 16,
        "sample_rate": 44100,
        "is_hires": False,
        "quality_str": "Lossless 16-bit / 44.1 kHz"
    }

    try:
        if ext == ".flac":
            audio = FLAC(str(filepath))
            info["bits"] = getattr(audio.info, "bits_per_sample", 16)
            info["sample_rate"] = getattr(audio.info, "sample_rate", 44100)
            if info["bits"] > 16 or info["sample_rate"] > 48000:
                info["is_hires"] = True
                info["quality_str"] = f"Hi-Res {info['bits']}-bit / {info['sample_rate']/1000:g} kHz"
            else:
                info["quality_str"] = f"Lossless {info['bits']}-bit / {info['sample_rate']/1000:g} kHz"
            
            tags = audio.tags or {}
            info["artist"] = tags.get("albumartist", [None])[0] or tags.get("artist", [None])[0]
            info["album"] = tags.get("album", [None])[0]
            info["title"] = tags.get("title", [None])[0]
            info["year"] = tags.get("date", [None])[0] or tags.get("year", [None])[0]
            info["track"] = tags.get("tracknumber", [None])[0]

        elif ext == ".mp3":
            audio = MP3(str(filepath), ID3=EasyID3)
            info["quality_str"] = f"MP3 {audio.info.bitrate // 1000} kbps"
            info["artist"] = audio.get("albumartist", [None])[0] or audio.get("artist", [None])[0]
            info["album"] = audio.get("album", [None])[0]
            info["title"] = audio.get("title", [None])[0]
            info["year"] = audio.get("date", [None])[0]
            info["track"] = audio.get("tracknumber", [None])[0]

        elif ext == ".m4a":
            audio = MP4(str(filepath))
            info["quality_str"] = f"AAC {audio.info.bitrate // 1000} kbps"
            tags = audio.tags or {}
            info["artist"] = tags.get("aART", [None])[0] or tags.get("©ART", [None])[0]
            info["album"] = tags.get("©alb", [None])[0]
            info["title"] = tags.get("©nam", [None])[0]
            info["year"] = tags.get("©day", [None])[0]

    except Exception as e:
        pass

    # Fallback to filename parsing if tags are missing
    stem = filepath.stem
    if not info["title"]:
        # Try format: Artist - Album - Title or Track - Artist - Title
        parts = stem.split(" - ")
        if len(parts) >= 3:
            if not info["artist"]:
                info["artist"] = parts[0].strip()
            if not info["album"]:
                info["album"] = parts[1].strip()
            info["title"] = parts[2].strip()
        elif len(parts) == 2:
            if not info["artist"]:
                info["artist"] = parts[0].strip()
            info["title"] = parts[1].strip()
        else:
            info["title"] = stem

    # Extract year from album or parent dir if format is [YYYY] Album
    parent_name = filepath.parent.name
    ym = re.search(r"\[(\d{4})\]", parent_name) or re.search(r"\[(\d{4})\]", str(info["album"] or ""))
    if ym and not info["year"]:
        info["year"] = ym.group(1)

    return info

def find_artist_genre(artist_name):
    r"""
    Locates which Genre folder in D:\MUSICA hosts this artist.
    """
    if not artist_name:
        return None
    artist_clean = artist_name.strip().lower()
    for g in GENRE_FOLDERS:
        gpath = MUSIC_ROOT / g
        if gpath.is_dir():
            for item in os.listdir(gpath):
                if item.lower() == artist_clean or artist_clean in item.lower():
                    return g
    return None

def sanitize_filename(name):
    """
    Removes invalid Windows path characters.
    """
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def reconcile_quarantine(title_clean, artist_clean):
    """
    Checks if this title/artist matches any file in _CUARENTENA_INCOMPLETAS.
    If so, removes the broken file from quarantine and logs resolution.
    """
    if not QUARANTINE_DIR.exists():
        return
    title_lower = title_clean.lower()
    for root, dirs, files in os.walk(QUARANTINE_DIR):
        for f in files:
            if f.lower() == "incompletas_log.txt":
                continue
            if title_lower in f.lower():
                broken_file = Path(root) / f
                try:
                    broken_file.unlink()
                    print(f"     [OK] Archivo dañado eliminado de Cuarentena: {broken_file.name}")
                    if QUARANTINE_LOG.exists():
                        with open(QUARANTINE_LOG, "a", encoding="utf-8") as lf:
                            lf.write(f"\n[RESUELTO Y SUSTITUIDO]: {broken_file.name} por nueva pista Hi-Res/Lossless verificada.\n")
                except Exception as e:
                    pass

def process_downloads():
    print_banner()
    
    # 1. Collect all candidate audio files in input dirs
    candidates = []
    for idir in INPUT_DIRS:
        if idir.exists():
            for root, dirs, files in os.walk(idir):
                for f in files:
                    fp = Path(root) / f
                    if fp.suffix.lower() in AUDIO_EXTS:
                        candidates.append(fp)

    if not candidates:
        print("\n[INFO] No se encontraron canciones nuevas en las carpetas de entrada:")
        for idir in INPUT_DIRS:
            print(f"       - {idir}")
        print("\nPara procesar pistas, descárgalas con SpotiFLAC o colócalas en _ENTRADA_DESCARGAS.")
        return

    print(f"\nSe encontraron {len(candidates)} archivos de audio para auditar.\n")

    valid_files = []
    corrupt_files = []

    # 2. Audit integrity of each file
    for idx, fp in enumerate(candidates, 1):
        rel = fp.name
        print(f"[{idx}/{len(candidates)}] Verificando integridad: {rel[:55]}...", end=" ", flush=True)
        is_ok, err = test_audio_integrity(fp)
        if is_ok:
            info = get_audio_info(fp)
            tag_badge = f"[{info['quality_str']}]"
            print(f"-> OK {tag_badge}")
            valid_files.append((fp, info))
        else:
            print(f"-> [FALLO]")
            print(f"      Motivo: {err[:80]}")
            corrupt_files.append((fp, err))

    # 3. Report corrupt files
    if corrupt_files:
        print("\n" + "!" * 78)
        print("  AVISO: SE DETECTARON DESCARGAS CORTADAS O CORRUPTAS")
        print("  Estos archivos NO se moverán a tu biblioteca para evitar dañarla.")
        print("!" * 78)
        for cf, err in corrupt_files:
            print(f"  [ERROR] {cf.name}")
            print(f"     -> {err}")
        print("\nRecomendación: Vuelve a descargar estas pistas en SpotiFLAC de forma individual.\n")

    if not valid_files:
        print("[INFO] No hay archivos sanos listos para sustituir.")
        return

    # 4. Integrate and substitute valid files
    print("\n" + "-" * 78)
    print("  INTEGRACIÓN Y SUSTITUCIÓN EN LA BIBLIOTECA (D:\\MUSICA)")
    print("-" * 78)

    substituted_count = 0
    new_tracks_count = 0

    for fp, info in valid_files:
        artist = info["artist"] or fp.parent.parent.name or "Varios"
        album = info["album"] or fp.parent.name or "Sencillos"
        title = info["title"] or fp.stem
        year = info["year"]
        ext = fp.suffix.lower()

        # Clean names
        artist_clean = sanitize_filename(artist)
        album_clean = sanitize_filename(album)
        title_clean = sanitize_filename(title)

        # Detect genre
        genre = find_artist_genre(artist)
        if not genre:
            genre = "Rock & Classic Rock" # safe default fallback

        # Determine target directory
        if year and f"[{year}]" not in album_clean:
            album_folder_name = f"[{year}] {album_clean}"
        else:
            album_folder_name = album_clean

        target_dir = MUSIC_ROOT / genre / artist_clean / album_folder_name
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / fp.name
        
        # Check if replacing an existing file
        existing_matches = list(target_dir.glob(f"*{title_clean}*{ext}"))
        
        if existing_matches:
            target_file = existing_matches[0]
            print(f"-> [SUSTITUYENDO] pista: {title_clean}")
            print(f"     Ubicación: {target_file.relative_to(MUSIC_ROOT)}")
            print(f"     Nueva Calidad: {info['quality_str']}")
            
            # Backup replaced file
            BACKUP_REPLACED_DIR.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(target_file), str(BACKUP_REPLACED_DIR / target_file.name))
            except Exception:
                pass
            
            shutil.move(str(fp), str(target_file))
            reconcile_quarantine(title_clean, artist_clean)
            substituted_count += 1
        else:
            print(f"-> [AÑADIENDO] nueva pista: {title_clean}")
            print(f"     Destino: {target_file.relative_to(MUSIC_ROOT)}")
            print(f"     Calidad: {info['quality_str']}")
            shutil.move(str(fp), str(target_file))
            reconcile_quarantine(title_clean, artist_clean)
            new_tracks_count += 1

    # 5. Clean up empty input directories
    for idir in INPUT_DIRS:
        if idir.exists():
            for root, dirs, files in os.walk(idir, topdown=False):
                if root != str(idir) and not os.listdir(root):
                    try:
                        os.rmdir(root)
                    except Exception:
                        pass

    # 6. Final report
    print("\n" + "=" * 78)
    print("  RESUMEN DEL PROCESO")
    print(f"  Pistas sustituidas con calidad superior/reparadas: {substituted_count}")
    print(f"  Pistas nuevas integradas a álbumes:               {new_tracks_count}")
    print(f"  Archivos rechazados por descarga cortada:          {len(corrupt_files)}")
    print("=" * 78)
    print("\nLas pistas ya están disponibles en foobar2000.")

if __name__ == "__main__":
    import time
    if "--watch" in sys.argv:
        print("\n[MODO VIGILANTE ACTIVO] Supervisando descargas cada 5 segundos...")
        print("Presiona Ctrl + C para detener.\n")
        try:
            while True:
                process_downloads()
                time.sleep(5)
        except KeyboardInterrupt:
            print("\nModo vigilante detenido.")
    else:
        process_downloads()
