import os
import sys
import re
import urllib.parse
from core.engine import fetch_deezer_metadata, download_cover, download_single_track, sanitize_filename

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"D:\MUSICA"

def detect_genre_for_artist(artist_name):
    """
    Checks existing genre folder for the artist in D:\MUSICA.
    Defaults to 'Rock & Classic Rock' if new.
    """
    for item in os.listdir(ROOT_DIR):
        genre_path = os.path.join(ROOT_DIR, item)
        if os.path.isdir(genre_path) and not item.startswith("_") and not item.startswith("."):
            if os.path.exists(os.path.join(genre_path, artist_name)):
                return item
    return "Rock & Classic Rock"

def main():
    print("=" * 80)
    print("   SPOTIFLAC HI-RES ENGINE - DESCARGADOR INTERACTIVO (1 CLIC)")
    print("   Prioridad 1: Hi-Res 24-bit / Prioridad 2: Lossless FLAC 16-bit")
    print("   Auditoría Acústica ffmpeg (0 Errores) + Carátula 1000x1000 HD")
    print("=" * 80)

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("\nIntroduce nombre de Artista - Álbum o ID/URL: ").strip()

    if not query:
        print("[!] No se proporcionó ninguna búsqueda. Saliendo...")
        return

    print(f"\n[*] Buscando metadatos oficiales para: '{query}'...")
    data = fetch_deezer_metadata(query)
    if not data:
        print(f"[X] No se encontraron resultados oficiales en Deezer para: {query}")
        return

    artist = data.get("artist", {}).get("name", "Unknown Artist")
    album = data.get("title", "Unknown Album")
    year = data.get("release_date", "2026")[:4]
    cover_url = data.get("cover_xl") or data.get("cover_big")
    tracks = data.get("tracks", {}).get("data", [])
    total_tracks = len(tracks)

    genre = detect_genre_for_artist(artist)
    clean_alb = sanitize_filename(album)
    target_dir = os.path.join(ROOT_DIR, genre, artist, f"[{year}] {clean_alb}")
    os.makedirs(target_dir, exist_ok=True)

    print(f"\n===============================================================================")
    print(f"Álbum: {artist} - [{year}] {album}")
    print(f"Género destino: {genre}")
    print(f"Total pistas: {total_tracks}")
    print(f"Ruta: {target_dir}")
    print(f"===============================================================================\n")

    if cover_url:
        cover_file = os.path.join(target_dir, "cover.jpg")
        if not os.path.exists(cover_file):
            print("[*] Descargando carátula oficial en alta resolución (1000x1000)...")
            download_cover(cover_url, cover_file)

    success = 0
    hires_count = 0
    lossless_count = 0
    streaming_count = 0
    for pos, t in enumerate(tracks, 1):
        t_title = t.get("title", f"Track {pos}")
        t_artist = t.get("artist", {}).get("name")
        print(f"[{pos:02d}/{total_tracks:02d}] Procesando: {t_title}...")
        ok, label = download_single_track(artist, album, t_title, pos, total_tracks, year, genre, target_dir, track_artist=t_artist)
        if ok:
            success += 1
            if "Hi-Res Master" in label:
                hires_count += 1
            elif "Lossless CD" in label:
                lossless_count += 1
            else:
                streaming_count += 1
            print(f"      -> OK ({label})")
        else:
            print(f"      -> ERROR al descargar")

    print("\n" + "=" * 80)
    print(f"DESCARGA COMPLETADA: {success}/{total_tracks} pistas guardadas.")
    detalles = []
    if hires_count > 0:
        detalles.append(f"{hires_count} Hi-Res Nativo")
    if lossless_count > 0:
        detalles.append(f"{lossless_count} Lossless CD Nativo")
    if streaming_count > 0:
        detalles.append(f"{streaming_count} Audio Oficial HQ (Opus/AAC en FLAC 16-bit)")
    print(f"Calidad Real: {', '.join(detalles) if detalles else str(success) + ' pistas'}")
    print(f"Destino: {target_dir}")
    print("=" * 80)

if __name__ == "__main__":
    main()
