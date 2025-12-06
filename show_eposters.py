#!/usr/bin/env python3
"""
show_eposters.py

- Reads POSTER_TOKEN from environment (required).
- CACHE_REFRESH (seconds) controls API polling interval (default 60).
- DISPLAY_TIME (seconds) controls per-image display time (default 5).
- Keeps cache directory ($HOME/eposter_cache) exactly synchronized with current API image list.
- Shows images fullscreen in portrait orientation (whole image visible).
- Exit cleanly with ESC or 'q'.
"""
from pathlib import Path
import os
import time
import sys
import requests
from PIL import Image
import pygame

# -------------------------
# Configuration (via env)
# -------------------------
API_BASE = "https://posterbridge.incandescentsolution.com/api/v1/eposter-list"
REQUEST_TIMEOUT = 10

POSTER_TOKEN = os.environ.get("POSTER_TOKEN")              # required
CACHE_REFRESH = int(os.environ.get("CACHE_REFRESH", "60"))  # seconds
DISPLAY_TIME = int(os.environ.get("DISPLAY_TIME", "5"))     # seconds

HOME = Path(os.environ.get("HOME", str(Path.home())))
CACHE_DIR = HOME / "eposter_cache"

# -------------------------
# Helpers
# -------------------------
def ensure_cache():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

def fetch_posters(token):
    """
    Returns a list of poster dicts (as returned by API) or None on failure.
    """
    try:
        r = requests.get(API_BASE, params={"key": token}, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            print(f"[fetch_posters] API returned status {r.status_code}")
            return None
        data = r.json()
        # sample structure: {"status":true,"message":"...","data":[{...}]}
        if isinstance(data, dict):
            arr = data.get("data") or data.get("eposters") or []
            if isinstance(arr, list):
                return arr
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        print("[fetch_posters] error:", e)
        return None

def expected_filenames_from_urls(urls):
    """Return set of filenames expected in cache based on URLs."""
    names = set()
    for u in urls:
        if not u:
            continue
        # keep only last path segment
        name = u.split("/")[-1].split("?")[0]
        if name:
            names.add(name)
    return names

def sync_cache(expected_urls):
    """
    Ensure cache contains exactly the files named by expected_urls.
    Returns list of Path objects for files that are now in cache (downloaded or already present),
    in the same order as expected_urls.
    """
    ensure_cache()
    expected_names = expected_filenames_from_urls(expected_urls)

    # Delete extras
    for f in CACHE_DIR.iterdir():
        if not f.is_file():
            continue
        if f.name.startswith("."):
            continue
        if f.name not in expected_names:
            try:
                f.unlink()
                print("[sync_cache] deleted old file:", f.name)
            except Exception as e:
                print("[sync_cache] failed delete:", f.name, e)

    # Download missing files and collect paths in the same order as expected_urls
    cached_paths = []
    for url in expected_urls:
        if not url:
            continue
        fname = url.split("/")[-1].split("?")[0]
        if not fname:
            continue
        dest = CACHE_DIR / fname
        if dest.exists():
            cached_paths.append(dest)
            continue
        # download to tmp then rename (avoid 'with requests.get' misuse)
        tmp = None
        try:
            r = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            tmp = dest.with_suffix(".tmp")
            with open(tmp, "wb") as fh:
                for chunk in r.iter_content(8192):
                    if chunk:
                        fh.write(chunk)
            tmp.rename(dest)
            print("[sync_cache] downloaded:", fname)
            cached_paths.append(dest)
        except Exception as e:
            print("[sync_cache] download failed for", url, "->", e)
            # try to remove tmp if exists
            try:
                if tmp and tmp.exists():
                    tmp.unlink()
            except Exception:
                pass
    return cached_paths

def make_portrait_and_fit(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Rotate to portrait if needed, scale to fit entirely, and letterbox on black canvas."""
    iw, ih = img.size
    if iw > ih:
        img = img.rotate(90, expand=True)
        iw, ih = img.size
    scale = min(target_w / iw, target_h / ih)
    nw = max(1, int(iw * scale))
    nh = max(1, int(ih * scale))
    resized = img.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 255))
    x = (target_w - nw) // 2
    y = (target_h - nh) // 2
    canvas.paste(resized, (x, y))
    return canvas

def pil_to_surface(pil_img: Image.Image):
    """Convert PIL image to pygame surface."""
    return pygame.image.fromstring(pil_img.tobytes(), pil_img.size, pil_img.mode)

# -------------------------
# Main
# -------------------------
def main():
    if not POSTER_TOKEN:
        print("ERROR: POSTER_TOKEN environment variable not set.")
        sys.exit(1)

    ensure_cache()

    pygame.init()
    pygame.display.init()
    info = pygame.display.Info()
    scr_w, scr_h = info.current_w, info.current_h
    print(f"[main] Screen detected: {scr_w}x{scr_h}")

    screen = pygame.display.set_mode((scr_w, scr_h), pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    last_sync = 0
    image_paths = []
    idx = 0
    running = True

    try:
        while running:
            # Sync cache if needed
            now = time.time()
            if now - last_sync >= CACHE_REFRESH:
                posters = fetch_posters(POSTER_TOKEN)

                if posters is None:
                    print("[main] API fetch error; will retry later.")
                else:
                    # Sort posters newest → oldest using id
                    posters = sorted(posters, key=lambda x: x.get("id", 0), reverse=True)

                    # Extract URLs in sorted order
                    urls = []
                    for entry in posters:
                        url = entry.get("eposter_file") or entry.get("file") or None
                        if url:
                            urls.append(url)

                    # Sync cache (only these files stay)
                    image_paths = sync_cache(urls)

                    if not image_paths:
                        print("[main] No poster images found in API.")
                    else:
                        print(f"[main] Cached {len(image_paths)} images (newest → oldest).")
                last_sync = now

            if not image_paths:
                # show waiting message and sleep briefly
                screen.fill((0, 0, 0))
                try:
                    font = pygame.font.SysFont("Arial", 28)
                    msg = "Waiting for posters..."
                    surf = font.render(msg, True, (255, 255, 255))
                    screen.blit(surf, ((scr_w - surf.get_width()) // 2, (scr_h - surf.get_height()) // 2))
                    pygame.display.flip()
                except Exception:
                    pygame.display.flip()
                time.sleep(1)
                # handle quit events while waiting
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        running = False
                    if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                continue

            # display current image
            path = image_paths[idx % len(image_paths)]
            try:
                img = Image.open(path).convert("RGBA")
            except Exception as e:
                print("[main] Failed to open cached image", path, e)
                idx += 1
                continue

            canvas = make_portrait_and_fit(img, scr_w, scr_h)
            surf = pil_to_surface(canvas)
            screen.blit(surf, (0, 0))
            pygame.display.flip()

            # show for DISPLAY_TIME while checking events and early-sync
            start = time.time()
            while time.time() - start < DISPLAY_TIME:
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        running = False
                    if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                # if it's time to refresh cache mid-display, break early to pick new images
                if time.time() - last_sync >= CACHE_REFRESH:
                    break
                clock.tick(30)

            idx += 1

    except KeyboardInterrupt:
        print("[main] KeyboardInterrupt, exiting.")
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()

