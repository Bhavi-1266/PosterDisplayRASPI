#!/usr/bin/env python3
"""
show_eposters.py

- Reads POSTER_TOKEN from environment (required).
- CACHE_REFRESH (seconds) controls API polling interval (default 60).
- DISPLAY_TIME (seconds) controls per-image display time (default 5).
- Optionally reads WIFI_SSID, WIFI_PSK, WIFI_CONNECT_TIMEOUT to bring up Wi-Fi before starting.
- Keeps cache directory ($HOME/eposter_cache) exactly synchronized with current API image list.
- Shows images fullscreen in portrait orientation (whole image visible).
- Exit cleanly with ESC or 'q'.
"""
from pathlib import Path
import os
import time
import sys
import shutil
import subprocess
import requests
import json
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
API_DATA_JSON = HOME / "api_data.json"  # JSON file to store API response data
EVENT_DATA_JSON = Path(__file__).parent / "event_data.json"  # JSON file with event data

# Wi-Fi envs (optional)
WIFI_SSID = os.environ.get("WIFI_SSID")
WIFI_PSK = os.environ.get("WIFI_PSK")
WIFI_TIMEOUT = int(os.environ.get("WIFI_CONNECT_TIMEOUT", "60"))  # seconds to wait to become online

# -------------------------
# Wi-Fi helpers
# -------------------------
def is_online(check_url=API_BASE, timeout=3):
    try:
        requests.get(check_url, timeout=timeout)
        return True
    except Exception:
        return False

def connect_wifi_nmcli(ssid, psk=None, iface=None, timeout=WIFI_TIMEOUT, check_url=API_BASE):
    """
    Use nmcli to connect to SSID. Returns True on success.
    """
    nmcli = shutil.which("nmcli")
    if not nmcli:
        print("[wifi] nmcli not found; cannot auto-connect.")
        return False

    # if already online, nothing to do
    if is_online(check_url=check_url):
        print("[wifi] Already online.")
        return True

    # If already connected to SSID, just verify internet
    try:
        out = subprocess.check_output([nmcli, "-t", "-f", "ACTIVE,SSID", "dev", "wifi"], text=True)
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 2 and parts[0] == "yes" and parts[1] == ssid:
                print(f"[wifi] Already connected to {ssid}.")
                return is_online(check_url=check_url)
    except Exception:
        pass

    print(f"[wifi] Attempting nmcli connect to SSID='{ssid}' (timeout {timeout}s)...")
    cmd = [nmcli, "device", "wifi", "connect", ssid]
    if psk:
        cmd += ["password", psk]
    if iface:
        cmd += ["ifname", iface]

    try:
        rc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
        print("[wifi] nmcli output:", rc.stdout.strip())
    except Exception as e:
        print("[wifi] nmcli connect failure:", e)
        return False

    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_online(check_url=check_url):
            print("[wifi] Online!")
            return True
        time.sleep(1.0)

    print("[wifi] Timed out waiting for network to become online.")
    return False

# Attempt Wi-Fi connect if WIFI_SSID provided
if WIFI_SSID:
    ok = connect_wifi_nmcli(WIFI_SSID, WIFI_PSK, timeout=WIFI_TIMEOUT, check_url=API_BASE)
    if not ok:
        print("[wifi] Could not ensure Wi-Fi connectivity. Exiting with failure so systemd can retry.")
        sys.exit(1)
else:
    print("[wifi] WIFI_SSID not set; skipping auto-connect. Ensure network is up before starting.")

# -------------------------
# Helpers (cache, fetch, display)
# -------------------------
def ensure_cache():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

def ensure_api_json():
    """
    Creates the API JSON file with empty structure if it doesn't exist.
    """
    try:
        if not API_DATA_JSON.exists():
            # Create parent directory if it doesn't exist
            API_DATA_JSON.parent.mkdir(parents=True, exist_ok=True)
            # Create empty JSON structure
            empty_data = {}
            with open(API_DATA_JSON, 'w', encoding='utf-8') as f:
                json.dump(empty_data, f, indent=2, ensure_ascii=False)
            print(f"[ensure_api_json] Created empty API data file: {API_DATA_JSON}")
    except Exception as e:
        print(f"[ensure_api_json] Failed to create API data file: {e}")

def fetch_posters(token):
    """
    Returns a list of poster dicts (as returned by API) or None on failure.
    Also saves the raw API response to api_data.json.
    """
    try:
        r = requests.get(API_BASE, params={"key": token}, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            print(f"[fetch_posters] API returned status {r.status_code}")
            return None
        data = r.json()
        
        # Save the raw API response to JSON file
        try:
            with open(API_DATA_JSON, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"[fetch_posters] Saved API response to {API_DATA_JSON}")
        except Exception as e:
            print(f"[fetch_posters] Failed to save API data to JSON: {e}")
        
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
    names = set()
    for u in urls:
        if not u:
            continue
        name = u.split("/")[-1].split("?")[0]
        if name:
            names.add(name)
    return names

def sync_cache(expected_urls):
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

    # Download missing files in order
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
            try:
                if tmp and tmp.exists():
                    tmp.unlink()
            except Exception:
                pass
    return cached_paths

def make_portrait_and_fit(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
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
    return pygame.image.fromstring(pil_img.tobytes(), pil_img.size, pil_img.mode)

def load_event_data():
    """
    Loads event data from event_data.json file.
    Returns a single event dict or None on failure.
    """
    try:
        if not EVENT_DATA_JSON.exists():
            print(f"[load_event_data] Event data file not found: {EVENT_DATA_JSON}")
            return None
        with open(EVENT_DATA_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # If it's already a dict with event fields, return it directly
            if isinstance(data, dict) and "event_id" in data:
                return data
            # Otherwise return None
            return None
    except Exception as e:
        print(f"[load_event_data] Error loading event data: {e}")
        return None

def print_event_info(event, image_index):
    """
    Prints event information to console.
    """
    print("\n" + "="*60)
    print(f"Displaying Image #{image_index + 1}")
    print("="*60)
    print(f"Event ID:        {event.get('event_id', 'N/A')}")
    print(f"Event Name:      {event.get('event_name', 'N/A')}")
    print(f"Date:            {event.get('date', 'N/A')}")
    print(f"Time:            {event.get('time', 'N/A')}")
    print(f"Venue:           {event.get('venue', 'N/A')}")
    print(f"Organizer:       {event.get('organizer', 'N/A')}")
    print(f"Category:        {event.get('category', 'N/A')}")
    print(f"Description:     {event.get('description', 'N/A')}")
    print("="*60 + "\n")

# -------------------------
# Main
# -------------------------
def main():
    if not POSTER_TOKEN:
        print("ERROR: POSTER_TOKEN environment variable not set.")
        sys.exit(1)

    ensure_cache()
    ensure_api_json()  # Create API JSON file if it doesn't exist

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
    
    # Load event data
    event_data = load_event_data()
    if event_data:
        print(f"[main] Loaded event data from {EVENT_DATA_JSON}")
        print(f"[main] Event: {event_data.get('event_name', 'N/A')}")
    else:
        print(f"[main] No event data loaded. Using default display.")

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
            current_image_idx = idx % len(image_paths)
            
            # Print event information if available
            if event_data:
                print_event_info(event_data, current_image_idx)
            
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
